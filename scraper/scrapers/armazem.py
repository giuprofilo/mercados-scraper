"""
Scraper para o Armazém da Maria (armazemdamaria.com.br).
Plataforma: Mercafacil (Next.js + styled-components). As classes CSS são
hashes gerados ("sc-aaf59d57-1") e mudam a cada deploy, então os seletores
aqui usam só estrutura estável (href "/produto/", atributo title, texto
"R$") — nunca as classes hash.

Como o site funciona (confirmado contra o site real):
- A loja vem na URL: /loja-1 é Curitiba/PR (existe também Campinas/SP;
  não há loja em Porto Alegre). Não há CEP a definir.
- Cada produto é um <a href="/loja-1/produto/m/<slug>-<id>"> com o nome em
  <span title="...">, seguido de um <div> de preço: preço atual primeiro
  ("R$ 59,90 /kg"); em promoção vem depois "- 14%" e o preço riscado.
- Produtos vendidos por peso mostram "/kg" e o preço é POR KG.
- 30 produtos por página; a paginação é por URL (?page=N) e o total vem em
  "N resultados para ...".
- Departamentos e subcategorias têm URL própria: /loja-1/<slug>-<id>.
"""

import math
import os
import re
import logging
from typing import Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
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

BASE_URL = "https://www.armazemdamaria.com.br"
ITENS_POR_PAGINA = 30
MAX_PAGINAS_SEGURANCA = 100


class ArmazemScraper(BaseScraper):
    nome_fornecedor = "armazem"

    SEL_CARD_PRODUTO = 'a[href*="/produto/"]'
    SEL_NOME_PRODUTO = "span[title]"

    _RE_PRECO = re.compile(r"R\$\s*([\d.]+,\d{2})")
    _RE_DESCONTO = re.compile(r"-\s*(\d+)\s*%")
    _RE_TOTAL = re.compile(r"([\d.]+)\s+resultados", re.IGNORECASE)

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "Armazém da Maria: a loja vem na URL (/loja-1 = Curitiba/PR) — "
            "nada a definir."
        )

    @staticmethod
    def _url_da_pagina(url: str, numero: int) -> str:
        if numero == 1:
            return url
        partes = urlsplit(url)
        query = [(k, v) for k, v in parse_qsl(partes.query) if k != "page"]
        query.append(("page", str(numero)))
        return urlunsplit(partes._replace(query=urlencode(query)))

    def _total_de_itens(self) -> Optional[int]:
        m = self._RE_TOTAL.search(self.page.inner_text("body"))
        return int(m.group(1).replace(".", "")) if m else None

    def _extrair_card(self, card, categoria: str) -> Optional[Produto]:
        nome_el = card.select_one(self.SEL_NOME_PRODUTO)
        if not nome_el:
            return None
        nome = (nome_el.get("title") or nome_el.get_text(strip=True)).strip()

        bloco_preco = nome_el.find_next_sibling("div")
        if bloco_preco is None:
            return None
        precos = [
            parse_preco(p) for p in self._RE_PRECO.findall(bloco_preco.get_text(" "))
        ]
        precos = [p for p in precos if p is not None]
        if not precos:
            return None
        preco = precos[0]

        preco_original = desconto = None
        if len(precos) > 1 and precos[1] > preco:
            preco_original = precos[1]
            m = self._RE_DESCONTO.search(bloco_preco.get_text(" "))
            desconto = f"-{m.group(1)}%" if m else None

        unidade_el = bloco_preco.select_one(".unit")
        por_kg = bool(unidade_el and "kg" in unidade_el.get_text().lower())

        quantidade, unidade = extrair_quantidade_e_unidade(nome)
        if quantidade is None:
            # o texto de embalagem ("500G", "0.82 kg") vem num div[title]
            # logo depois do preço
            embalagem = card.select_one("div[title]")
            if embalagem:
                quantidade, unidade = extrair_quantidade_e_unidade(
                    embalagem.get_text(" ", strip=True)
                )
        if quantidade is None and por_kg:
            # preço por peso: o valor exibido é por 1 kg
            quantidade, unidade = 1.0, "kg"

        href = card.get("href", "")
        url_produto = href if href.startswith("http") else f"{BASE_URL}{href}"

        return Produto(
            fornecedor=self.nome_fornecedor,
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

    def _tirar_print(self, indice: int, pagina: int, nome: str) -> Optional[str]:
        """Print do card (o `indice`-ésimo da página atual). None se falhar."""
        try:
            os.makedirs(config.PRINTS_DIR, exist_ok=True)
            nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(" ", "_")[:60]
            caminho = os.path.join(
                config.PRINTS_DIR, f"armazem_p{pagina}_{indice}_{nome_seguro}.png"
            )
            card = self.page.locator(self.SEL_CARD_PRODUTO).nth(indice)
            card.evaluate(
                "el => el.scrollIntoView({block: 'center', inline: 'center'})"
            )
            self.page.wait_for_timeout(100)
            card.screenshot(path=caminho)
            return caminho
        except Exception as e:
            logger.warning("Falha ao tirar print de '%s' (Armazém): %s", nome, e)
            return None

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Armazém)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = 0

        try:
            paginas = 1
            pagina = 1
            while pagina <= min(paginas, MAX_PAGINAS_SEGURANCA):
                self.page.goto(
                    self._url_da_pagina(url, pagina), timeout=config.NAV_TIMEOUT_MS
                )
                try:
                    self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=15000)
                except Exception:
                    logger.info("Página %d sem produtos — fim da categoria.", pagina)
                    break
                self.page.wait_for_timeout(800)

                if pagina == 1:
                    total = self._total_de_itens()
                    paginas = math.ceil(total / ITENS_POR_PAGINA) if total else 1
                    logger.info("%s itens em %d página(s).", total, paginas)

                soup = BeautifulSoup(self.page.content(), "html.parser")
                for i, card in enumerate(soup.select(self.SEL_CARD_PRODUTO)):
                    href = card.get("href", "")
                    if href in vistos:
                        continue

                    produto = self._extrair_card(card, categoria)
                    if produto is None:
                        sem_preco += 1
                        continue

                    if palavras_chave and not any(
                        pk.lower() in produto.nome.lower() for pk in palavras_chave
                    ):
                        continue

                    if getattr(config, "SALVAR_PRINTS_ITENS", False):
                        produto.imagem_print = self._tirar_print(
                            i, pagina, produto.nome
                        )

                    vistos.add(href)
                    produtos.append(produto)
                pagina += 1

            logger.info(
                "Categoria '%s' (Armazém): %d produtos extraídos, %d sem preço.",
                categoria,
                len(produtos),
                sem_preco,
            )
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Armazém)", categoria)

        return produtos
