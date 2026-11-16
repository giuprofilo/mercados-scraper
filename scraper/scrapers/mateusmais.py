"""
Scraper para o Mateus Mais (mateusmais.com.br), e-commerce do Grupo Mateus (MA/CE/PI/...).
Plataforma: SPA Angular + API própria (app.mateusmais.com.br) com busca Meilisearch.

Como o site funciona (confirmado contra o site real em 16/11/2026):
- Coleta 100% via API, sem navegador nem login (o HTML vem vazio, só o `<app-root>`):
  POST https://app.mateusmais.com.br/api/products/internal/v1/service/priority
  corpo JSON {"facets": ["brand"], "params": "<querystring>", "index":
  "SHOWCASE_catalog_product_api_index_PROD_total_quantity_sold_desc", "service": "meilisearch",
  "market_priority": {"market_ids": [<loja>]}}; `params` = page (de 0), hitsPerPage (máx. 500),
  query e facetFilters=[["market_id:<loja>"]]. Resposta: hits[], nbHits, nbPages.
- Região = LOJA (market_id), que o site escolhe pela geolocalização (default São Luís/MA).
  Lojas de uma coordenada: GET /api/products/market-category-group/?latitude=&longitude=&city_code=.
  Em Fortaleza (-3.7319,-38.5267, city_code 2304400) aparece só uma loja de alimentos de atacarejo:
  "Mix Mateus José Walter" (id 8d5dfbd5-2150-43ee-b408-329c576550ea; categoria "Mercado" = Mix,
  o atacarejo) e a "Mateus Express José Walter" (fec6b6c4-..., conveniência). Outras do CE:
  Mix Mateus Sobral b749a737-a0e9-4b17-87b2-3c7ca88300b6. O CEP do bot (`config.CEP`) é ignorado.
  O CNPJ da loja online (03995515001309) bate com a "Mateus Supermercados" da aba Empresas.
- URL da tarefa = a própria URL de busca do site:
  https://mateusmais.com.br/produtos/all?query=<termo>&market_ids=<id-da-loja>
  (sem `market_ids` usa a Mix Mateus José Walter). O scraper lê `query` e `market_ids` da URL.
- Item (hit): name, brand, price (cheio), sale_price (atual; < price = promoção), measure_type/
  measure (KG/G/L/ML/Unidade/CARTELA/porção), is_bulk, bulk_portion, bulk_price, for_sale,
  is_active, amount_in_stock, objectID (id estável) e market_id. Link do produto:
  https://mateusmais.com.br/produtos/<market_id>/<objectID>.
- Por peso (`is_bulk` true, measure_type "porção"): `price`/`sale_price` valem para a PORÇÃO
  `bulk_portion` (g) e `bulk_price` é o preço atual por kg (tomate: 8,24 por 500 g = 16,49/kg;
  banana prata: 1000 g = 3,99/kg). Grava-se o preço por kg com quantidade 1 kg.
- Demais itens: preço da embalagem; quantidade/unidade de measure (KG/G/L/ML) ou do nome.
- A busca é aproximada ("banana" traz barra de cereal e iogurte), então o filtro por
  `palavras_chave` é obrigatório. Mesmo filtro estrito do CasaAurora/DelMoro: sem acento, palavra
  inteira, "a+b" exige as duas, "-x" exclui (ex.: "-bandeja"). Token extra "@avulso": só itens
  avulsos da loja (por peso ou unidade, código de barras interno com 7+ zeros à esquerda, sem
  EAN de fábrica). Serve para hortifrúti/carne fresca, onde a busca traz shampoo, refresco,
  salgadinho e ração com o mesmo nome (ex.: "abacate", "cebola", "músculo").
- Atacado: `wholesale_sale_price` veio sempre nulo (2.500 itens por loja varridos); não há preço
  de atacado mapeado. Itens sem estoque (`for_sale` falso) ou inativos são descartados.
"""

import json
import logging
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from database import Produto
from scrapers.base import BaseScraper
from scrapers.casaaurora import CasaAuroraScraper
from setup_sessao import USER_AGENT
from utils.parsers import extrair_marca, extrair_quantidade_e_unidade

logger = logging.getLogger(__name__)

BASE_URL = "https://mateusmais.com.br"
API_URL = "https://app.mateusmais.com.br/api/products/internal/v1/service/priority"
INDICE = "SHOWCASE_catalog_product_api_index_PROD_total_quantity_sold_desc"
LOJA_PADRAO = "8d5dfbd5-2150-43ee-b408-329c576550ea"  # Mix Mateus José Walter (Fortaleza/CE)
ITENS_POR_PAGINA = 100
MAX_PAGINAS_SEGURANCA = 10
PAUSA_ENTRE_REQUISICOES_S = (0.5, 1.0)
STATUS_BLOQUEIO = (403, 429, 503)

_UNIDADE_MEDIDA = {"KG": "kg", "G": "g", "L": "L", "ML": "ml"}


_REGEX_CARTELA = re.compile(r"(\d+)\s*x\s*1\b", re.IGNORECASE)  # "Ovos 20x1" = 20 un
TOKEN_AVULSO = "@avulso"
PREFIXO_CODIGO_INTERNO = "0000000"


class MateusMaisScraper(BaseScraper):
    nome_fornecedor = "mateusmais"

    @staticmethod
    def _avulso(item: dict) -> bool:
        """Item da loja sem EAN de fábrica (hortifrúti, açougue, peixaria, padaria)."""
        codigo = (item.get("barcode") or "").strip()
        return not codigo or codigo.startswith(PREFIXO_CODIGO_INTERNO)

    @staticmethod
    def _consulta(url: str) -> tuple[str, str]:
        """(termo, market_id) lidos da URL de busca da tarefa."""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        termo = (query.get("query") or [""])[0].strip()
        lojas = (query.get("market_ids") or [LOJA_PADRAO])[0].split(",")
        return termo, lojas[0].strip() or LOJA_PADRAO

    @staticmethod
    def _produto_da_api(item: dict, categoria: str) -> Optional[Produto]:
        nome = (item.get("name") or "").strip()
        if not nome or not item.get("is_active", True) or not item.get("for_sale", True):
            return None
        cheio = item.get("price")
        atual = item.get("sale_price") or cheio
        if not atual or atual <= 0:
            return None

        if item.get("is_bulk") and item.get("bulk_price"):
            # price/sale_price são da porção `bulk_portion`; bulk_price = atual por kg.
            por_kg = float(item["bulk_price"])
            cheio = round(cheio * por_kg / atual, 2) if cheio else None
            atual = por_kg
            quantidade, unidade = 1.0, "kg"
        else:
            medida = item.get("measure")
            unidade = _UNIDADE_MEDIDA.get((item.get("measure_type") or "").upper())
            if unidade and medida:
                quantidade = float(medida)
            elif (item.get("measure_type") or "").lower() == "unidade" and (medida or 0) > 1:
                quantidade, unidade = float(medida), "un"  # ex.: ovos "10x1" = 10 un
            else:
                quantidade, unidade = extrair_quantidade_e_unidade(nome)
                cartela = _REGEX_CARTELA.search(nome)
                if quantidade is None and cartela:
                    quantidade, unidade = float(cartela.group(1)), "un"

        preco_original = desconto = None
        if cheio and cheio > atual:
            preco_original = float(cheio)
            desconto = f"-{round((1 - atual / cheio) * 100)}%"

        id_item, loja = item.get("objectID") or item.get("id"), item.get("market_id")
        return Produto(
            fornecedor=MateusMaisScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=item.get("brand") or extrair_marca(nome),
            preco=float(atual),
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=f"{BASE_URL}/produtos/{loja}/{id_item}" if id_item and loja else None,
        )

    @staticmethod
    def _buscar_pagina(termo: str, loja: str, pagina: int) -> dict:
        params = urllib.parse.urlencode(
            {
                "page": pagina,
                "hitsPerPage": ITENS_POR_PAGINA,
                "facetFilters": json.dumps([[f"market_id:{loja}"], ["for_sale:true"]]),
                "query": termo,
            }
        )
        corpo = {
            "facets": ["brand"],
            "params": params,
            "index": INDICE,
            "service": "meilisearch",
            "market_priority": {"market_ids": [loja]},
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(
            API_URL, data=json.dumps(corpo).encode(), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def definir_cep(self, cep: str) -> None:
        logger.info("Mateus Mais: a loja (market_id) vem na URL da tarefa — nada a definir.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        termo, loja = self._consulta(url)
        logger.info("Coletando '%s' (busca '%s', loja %s) (Mateus Mais)", categoria, termo, loja[:8])
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = 0
        so_avulso = TOKEN_AVULSO in (palavras_chave or [])
        palavras_chave = [p for p in (palavras_chave or []) if p != TOKEN_AVULSO]
        if not termo:
            logger.error("Mateus Mais: URL sem `query=<termo>`: %s", url)
            return produtos

        try:
            pagina, total_paginas = 0, 1
            while pagina < min(total_paginas, MAX_PAGINAS_SEGURANCA):
                try:
                    dados = self._buscar_pagina(termo, loja, pagina)
                except urllib.error.HTTPError as e:
                    nivel = "bloqueio" if e.code in STATUS_BLOQUEIO else "erro"
                    logger.error("Mateus Mais: HTTP %d (%s) em '%s'.", e.code, nivel, termo)
                    break
                except (urllib.error.URLError, TimeoutError, ValueError) as e:
                    logger.error("Mateus Mais: falha em '%s': %s", termo, e)
                    break

                for item in dados.get("hits", []):
                    id_item = item.get("objectID") or item.get("id")
                    if id_item in vistos:
                        continue
                    vistos.add(id_item)
                    if so_avulso and not self._avulso(item):
                        continue
                    produto = self._produto_da_api(item, categoria)
                    if produto is None:
                        sem_preco += 1
                        continue
                    if palavras_chave and not CasaAuroraScraper._nome_confere(
                        produto.nome, palavras_chave
                    ):
                        continue
                    produtos.append(produto)

                total_paginas = dados.get("nbPages", 1)
                pagina += 1
                if pagina < total_paginas:
                    time.sleep(random.uniform(*PAUSA_ENTRE_REQUISICOES_S))
        except Exception:
            logger.exception("Erro ao processar '%s' (Mateus Mais)", categoria)

        logger.info(
            "Mateus Mais: %d produtos em '%s' (busca '%s'; %d sem preço/indisponíveis).",
            len(produtos),
            categoria,
            termo,
            sem_preco,
        )
        return produtos
