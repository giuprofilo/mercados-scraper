"""
Scraper para o Supervi Anápolis (compras.supervi.com.br).
Plataforma: Instabuy/Ibecom (mesma do Super Adega; Next.js, produtos carregados
no cliente — o HTML da categoria vem sem cards).

Como o site funciona (confirmado contra o site real em 15/10/2026):
- Coleta 100% via API, sem navegador:
  GET api.ibecom.com.br/api_ecommerce/v5/items?subcategory_id=..&limit=20&sort=popular&page=N
  com os headers `x-store-id` (loja Supervi Anápolis), `Origin` e `Referer`.
  Não exige login nem IBSessionId. Resposta: data[] (name, slug, brand, unit_type,
  price_config.price / price_discount.promo_price / promo_wholesale{price,
  min_qtd_to_apply}) e pagination.total_pages. Filtros `category_id` não
  funcionam (0 itens); `department_id` e `subcategory_id` sim.
- O site não tem CEP/região para preço: a loja vai no header `x-store-id`.
- Páginas de departamento: /cat/<departamento>. Sub-páginas /cat/<dep>/<sub> são
  barradas pelo Cloudflare em headless e /sub/... não existe.
  Por isso a URL da tarefa é `/cat/<departamento>?sub=<slug-da-subcategoria>`
  (a query é só a chave para achar o subcategory_id em SUBCATEGORIAS).
- Link do produto: /p/<slug>.
- Itens por peso (unit_type "KG"): o preço já é por kg -> quantidade 1, unidade "kg".
"""

import json
import logging
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from database import Produto
from scrapers.base import BaseScraper
from setup_sessao import USER_AGENT
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://www.compras.supervi.com.br"
API_URL = "https://api.ibecom.com.br/api_ecommerce/v5/items"
API_STORE_ID = "6304d114bbc17ee1fbf104e1"
API_POR_PAGINA = 20
MAX_PAGINAS_SEGURANCA = 100
PAUSA_ENTRE_PAGINAS_S = (1.0, 2.0)
STATUS_BLOQUEIO = (403, 429, 503)

# Chave = (departamento, subcategoria) da URL `/cat/<dep>?sub=<slug>`.
SUBCATEGORIAS = {
    ("frutas-legumes-e-verduras", "frutas"): "6349b79d40cbac6f37bc758e",
    ("frutas-legumes-e-verduras", "legumes"): "6349b79d40cbac6f37bc758f",
    ("frutas-legumes-e-verduras", "verduras"): "6349b79d40cbac6f37bc7590",
    ("acougue-aves-peixaria", "aves-e-frangos-cortes-resfriados-e-congelados"): "6304d1b5b88a834b6c95531b",
    ("acougue-aves-peixaria", "bovinos-e-cortes"): "6304d1b5b88a834b6c95531e",
    ("acougue-aves-peixaria", "linguicas-e-salsichas"): "6304d1b5b88a834b6c95531c",
    ("acougue-aves-peixaria", "peixaria-e-derivados"): "6304d1b5b88a834b6c95531d",
    ("acougue-aves-peixaria", "suinos-e-derivados"): "6304d1b5b88a834b6c95531f",
    ("alimentos-basicos", "arroz"): "6304d1b5b88a834b6c955306",
    ("alimentos-basicos", "conservas-e-enlatados"): "6304d1b5b88a834b6c955304",
    ("alimentos-basicos", "farinhas-e-farofas"): "6304d1b5b88a834b6c955305",
    ("alimentos-basicos", "feijao"): "6304d1b5b88a834b6c955303",
    ("alimentos-basicos", "granel"): "6304d1b5b88a834b6c955307",
    ("alimentos-basicos", "massas-instantaneas-e-tradicionais"): "6304d1b5b88a834b6c955309",
    ("condimentos-e-molhos", "fermentos-e-essencias"): "6304d1b5b88a834b6c955338",
    ("condimentos-e-molhos", "temperos-e-condimentos"): "6304d1b5b88a834b6c955339",
    ("frios-e-laticinios", "lacteos-e-iogurtes"): "6304d1b5b88a834b6c95530c",
    ("frios-e-laticinios", "manteigas-margarinas-e-cremes-vegetais"): "6304d1b5b88a834b6c95530e",
    ("frios-e-laticinios", "queijos"): "6304d1b5b88a834b6c95530f",
    ("mercearia", "acucares-e-adocantes"): "6304d1b5b88a834b6c955318",
    ("mercearia", "azeites-oleos-e-vinagres"): "6304d1b5b88a834b6c955315",
    ("mercearia", "cereais-graos-e-sementes"): "6304d1b5b88a834b6c955319",
    ("mercearia", "leites"): "6304d1b5b88a834b6c955313",
    ("mercearia", "sal"): "6304d1b5b88a834b6c955317",
}


class SuperviScraper(BaseScraper):
    nome_fornecedor = "supervi"

    @staticmethod
    def _subcategoria(url: str) -> Optional[str]:
        partes = urllib.parse.urlparse(url)
        dep = partes.path.rstrip("/").rsplit("/", 1)[-1]
        sub = urllib.parse.parse_qs(partes.query).get("sub", [""])[0]
        return SUBCATEGORIAS.get((dep, sub))

    @staticmethod
    def _produto_da_api(item: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        nome = (item.get("name") or "").strip()
        cfg = item.get("price_config") or {}
        normal = cfg.get("price")
        promo = (cfg.get("price_discount") or {}).get("promo_price")
        preco = promo or normal
        if not nome or not preco:
            return None

        preco_original = desconto = None
        if promo and normal and normal > promo:
            preco_original = normal
            desconto = f"-{round((1 - promo / normal) * 100)}%"

        atacado = cfg.get("promo_wholesale") or {}
        preco_atacado = atacado.get("price")
        qtd_minima = atacado.get("min_qtd_to_apply")

        if item.get("unit_type") == "KG":
            quantidade, unidade = 1.0, "kg"  # preço já é por kg
        else:
            quantidade, unidade = extrair_quantidade_e_unidade(nome)

        slug = item.get("slug")
        return Produto(
            fornecedor=SuperviScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=item.get("brand") or extrair_marca(nome),
            preco=float(preco),
            quantidade=quantidade,
            unidade=unidade,
            preco_atacado=float(preco_atacado) if preco_atacado else None,
            qtd_minima_atacado=int(qtd_minima) if qtd_minima else None,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=f"{BASE_URL}/p/{slug}" if slug else url_fonte,
        )

    @staticmethod
    def _buscar_pagina(subcategory_id: str, pagina: int) -> dict:
        query = urllib.parse.urlencode(
            {
                "subcategory_id": subcategory_id,
                "limit": API_POR_PAGINA,
                "sort": "popular",
                "page": pagina,
            }
        )
        headers = {
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "User-Agent": USER_AGENT,
            "x-store-id": API_STORE_ID,
        }
        req = urllib.request.Request(f"{API_URL}?{query}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def definir_cep(self, cep: str) -> None:
        logger.info("Supervi: a loja vai no header x-store-id da API — nada a definir.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Supervi)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = 0

        subcategory_id = self._subcategoria(url)
        if not subcategory_id:
            logger.error(
                "Supervi: URL sem subcategoria conhecida (use /cat/<dep>?sub=<slug>): %s", url
            )
            return produtos

        try:
            pagina, total_paginas = 1, 1
            while pagina <= min(total_paginas, MAX_PAGINAS_SEGURANCA):
                try:
                    dados = self._buscar_pagina(subcategory_id, pagina)
                except urllib.error.HTTPError as e:
                    nivel = "bloqueio" if e.code in STATUS_BLOQUEIO else "erro"
                    logger.error("Supervi: HTTP %d (%s) em '%s'.", e.code, nivel, categoria)
                    break
                except (urllib.error.URLError, TimeoutError, ValueError) as e:
                    logger.error("Supervi: falha em '%s': %s", categoria, e)
                    break

                for item in dados.get("data", []):
                    id_item = item.get("id") or item.get("slug")
                    if id_item in vistos:
                        continue
                    vistos.add(id_item)
                    produto = self._produto_da_api(item, categoria, url)
                    if produto is None:
                        sem_preco += 1
                        continue
                    if palavras_chave and not any(
                        pc.lower() in produto.nome.lower() for pc in palavras_chave
                    ):
                        continue
                    produtos.append(produto)

                total_paginas = (dados.get("pagination") or {}).get("total_pages", 1)
                pagina += 1
                if pagina <= total_paginas:
                    time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS_S))
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Supervi)", categoria)

        logger.info(
            "Supervi: %d produtos em '%s' (%d sem preço).", len(produtos), categoria, sem_preco
        )
        return produtos
