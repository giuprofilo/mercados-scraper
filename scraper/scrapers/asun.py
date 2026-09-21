"""
Scraper para o Asun Supermercados (levemaisonline.com.br).
Plataforma: Osuper. O site não vende no modelo atacarejo tradicional, mas
tem promoções (preço riscado + badge de desconto). Detalhes e histórico
de ajustes: ver README, seção "Fornecedores já mapeados".
"""

import os
import re
import logging
from typing import Optional
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import (
    parse_preco,
    extrair_quantidade_e_unidade,
    extrair_marca,
)

logger = logging.getLogger(__name__)


class AsunScraper(BaseScraper):
    nome_fornecedor = "asun"

    # --- CEP / loja ---
    SEL_INPUT_CEP = "input[placeholder*='CEP' i], input[name*='cep' i]"
    SEL_BOTAO_CONFIRMAR_CEP = "button:has-text('Buscar'), button:has-text('Confirmar')"
    SEL_BOTAO_ESCOLHER_LOJA = (
        "button:has-text('Selecionar'), button:has-text('Escolher')"
    )
    SEL_ABRIR_TROCA_LOJA = "text=Loja de"

    # --- Card de produto no grid de categoria ---
    # Confirmado contra HTML real: o <a> do card não tem href (navegação
    # via onClick), então a URL do produto é pega do
    # <script type="application/ld+json"> (ItemList) — ver
    # _mapear_urls_por_ordem().
    SEL_CARD_PRODUTO = ".item-product-wrapper"
    SEL_NOME_PRODUTO = "img[alt]"  # nome do produto vem no alt da imagem
    SEL_PRECO_CHEIO = ".text-full-price"  # preço riscado (antes do desconto)
    SEL_BADGE_DESCONTO = "[class*='bg-regular-promotion/15']"  # ex: "-10%"

    SEL_BOTAO_MOSTRAR_MAIS = (
        "button:has-text('Mostrar mais'), button:has-text('Ver mais'), "
        "button:has-text('Carregar mais')"
    )

    def definir_cep(self, cep: str) -> None:
        if (
            config.USAR_SESSAO_SALVA
            and os.path.isdir(config.PERFIL_NAVEGADOR_DIR)
            and os.listdir(config.PERFIL_NAVEGADOR_DIR)
        ):
            logger.info("Perfil persistente detectado — pulando modal de CEP (Asun).")
            return

        logger.info("Abrindo Asun para definir CEP...")
        self.page.goto("https://www.asunonline.com.br/", timeout=config.NAV_TIMEOUT_MS)

        try:
            if self.page.locator(self.SEL_ABRIR_TROCA_LOJA).count() > 0:
                self.page.locator(self.SEL_ABRIR_TROCA_LOJA).first.click()
                self.page.wait_for_timeout(1000)

            self.page.wait_for_selector(self.SEL_INPUT_CEP, timeout=8000)
            self.page.fill(self.SEL_INPUT_CEP, cep)
            self.page.click(self.SEL_BOTAO_CONFIRMAR_CEP)
            self.page.wait_for_timeout(2000)

            if self.page.locator(self.SEL_BOTAO_ESCOLHER_LOJA).count() > 0:
                self.page.locator(self.SEL_BOTAO_ESCOLHER_LOJA).first.click()
                self.page.wait_for_timeout(1500)

            logger.info("CEP definido com sucesso (Asun): %s", cep)
        except PlaywrightTimeoutError:
            logger.warning(
                "Modal de CEP não apareceu (Asun) — o site pode já ter atribuído "
                "uma loja padrão por geolocalização. Rode setup_sessao.py e "
                "confirme a loja certa manualmente antes de coletar de verdade."
            )

    def _extrair_precos(self, card) -> dict:
        resultado = {
            "preco": None,
            "preco_original": None,
            "preco_atacado": None,
            "qtd_minima_atacado": None,
            "desconto": None,
        }

        preco_cheio_el = card.select_one(self.SEL_PRECO_CHEIO)
        if preco_cheio_el:
            resultado["preco_original"] = parse_preco(
                preco_cheio_el.get_text(strip=True)
            )

        badge = card.select_one(self.SEL_BADGE_DESCONTO)
        if badge:
            resultado["desconto"] = badge.get_text(strip=True)

        texto_atacado = card.find(string=re.compile(r"a partir de", re.IGNORECASE))
        if texto_atacado:
            match_qtd = re.search(
                r"a partir de\s*(\d+)", str(texto_atacado), re.IGNORECASE
            )
            if match_qtd:
                resultado["qtd_minima_atacado"] = int(match_qtd.group(1))

        textos_rs = card.find_all(string=re.compile(r"R\$"))
        precos_floats = []
        for t in textos_rs:
            val = parse_preco(str(t))
            if val is not None and val not in precos_floats:
                precos_floats.append(val)
        precos_floats.sort(reverse=True)

        if precos_floats:
            if resultado["preco_original"] is not None:
                candidatos = [
                    p for p in precos_floats if p != resultado["preco_original"]
                ]
                resultado["preco"] = candidatos[0] if candidatos else precos_floats[-1]
            else:
                resultado["preco"] = precos_floats[-1]
                resultado["preco_original"] = precos_floats[-1]

        return resultado

    def _mapear_urls_por_ordem(self, soup: BeautifulSoup) -> list[Optional[str]]:
        """URL de cada produto vem do <script application/ld+json>
        (ItemList), casando por posição com a ordem dos cards no grid."""
        import json

        urls: list[Optional[str]] = []
        for script_tag in soup.find_all(
            "script", attrs={"type": "application/ld+json"}
        ):
            try:
                dados = json.loads(script_tag.string or "{}")
            except (ValueError, TypeError):
                continue
            if dados.get("@type") != "ItemList":
                continue
            itens = sorted(
                dados.get("itemListElement", []),
                key=lambda x: x.get("position", 0),
            )
            urls = [item.get("url") for item in itens]
            break  # só deve existir um ItemList por página de categoria
        return urls

    def _rolar_ou_paginar(self) -> None:
        for _ in range(6):
            self.page.mouse.wheel(0, 2500)
            self.page.wait_for_timeout(900)

        botao = self.page.locator(self.SEL_BOTAO_MOSTRAR_MAIS)
        tentativas = 0
        while botao.count() > 0 and tentativas < config.MAX_PAGINAS_POR_CATEGORIA:
            try:
                botao.first.click()
                self.page.wait_for_timeout(1500)
                for _ in range(3):
                    self.page.mouse.wheel(0, 2000)
                    self.page.wait_for_timeout(700)
            except Exception:
                break
            tentativas += 1

    def _salvar_debug_pagina_vazia(self, categoria: str) -> None:
        logs_dir = os.path.join(config.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        nome_arquivo = (
            f"debug_vazio_asun_{categoria.replace(' ', '_').replace(',', '')}.html"
        )
        caminho = os.path.join(logs_dir, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.page.content())
        logger.warning(
            "0 produtos em '%s' (Asun). HTML salvo em %s", categoria, caminho
        )

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Asun)", categoria, url)
        produtos: list[Produto] = []

        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            self.page.wait_for_timeout(2500)
            self._rolar_ou_paginar()

            soup = BeautifulSoup(self.page.content(), "html.parser")
            cards = soup.select(self.SEL_CARD_PRODUTO)
            urls_por_ordem = self._mapear_urls_por_ordem(soup)

            for i, card in enumerate(cards):
                nome_el = card.select_one(self.SEL_NOME_PRODUTO)
                if not nome_el:
                    continue

                nome = (
                    nome_el.get("alt")
                    or nome_el.get("title")
                    or card.get_text(strip=True)
                )
                if not nome:
                    continue

                if palavras_chave and not any(
                    pk.lower() in nome.lower() for pk in palavras_chave
                ):
                    continue

                dados_preco = self._extrair_precos(card)
                if dados_preco["preco"] is None:
                    continue

                quantidade, unidade = extrair_quantidade_e_unidade(nome)
                marca = extrair_marca(nome)

                # não existe href no <a> do card — URL vem do JSON-LD
                url_produto = urls_por_ordem[i] if i < len(urls_por_ordem) else None
                if url_produto and url_produto.startswith("http://"):
                    url_produto = "https://" + url_produto[len("http://") :]

                caminho_print = None
                if getattr(config, "SALVAR_PRINTS_ITENS", False):
                    try:
                        os.makedirs(config.PRINTS_DIR, exist_ok=True)
                        nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(
                            " ", "_"
                        )[:60]
                        caminho_print = os.path.join(
                            config.PRINTS_DIR, f"asun_{i}_{nome_seguro}.png"
                        )
                        card_locator = self.page.locator(self.SEL_CARD_PRODUTO).nth(i)
                        card_locator.evaluate(
                            "el => el.scrollIntoView({block: 'center', inline: 'center'})"
                        )
                        self.page.wait_for_timeout(100)
                        card_locator.screenshot(path=caminho_print)
                    except Exception as e:
                        logger.warning(
                            "Falha ao tirar print de '%s' (Asun): %s", nome, e
                        )

                produtos.append(
                    Produto(
                        fornecedor=self.nome_fornecedor,
                        categoria=categoria,
                        nome=nome,
                        marca=marca,
                        preco=dados_preco["preco"],
                        quantidade=quantidade,
                        unidade=unidade,
                        preco_original=dados_preco["preco_original"],
                        preco_atacado=dados_preco["preco_atacado"],
                        qtd_minima_atacado=dados_preco["qtd_minima_atacado"],
                        desconto=dados_preco["desconto"],
                        url_produto=url_produto,
                        imagem_print=caminho_print,
                    )
                )

            logger.info(
                "Categoria '%s' (Asun): %d produtos extraídos.",
                categoria,
                len(produtos),
            )

        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Asun)", categoria)

        if len(produtos) == 0:
            self._salvar_debug_pagina_vazia(categoria)

        return produtos
