"""
Scraper para o Super Adega Atacadista (atacadistasuperadega.com.br).
Plataforma: Instabuy/Ibecom (Next.js app router, sem __NEXT_DATA__; dados em
api.ibecom.com.br/api_ecommerce/v5/items). Os seletores usam só `data-testid`
(estáveis); as classes Tailwind do card não são usadas, exceto o parágrafo
do nome (`p.line-clamp-2`), com fallback no `alt` da imagem.

Como o site funciona (confirmado contra o HTML real enviado pelo usuário;
o que está marcado como "não confirmado" ainda não foi visto rodando):
- Cloudflare: bloqueia curl e Chrome headless na 1ª visita. Usar o Chrome real
  (config.NAVEGADOR_CANAL = "chrome") com o perfil persistente de
  `python setup_sessao.py`.
- Região/loja: o CEP de entrega (ex.: 70310-500) é escolhido no site e fica no
  perfil persistente; preço e disponibilidade dependem dele. O scraper NÃO
  define CEP (`definir_cep` só loga) — refazer via `setup_sessao.py`. As
  chamadas da API levam os headers `x-store-id` e `IBSessionId` da sessão.
- Listagem: /sub/<categoria>/<subcategoria> (ex.:
  /sub/frutas-legumes-e-verduras/frutas). A mesma URL com o id no lugar do
  slug deu "Algo deu errado" ao abrir direto. /cat/<slug> só mostra carrosséis
  com poucos itens por subcategoria. A API pagina com
  `items?subcategory_id=..&limit=20&sort=popular&page=N`.
- Card: <a data-testid="product-card" href="/p/<slug>">; preço em
  `[data-testid=price-display-price]` (texto "R$ 5,29"; em itens por peso há um
  <span>kg</span> e o preço é POR KG); promoção: `price-display-badge` ("-29%")
  e `price-display-original` (<del>, preço riscado). O nome é o <p> do card e
  termina em "Un"/"Kg" conforme a venda. Sem atacado/"a partir de N".
- Paginação (não confirmado): a listagem deve carregar mais itens ao rolar a
  página; o scraper rola até a contagem de cards parar de crescer e clica em
  "Ver mais"/"Carregar mais" se existir.
"""

import os
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

BASE_URL = "https://www.atacadistasuperadega.com.br"
MAX_PAGINAS_SEGURANCA = 100
ROLAGENS_SEM_NOVOS_PARA_PARAR = 3


class SuperAdegaScraper(BaseScraper):
    nome_fornecedor = "superadega"

    SEL_CARD_PRODUTO = '[data-testid="product-card"]'
    SEL_NOME_PRODUTO = "p.line-clamp-2"
    SEL_PRECO = '[data-testid="price-display-price"]'
    SEL_PRECO_ORIGINAL = '[data-testid="price-display-original"]'
    SEL_DESCONTO = '[data-testid="price-display-badge"]'

    _RE_DESCONTO = re.compile(r"-\s*(\d+)\s*%")
    _RE_UNIDADE_NO_NOME = re.compile(r"\b(un|unid|unidade)$", re.IGNORECASE)

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "Super Adega: o CEP de entrega fica no perfil persistente "
            "(setup_sessao.py) — nada a definir."
        )

    def _extrair_card(self, card, categoria: str) -> Optional[Produto]:
        nome_el = card.select_one(self.SEL_NOME_PRODUTO)
        nome = nome_el.get_text(" ", strip=True) if nome_el else ""
        if not nome:
            img = card.select_one("img[alt]")
            nome = (img.get("alt") or "").strip() if img else ""
        preco_el = card.select_one(self.SEL_PRECO)
        if not nome or preco_el is None:
            return None

        # só o texto direto: o <span> filho ("kg") não faz parte do número
        preco = parse_preco("".join(preco_el.find_all(string=True, recursive=False)))
        if not preco:
            return None
        unidade_el = preco_el.find("span")
        por_kg = bool(unidade_el and "kg" in unidade_el.get_text().lower())

        preco_original = desconto = None
        original_el = card.select_one(self.SEL_PRECO_ORIGINAL)
        original = parse_preco(original_el.get_text()) if original_el else None
        if original and original > preco:
            preco_original = original
            badge = card.select_one(self.SEL_DESCONTO)
            m = self._RE_DESCONTO.search(badge.get_text()) if badge else None
            desconto = (
                f"-{m.group(1)}%" if m else f"-{round((1 - preco / original) * 100)}%"
            )

        quantidade, unidade = extrair_quantidade_e_unidade(nome)
        if quantidade is None and por_kg:
            # preço por peso: o valor exibido é por 1 kg
            quantidade, unidade = 1.0, "kg"
        elif quantidade is None and self._RE_UNIDADE_NO_NOME.search(nome):
            quantidade, unidade = 1.0, "un"

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

    def _carregar_todos_os_cards(self) -> None:
        """Rola a página (e clica em "ver mais", se houver) até a contagem de
        cards parar de crescer."""
        anterior = -1
        sem_novos = 0
        for _ in range(MAX_PAGINAS_SEGURANCA):
            total = self.page.locator(self.SEL_CARD_PRODUTO).count()
            if total == anterior:
                sem_novos += 1
                if sem_novos >= ROLAGENS_SEM_NOVOS_PARA_PARAR:
                    break
            else:
                sem_novos = 0
            anterior = total

            botao = self.page.get_by_role(
                "button", name=re.compile(r"(ver|carregar|mostrar) mais", re.I)
            )
            if botao.count() > 0:
                try:
                    botao.first.click(timeout=2000)
                except Exception:
                    pass
            self.page.mouse.wheel(0, 3000)
            self.page.wait_for_timeout(1200)
        logger.info("%d cards carregados na página.", max(anterior, 0))

    def _tirar_print(self, indice: int, nome: str) -> Optional[str]:
        """Print do card (o `indice`-ésimo da página). None se falhar."""
        try:
            os.makedirs(config.PRINTS_DIR, exist_ok=True)
            nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(" ", "_")[:60]
            caminho = os.path.join(
                config.PRINTS_DIR, f"superadega_{indice}_{nome_seguro}.png"
            )
            card = self.page.locator(self.SEL_CARD_PRODUTO).nth(indice)
            card.evaluate(
                "el => el.scrollIntoView({block: 'center', inline: 'center'})"
            )
            self.page.wait_for_timeout(100)
            card.screenshot(path=caminho)
            return caminho
        except Exception as e:
            logger.warning("Falha ao tirar print de '%s' (Super Adega): %s", nome, e)
            return None

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Super Adega)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = 0

        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            try:
                self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=15000)
            except Exception:
                logger.error("Nenhum card em '%s' (Super Adega).", categoria)
                self._salvar_debug_vazio(categoria)
                return produtos
            self._carregar_todos_os_cards()

            soup = BeautifulSoup(self.page.content(), "html.parser")
            cards = soup.select(self.SEL_CARD_PRODUTO)
            for i, card in enumerate(cards):
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
                    produto.imagem_print = self._tirar_print(i, produto.nome)

                vistos.add(href)
                produtos.append(produto)

            if cards and not produtos and not palavras_chave:
                self._salvar_debug_vazio(categoria)
            logger.info(
                "Categoria '%s' (Super Adega): %d produtos extraídos, %d sem preço.",
                categoria,
                len(produtos),
                sem_preco,
            )
        except Exception:
            logger.exception(
                "Erro ao processar categoria '%s' (Super Adega)", categoria
            )

        return produtos

    def _salvar_debug_vazio(self, categoria: str) -> None:
        try:
            logs_dir = os.path.join(config.BASE_DIR, "logs")
            os.makedirs(logs_dir, exist_ok=True)
            nome = re.sub(r"[^\w-]+", "_", categoria)
            with open(
                os.path.join(logs_dir, f"debug_vazio_{nome}.html"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(self.page.content())
        except Exception:
            logger.warning("Não consegui salvar o HTML de debug de '%s'.", categoria)
