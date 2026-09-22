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


class AtacadaoScraper(BaseScraper):
    nome_fornecedor = "atacadao"

    SEL_INPUT_CEP = "input[placeholder*='CEP' i], input[name*='cep' i]"
    SEL_BOTAO_CONFIRMAR_CEP = "button:has-text('Buscar'), button:has-text('Confirmar')"
    SEL_BOTAO_ESCOLHER_LOJA = (
        "button:has-text('Selecionar'), button:has-text('Escolher')"
    )

    SEL_CARD_PRODUTO = "[data-testid='store-product-card-content']"
    SEL_NOME_PRODUTO = "[data-testid='product-link']"
    SEL_LINK_PRODUTO = "[data-testid='product-link']"
    SEL_MARCA = None

    SEL_BOTAO_MOSTRAR_MAIS = "button:has-text('Mostrar mais'), button:has-text('Ver mais'), button:has-text('Carregar mais')"

    def definir_cep(self, cep: str) -> None:
        if (
            config.USAR_SESSAO_SALVA
            and os.path.isdir(config.PERFIL_NAVEGADOR_DIR)
            and os.listdir(config.PERFIL_NAVEGADOR_DIR)
        ):
            logger.info("Perfil persistente detectado — pulando modal de CEP.")
            return

        logger.info("Abrindo Atacadão para definir CEP...")
        self.page.goto("https://www.atacadao.com.br/", timeout=config.NAV_TIMEOUT_MS)

        try:
            self.page.wait_for_selector(self.SEL_INPUT_CEP, timeout=8000)
            self.page.fill(self.SEL_INPUT_CEP, cep)
            self.page.click(self.SEL_BOTAO_CONFIRMAR_CEP)
            self.page.wait_for_timeout(2000)

            if self.page.locator(self.SEL_BOTAO_ESCOLHER_LOJA).count() > 0:
                self.page.locator(self.SEL_BOTAO_ESCOLHER_LOJA).first.click()
                self.page.wait_for_timeout(1500)

            logger.info("CEP definido com sucesso: %s", cep)
        except PlaywrightTimeoutError:
            logger.warning("Modal de CEP não apareceu (timeout).")

    def _extrair_precos_e_atacado(self, card) -> dict:
        resultado = {
            "preco_varejo": None,
            "preco_atacado": None,
            "qtd_minima_atacado": None,
            "desconto": None,
        }

        texto_atacado = card.find(string=re.compile(r"a partir de", re.IGNORECASE))
        if texto_atacado:
            match_qtd = re.search(
                r"a partir de\s*(\d+)", str(texto_atacado), re.IGNORECASE
            )
            if match_qtd:
                resultado["qtd_minima_atacado"] = int(match_qtd.group(1))

        badge = card.select_one("[data-test='discount-badge']")
        if badge:
            resultado["desconto"] = badge.get_text(strip=True)

        textos_rs = card.find_all(string=re.compile(r"R\$"))
        precos_floats = []
        for t in textos_rs:
            val = parse_preco(str(t))
            if val is not None and val not in precos_floats:
                precos_floats.append(val)

        precos_floats.sort(reverse=True)

        if precos_floats:
            if resultado["qtd_minima_atacado"] and len(precos_floats) >= 2:
                resultado["preco_varejo"] = precos_floats[0]
                resultado["preco_atacado"] = precos_floats[-1]
            else:
                resultado["preco_varejo"] = precos_floats[-1]

        return resultado

    def _salvar_debug_pagina_vazia(self, categoria: str) -> None:
        logs_dir = os.path.join(config.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        nome_arquivo = (
            f"debug_vazio_{categoria.replace(' ', '_').replace(',', '')}.html"
        )
        caminho = os.path.join(logs_dir, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.page.content())
        logger.warning("0 produtos em '%s'. HTML salvo em %s", categoria, caminho)

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s", categoria, url)
        produtos: list[Produto] = []

        for pagina in range(1, config.MAX_PAGINAS_POR_CATEGORIA + 1):
            separador = "&" if "?" in url else "?"
            url_pagina = f"{url}{separador}page={pagina}" if pagina > 1 else url

            logger.info("Acessando página %d: %s", pagina, url_pagina)
            try:
                self.page.goto(url_pagina, timeout=config.NAV_TIMEOUT_MS)
                self.page.wait_for_timeout(2000)

                for _ in range(4):
                    self.page.mouse.wheel(0, 2000)
                    self.page.wait_for_timeout(1000)

                soup = BeautifulSoup(self.page.content(), "html.parser")
                cards = soup.select(self.SEL_CARD_PRODUTO)

                if not cards:
                    logger.info("Fim da paginação na página %d.", pagina)
                    break

                produtos_na_pagina = 0

                for i, card in enumerate(cards):
                    nome_el = card.select_one(self.SEL_NOME_PRODUTO)
                    if not nome_el:
                        continue

                    nome = nome_el.get("title") or nome_el.get_text(strip=True)

                    if palavras_chave and not any(
                        pk.lower() in nome.lower() for pk in palavras_chave
                    ):
                        continue

                    dados_preco = self._extrair_precos_e_atacado(card)
                    preco_varejo = dados_preco["preco_varejo"]
                    preco_atacado = dados_preco["preco_atacado"]

                    if preco_varejo is None and preco_atacado is None:
                        continue

                    preco_base = (
                        preco_varejo if preco_varejo is not None else preco_atacado
                    )
                    quantidade, unidade = extrair_quantidade_e_unidade(nome)
                    marca = extrair_marca(nome)

                    link_el = card.select_one(self.SEL_LINK_PRODUTO)
                    url_produto = None
                    if link_el and link_el.get("href"):
                        href = link_el["href"]
                        url_produto = (
                            href
                            if href.startswith("http")
                            else f"https://www.atacadao.com.br{href}"
                        )

                    caminho_print = None
                    if getattr(config, "SALVAR_PRINTS_ITENS", False):
                        try:
                            os.makedirs(config.PRINTS_DIR, exist_ok=True)
                            nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(
                                " ", "_"
                            )[:60]
                            caminho_print = os.path.join(
                                config.PRINTS_DIR,
                                f"atacadao_p{pagina}_{i}_{nome_seguro}.png",
                            )

                            card_locator = self.page.locator(self.SEL_CARD_PRODUTO).nth(
                                i
                            )
                            card_locator.evaluate(
                                "el => el.scrollIntoView({block: 'center', inline: 'center'})"
                            )
                            self.page.wait_for_timeout(100)
                            card_locator.screenshot(path=caminho_print)
                        except Exception as e:
                            logger.warning("Falha ao tirar print de '%s': %s", nome, e)

                    produtos.append(
                        Produto(
                            fornecedor=self.nome_fornecedor,
                            categoria=categoria,
                            nome=nome,
                            marca=marca,
                            preco=preco_base,
                            quantidade=quantidade,
                            unidade=unidade,
                            preco_atacado=preco_atacado,
                            qtd_minima_atacado=dados_preco["qtd_minima_atacado"],
                            desconto=dados_preco["desconto"],
                            url_produto=url_produto,
                            imagem_print=caminho_print,
                        )
                    )
                    produtos_na_pagina += 1

                logger.info(
                    "Página %d: %d produtos extraídos.", pagina, produtos_na_pagina
                )

            except Exception:
                logger.exception(
                    "Erro ao processar página %d da categoria '%s'", pagina, categoria
                )
                break

        if len(produtos) == 0:
            self._salvar_debug_pagina_vazia(categoria)

        return produtos
