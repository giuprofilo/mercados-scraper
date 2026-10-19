"""
Scraper para o Abevê (abeve.com.br), loja Abevê Albino Torraca, Dourados/MS.
Plataforma: VIP Commerce (Angular; o HTML vem vazio, só `<vip-root>`).

Como o site funciona (confirmado contra o site real em 19/10/2026):
- Coleta 100% via API, sem navegador. Base:
  https://services.vipcommerce.com.br/api-admin/v1/org/276 (276 = Abevê).
  Autenticação anônima: POST /auth/loja/login {domain, username: "loja", key} devolve
  um JWT (a `key` é pública, embutida no JS do site) e as chamadas seguintes levam
  `Authorization: Bearer <jwt>`, `DomainKey: abeve.com.br` e `OrganizationId: 276`.
  Sem Cloudflare/bloqueio: funciona até em headless e com urllib.
- Loja única: filial 1 / centro de distribuição 1 (Albino Torraca). Não há CEP nem
  login para preço; `definir_cep` não faz nada.
- Busca (a fonte das tarefas, abrange o catálogo inteiro e ignora acentos):
  GET /filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/<termo>?page=N
  -> data.produtos[], paginator{page, items_per_page=20, total_pages, total_items}.
  A URL da tarefa é a do site: https://www.abeve.com.br/busca?termo=<termo>,
  mais `&secoes=131,133` (extra, ignorado pelo site): ids de seção mercadológica
  (`classificacao_mercadologica_id` do item; árvore em
  .../loja/classificacoes_mercadologicas/departamentos/arvore: 131 Fruta, 133 Legume,
  135 Verdura folha, 85 Carne bovina, 92 Arroz...) em que o item precisa estar. Sem isso
  a busca por "banana" traz bala, iogurte e shampoo.
  Também existe .../loja/classificacoes_mercadologicas/departamentos/<id>/produtos
  (listagem por departamento, mesmo formato), não usada.
- A busca devolve também itens que só citam o termo (ex.: "tomate" traz extrato,
  "carne" traz escondidinho), por isso o filtro de `palavras_chave` é essencial.
- Produto: descricao, preco (string), disponivel, unidade_sigla ("UN"/"KG"),
  quantidade_unidade_diferente, em_oferta + oferta{preco_antigo, preco_oferta}
  ("Preço Abevê"), produto_id, link. Link do site: /produto/<produto_id>/<link>.
- Peso: com unidade_sigla "KG" o `preco` é de UMA unidade aproximada de
  `quantidade_unidade_diferente` kg (ex.: "Banana Nanica 600g" = 3.89 por 0,6 kg; o
  site mostra "/600g"). O preço por kg é preco / quantidade_unidade_diferente
  (preço de oferta idem), gravado com quantidade 1 kg. Quando a quantidade é 1
  (ex.: "Carne Bov Figado Kg") o preço já é por kg. Itens "UN" (ex.: "Tomate Grape 180g")
  guardam o preço da embalagem e a quantidade vem do nome.
- Promoção: oferta.preco_antigo é o preço cheio e oferta.preco_oferta o ativo
  (`preco_original`/`exibe_preco_original` do item vêm zerados). Sem preço atacado
  mapeado (`faixas_precos` veio sempre vazio).
- Indisponível: `disponivel` false -> descartado.
- Dedupe por produto_id dentro da tarefa e entre as tarefas da mesma execução (as buscas
  de um mesmo grupo se sobrepõem; o scraper.py cria uma instância por tarefa, então o
  controle fica na classe).
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

BASE_URL = "https://www.abeve.com.br"
DOMINIO = "abeve.com.br"
API_URL = "https://services.vipcommerce.com.br/api-admin/v1/org/276"
API_CHAVE_LOJA = "df072f85df9bf7dd71b6811c34bdbaa4f219d98775b56cff9dfa5f8ca1bf8469"
API_BUSCA = "/filial/1/centro_distribuicao/1/loja/buscas/produtos/termo"
MAX_PAGINAS_SEGURANCA = 10
PAUSA_ENTRE_PAGINAS_S = (0.5, 1.2)
STATUS_BLOQUEIO = (403, 429, 503)


class AbeveScraper(BaseScraper):
    nome_fornecedor = "abeve"

    # Em nível de classe: o scraper.py cria uma instância por tarefa, e o token e o dedupe
    # precisam valer para a execução inteira.
    _token: Optional[str] = None
    _ja_coletados: set = set()  # produto_id já devolvido nesta execução

    @staticmethod
    def _termo(url: str) -> Optional[str]:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        termo = (query.get("termo") or [""])[0].strip()
        return termo or None

    @staticmethod
    def _secoes(url: str) -> Optional[set[int]]:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        ids = (query.get("secoes") or [""])[0]
        return {int(i) for i in ids.split(",") if i.strip().isdigit()} or None

    @staticmethod
    def _requisitar(caminho: str, token: Optional[str] = None, corpo=None) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "DomainKey": DOMINIO,
            "OrganizationId": "276",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "User-Agent": USER_AGENT,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        dados = json.dumps(corpo).encode() if corpo is not None else None
        req = urllib.request.Request(f"{API_URL}{caminho}", data=dados, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def _obter_token(self, renovar: bool = False) -> str:
        if AbeveScraper._token is None or renovar:
            resposta = self._requisitar(
                "/auth/loja/login",
                corpo={"domain": DOMINIO, "username": "loja", "key": API_CHAVE_LOJA},
            )
            AbeveScraper._token = resposta["data"]
        return AbeveScraper._token

    def _buscar_pagina(self, termo: str, pagina: int) -> dict:
        caminho = f"{API_BUSCA}/{urllib.parse.quote(termo)}?page={pagina}"
        try:
            return self._requisitar(caminho, self._obter_token())
        except urllib.error.HTTPError as e:
            if e.code != 401:
                raise
            return self._requisitar(caminho, self._obter_token(renovar=True))

    @staticmethod
    def _produto_da_api(item: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        nome = (item.get("descricao") or "").strip()
        if not nome or not item.get("disponivel"):
            return None
        try:
            normal = float(item.get("preco") or 0)
            oferta = item.get("oferta") if item.get("em_oferta") else None
            promo = float((oferta or {}).get("preco_oferta") or 0)
            if oferta and oferta.get("preco_antigo"):
                normal = float(oferta["preco_antigo"])
        except (TypeError, ValueError):
            return None
        preco = promo or normal
        if preco <= 0:
            return None

        por_kg = item.get("unidade_sigla") == "KG"
        fator = 1.0
        if por_kg:
            fator = float(item.get("quantidade_unidade_diferente") or 1) or 1.0
            preco = round(preco / fator, 2)
            normal = round(normal / fator, 2)
            quantidade, unidade = 1.0, "kg"
        else:
            quantidade, unidade = extrair_quantidade_e_unidade(nome)

        preco_original = desconto = None
        if promo and normal > preco:
            preco_original = normal
            desconto = f"-{round((1 - preco / normal) * 100)}%"

        link = item.get("link")
        id_produto = item.get("produto_id")
        url_produto = f"{BASE_URL}/produto/{id_produto}/{link}" if link else url_fonte
        return Produto(
            fornecedor=AbeveScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=preco,
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=url_produto,
        )

    def definir_cep(self, cep: str) -> None:
        logger.info("Abevê: loja única (Albino Torraca, Dourados/MS) — nada a definir.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Abevê)", categoria, url)
        produtos: list[Produto] = []
        vistos: set = set()
        sem_preco = 0

        termo = self._termo(url)
        if not termo:
            logger.error("Abevê: URL sem termo de busca (use /busca?termo=<termo>): %s", url)
            return produtos

        secoes = self._secoes(url)
        try:
            pagina, total_paginas = 1, 1
            while pagina <= min(total_paginas, MAX_PAGINAS_SEGURANCA):
                try:
                    dados = self._buscar_pagina(termo, pagina)
                except urllib.error.HTTPError as e:
                    nivel = "bloqueio" if e.code in STATUS_BLOQUEIO else "erro"
                    logger.error("Abevê: HTTP %d (%s) em '%s'.", e.code, nivel, categoria)
                    break
                except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
                    logger.error("Abevê: falha em '%s': %s", categoria, e)
                    break

                for item in (dados.get("data") or {}).get("produtos") or []:
                    id_item = item.get("produto_id")
                    if id_item in vistos or id_item in AbeveScraper._ja_coletados:
                        continue
                    vistos.add(id_item)
                    if secoes and item.get("classificacao_mercadologica_id") not in secoes:
                        continue
                    produto = self._produto_da_api(item, categoria, url)
                    if produto is None:
                        sem_preco += 1
                        continue
                    if palavras_chave and not any(
                        pc.lower() in produto.nome.lower() for pc in palavras_chave
                    ):
                        continue
                    AbeveScraper._ja_coletados.add(id_item)
                    produtos.append(produto)

                total_paginas = (dados.get("paginator") or {}).get("total_pages", 1)
                pagina += 1
                if pagina <= min(total_paginas, MAX_PAGINAS_SEGURANCA):
                    time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS_S))
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Abevê)", categoria)

        logger.info(
            "Abevê: %d produtos em '%s' (%d sem preço/indisponíveis).",
            len(produtos),
            categoria,
            sem_preco,
        )
        return produtos
