"""
Scraper para o Machadão Atacadista (machadao.com.br), lojas de MT.
Plataforma: Osuper com front novo (mesmo do Comper: Tailwind + modais; NÃO use os
seletores do Asun/Fort). Os dados vêm de uma API de busca, não do HTML.

Como o site funciona (confirmado contra o site real em 21/10/2026):
- Rede Osuper 273 e três lojas de retirada (ids do GraphQL `OnlineStoresQuery`): 1353 Primavera
  do Leste (a padrão do site, usada aqui), 1354 Alta Floresta e 1701 Lucas do Rio Verde.
  O catálogo e o preço mudam por loja (a busca "arroz" dá 82 itens na 1353 e 87 na 1354).
- Produtos só existem no cliente. A API é
  GET https://sense.osuper.com.br/273/<loja>/v2/search?brands=&categories=&tags=&size=N&from=M
      &search=<termo>&sortField=_score&sortOrder=desc
  Resposta: hits[], total, nextFrom, hasNext. `size` máximo = 20 (maior dá HTTP 400).
  Ao contrário do Comper, NÃO precisa do header `x-osuper-search-token` nem de login, e a loja
  vai no caminho da URL (o cookie `st_273` só decide qual loja a interface mostra). Mas o
  Cloudflare/CORS barra qualquer chamada fora do navegador (curl dá 403; Chromium headless
  falha com CORS): é preciso Chrome real com janela (config.NAVEGADOR_CANAL = "chrome",
  HEADLESS = False) e fazer o `fetch` DENTRO de uma página de machadao.com.br.
- Busca com `search=` vazio devolve o catálogo inteiro, mas o filtro por `categories` aninhada
  ("store1353:Mercearia > Grãos, ...") não devolveu nada; por isso as tarefas são buscas por
  termo (como no Abevê) filtradas por `palavras_chave`.
- URL da tarefa: https://machadao.com.br/busca/<termo> (a busca do site). `?loja=<id>` é extra,
  ignorado pelo site, e troca a loja consultada (padrão 1353).
- hit: name, brandName, saleUnit ("UN" ou "KG"), pricing{price, promotion, promotionalPrice,
  discount}, quantity{inStock, fraction, sellByWeightAndUnit}, slug. Preço ativo =
  `promotionalPrice` só quando `promotion` é true (com promotion false o promotionalPrice vem
  preenchido e menor que `price`, mas o cliente paga `price`); `price` é o cheio riscado.
  saleUnit "KG" = preço já é por kg (grava 1 kg; `fraction` é o peso da porção vendida).
  Itens "UN" trazem o conteúdo no nome ("ARROZ URBANO ... 1KG"). Sem preço atacado.
- Produto abre em modal, sem URL própria conhecida: `url_produto` = página de busca da tarefa.
- `quantity.inStock` <= 0 é tratado como indisponível. Dedupe por `id` do hit dentro da tarefa
  e entre as tarefas da execução por loja (o scraper.py cria uma instância por tarefa, então o
  controle fica na classe).
"""

import json
import logging
import random
import re
import urllib.parse
from typing import Optional

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://machadao.com.br"
REDE_ID = "273"
LOJA_PADRAO = "1353"  # Primavera do Leste (a padrão do site)
API_POR_PAGINA = 20  # limite da API
MAX_PAGINAS_SEGURANCA = 50
PAUSA_ENTRE_PAGINAS_MS = (300, 800)

_JS_BUSCAR = """async (url) => {
    const r = await fetch(url, {headers: {'accept': 'application/json'}});
    return [r.status, await r.text()];
}"""


class MachadaoScraper(BaseScraper):
    nome_fornecedor = "machadao"

    # Em nível de classe: o dedupe vale para a execução inteira (uma instância por tarefa).
    _ja_coletados: set = set()  # (loja, id do hit) já devolvidos nesta execução

    @staticmethod
    def _termo_e_loja(url: str) -> tuple[Optional[str], str]:
        partes = urllib.parse.urlparse(url)
        m = re.match(r"^/busca/([^/]+)", partes.path)
        termo = urllib.parse.unquote(m.group(1)).strip() if m else None
        loja = (urllib.parse.parse_qs(partes.query).get("loja") or [LOJA_PADRAO])[0]
        return termo or None, loja

    @staticmethod
    def _url_api(loja: str, termo: str, inicio: int) -> str:
        return (
            f"https://sense.osuper.com.br/{REDE_ID}/{loja}/v2/search?brands=&categories=&tags="
            f"&size={API_POR_PAGINA}&from={inicio}&search={urllib.parse.quote(termo)}"
            "&sortField=_score&sortOrder=desc"
        )

    @staticmethod
    def _produto_do_hit(hit: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        nome = (hit.get("name") or "").strip()
        precos = hit.get("pricing") or {}
        normal = precos.get("price")
        promo = precos.get("promotionalPrice") if precos.get("promotion") else None
        preco = promo or normal
        estoque = (hit.get("quantity") or {}).get("inStock")
        if not nome or not preco or preco <= 0 or (estoque is not None and estoque <= 0):
            return None

        preco_original = desconto = None
        if promo and normal and normal > promo:
            preco_original = float(normal)
            desconto = f"-{round((1 - promo / normal) * 100)}%"

        if hit.get("saleUnit") == "KG":
            quantidade, unidade = 1.0, "kg"  # preço já é por kg
        else:
            quantidade, unidade = extrair_quantidade_e_unidade(nome)

        return Produto(
            fornecedor=MachadaoScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=hit.get("brandName") or extrair_marca(nome),
            preco=float(preco),
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=url_fonte,
        )

    def _garantir_pagina_do_site(self) -> None:
        """O fetch precisa rodar numa página de machadao.com.br (CORS/Cloudflare)."""
        if "machadao.com.br" not in (self.page.url or ""):
            self.page.goto(BASE_URL, timeout=config.NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            self.page.wait_for_timeout(4000)

    def _buscar(self, loja: str, termo: str, inicio: int) -> Optional[dict]:
        status, corpo = self.page.evaluate(_JS_BUSCAR, self._url_api(loja, termo, inicio))
        if status != 200:
            logger.warning("Machadão: API respondeu %s em '%s' (from=%s)", status, termo, inicio)
            return None
        return json.loads(corpo)

    def definir_cep(self, cep: str) -> None:
        logger.info("Machadão: a loja vem da URL da API (padrão %s); CEP %s ignorado.", LOJA_PADRAO, cep)

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        cls = type(self)
        logger.info("Coletando categoria '%s' -> %s (Machadão)", categoria, url)
        produtos: list[Produto] = []
        vistos: set = set()
        sem_preco = fora_do_filtro = 0

        termo, loja = self._termo_e_loja(url)
        if not termo:
            logger.error("Machadão: URL sem termo de busca (use /busca/<termo>): %s", url)
            return produtos

        try:
            self._garantir_pagina_do_site()
            inicio = 0
            for _ in range(MAX_PAGINAS_SEGURANCA):
                dados = self._buscar(loja, termo, inicio)
                if not dados:
                    break
                for hit in dados.get("hits", []):
                    chave = (loja, str(hit.get("id")))
                    if chave in vistos or chave in cls._ja_coletados:
                        continue
                    vistos.add(chave)
                    nome = hit.get("name") or ""
                    if palavras_chave and not any(
                        pk.lower() in nome.lower() for pk in palavras_chave
                    ):
                        fora_do_filtro += 1
                        continue
                    produto = self._produto_do_hit(hit, categoria, url)
                    if produto is None:
                        sem_preco += 1
                        continue
                    cls._ja_coletados.add(chave)
                    produtos.append(produto)
                if not dados.get("hasNext"):
                    break
                inicio = dados.get("nextFrom") or inicio + API_POR_PAGINA
                self.page.wait_for_timeout(random.randint(*PAUSA_ENTRE_PAGINAS_MS))
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Machadão)", categoria)

        logger.info(
            "Categoria '%s' (Machadão, loja %s): %d extraídos, %d sem preço/indisponíveis, "
            "%d fora do filtro.",
            categoria,
            loja,
            len(produtos),
            sem_preco,
            fora_do_filtro,
        )
        return produtos
