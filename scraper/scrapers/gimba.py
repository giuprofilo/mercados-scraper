"""
Scraper para o Gimba (gimba.com.br).
Plataforma própria (ASP.NET, HTML renderizado no servidor) — NÃO é Osuper,
então os seletores não têm nada a ver com Asun/Fort.

Como o site funciona (confirmado contra o site real):
- Cada card é um ".CardProduto" com nome em "h2.ChamaItem", link em
  "a.LinkCardPDP" (href com "?PID=<id>") e preços em blocos separados:
  ".CardPrecoDE" ("de R$ 29,90", riscado), ".CardPrecoPOR" ("por apenas
  R$ 25,99" ou "Produto Indisponível") e ".CardPrecoLeveMais" (atacado:
  "12 un. ou + por R$ 2,99 cada").
- ".CardDescontoPreco" é o preço no PIX (3% off) — não é promoção, é
  ignorado.
- Categoria mostra 60 itens por página; a troca de página é AJAX
  (PaginaLista(n) troca o conteúdo de #conteudoVitrine, a URL não muda).
  O total vem em ".TotalItens" ("114 produtos encontrados").
- Páginas de departamento (ex: /limpeza/?DID=9) já incluem os produtos das
  subcategorias. Departamentos como "cafe", "snacks" e "natal" são
  agrupamentos que repetem produtos de outros — por isso é feito dedupe
  por PID.
- Preço/condição pode depender da conta (CNPJ). O login é por e-mail +
  código de 6 dígitos em cliente.gimba.com.br, então não dá para
  automatizar: rode setup_sessao.py, entre manualmente e o perfil
  persistente guarda a sessão. definir_cep aqui só confere se a sessão
  está ativa (deslogado, o cabeçalho mostra "faça login" em #ClicarLogar).
- Não há CEP a definir.
"""

import math
import re
import logging
from typing import Optional
from bs4 import BeautifulSoup

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import (
    parse_preco,
    extrair_quantidade_e_unidade,
    extrair_marca,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.gimba.com.br"
ITENS_POR_PAGINA = 60
MAX_PAGINAS_SEGURANCA = 200


class GimbaScraper(BaseScraper):
    nome_fornecedor = "gimba"

    SEL_CARD_PRODUTO = ".CardProduto"
    SEL_NOME_PRODUTO = "h2.ChamaItem"
    SEL_LINK_PRODUTO = "a.LinkCardPDP"
    SEL_PRECO_DE = ".CardPrecoDE"
    SEL_PRECO_POR = ".CardPrecoPOR"
    SEL_PRECO_LEVE_MAIS = ".CardPrecoLeveMais"
    SEL_TOTAL_ITENS = ".TotalItens"
    SEL_LINK_LOGIN = "#ClicarLogar"

    _RE_PID = re.compile(r"[?&]PID=(\d+)")
    _RE_ATACADO = re.compile(
        r"(\d+)\s*un\.?\s*ou\s*\+\s*por\s*R\$\s*([\d.,]+)", re.IGNORECASE
    )

    def definir_cep(self, cep: str) -> None:
        """Não há CEP: só confere se a sessão (conta CNPJ) está logada."""
        self.page.goto(BASE_URL, timeout=config.NAV_TIMEOUT_MS)
        try:
            self.page.wait_for_selector(self.SEL_LINK_LOGIN, timeout=10000)
        except Exception:
            logger.warning("Gimba: não achei o link de login; não sei se há sessão.")
            return
        texto = self.page.locator(self.SEL_LINK_LOGIN).first.inner_text()
        if "faça login" in texto.lower():
            logger.warning(
                "Gimba: sessão NÃO logada — os preços coletados serão os de "
                "visitante, não os da conta CNPJ. Rode `python setup_sessao.py` "
                "e faça login no Gimba (também confira config.USAR_SESSAO_SALVA)."
            )
        else:
            logger.info("Gimba: sessão logada (%s).", " ".join(texto.split()))

    def _total_de_itens(self) -> Optional[int]:
        loc = self.page.locator(self.SEL_TOTAL_ITENS)
        if loc.count() == 0:
            return None
        m = re.search(r"(\d+)", loc.first.inner_text())
        return int(m.group(1)) if m else None

    def _primeiro_nome(self) -> Optional[str]:
        loc = self.page.locator(f"{self.SEL_CARD_PRODUTO} {self.SEL_NOME_PRODUTO}")
        return loc.first.inner_text().strip() if loc.count() > 0 else None

    def _ir_para_pagina(self, numero: int) -> bool:
        """Chama a paginação AJAX do site e espera o grid trocar."""
        anterior = self._primeiro_nome()
        self.page.evaluate(f"PaginaLista({numero})")
        try:
            self.page.wait_for_function(
                """(antigo) => {
                    const h = document.querySelector('.CardProduto h2.ChamaItem');
                    return h && h.innerText.trim() !== antigo;
                }""",
                arg=anterior,
                timeout=15000,
            )
        except Exception:
            logger.warning("Página %d não carregou (grid não mudou).", numero)
            return False
        self.page.wait_for_timeout(500)
        return True

    def _extrair_card(self, card, categoria: str) -> Optional[Produto]:
        nome_el = card.select_one(self.SEL_NOME_PRODUTO)
        if not nome_el:
            return None
        nome = nome_el.get_text(strip=True)

        por_el = card.select_one(self.SEL_PRECO_POR)
        # "Produto Indisponível" não tem R$ -> parse_preco devolve None
        preco = parse_preco(por_el.get_text(" ", strip=True)) if por_el else None
        if preco is None:
            return None

        preco_original = None
        de_el = card.select_one(self.SEL_PRECO_DE)
        if de_el:
            preco_original = parse_preco(de_el.get_text(" ", strip=True))

        desconto = None
        if preco_original and preco_original > preco:
            desconto = f"-{round((1 - preco / preco_original) * 100)}%"
        else:
            preco_original = None

        preco_atacado = qtd_minima = None
        lm_el = card.select_one(self.SEL_PRECO_LEVE_MAIS)
        if lm_el:
            m = self._RE_ATACADO.search(lm_el.get_text(" ", strip=True))
            if m:
                qtd_minima = int(m.group(1))
                preco_atacado = parse_preco(m.group(2))

        url_produto = None
        link_el = card.select_one(self.SEL_LINK_PRODUTO)
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url_produto = href if href.startswith("http") else f"{BASE_URL}{href}"

        quantidade, unidade = extrair_quantidade_e_unidade(nome)

        return Produto(
            fornecedor=self.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=preco,
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            preco_atacado=preco_atacado,
            qtd_minima_atacado=qtd_minima,
            desconto=desconto,
            url_produto=url_produto,
        )

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Gimba)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        indisponiveis = 0

        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=15000)

            total = self._total_de_itens()
            paginas = math.ceil(total / ITENS_POR_PAGINA) if total else 1
            paginas = min(paginas, MAX_PAGINAS_SEGURANCA)
            logger.info("%s itens em %d página(s).", total, paginas)

            for pagina in range(1, paginas + 1):
                if pagina > 1 and not self._ir_para_pagina(pagina):
                    break

                soup = BeautifulSoup(self.page.content(), "html.parser")
                for card in soup.select(self.SEL_CARD_PRODUTO):
                    link = card.select_one(self.SEL_LINK_PRODUTO)
                    m_pid = self._RE_PID.search(link.get("href", "")) if link else None
                    chave = m_pid.group(1) if m_pid else None
                    if chave and chave in vistos:
                        continue

                    produto = self._extrair_card(card, categoria)
                    if produto is None:
                        indisponiveis += 1
                        continue

                    if palavras_chave and not any(
                        pk.lower() in produto.nome.lower() for pk in palavras_chave
                    ):
                        continue

                    if chave:
                        vistos.add(chave)
                    produtos.append(produto)

            logger.info(
                "Categoria '%s' (Gimba): %d produtos extraídos, %d sem preço/indisponíveis.",
                categoria,
                len(produtos),
                indisponiveis,
            )
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Gimba)", categoria)

        return produtos
