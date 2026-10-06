import os
import logging
from playwright.sync_api import sync_playwright

import config as config
from database import Produto
from scrapers import SCRAPERS_DISPONIVEIS
from data.produtos import TAREFAS_DE_COLETA

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def criar_browser_context(playwright):
    browser = playwright.chromium.launch(
        headless=config.HEADLESS, slow_mo=config.SLOW_MO_MS
    )
    context = browser.new_context(
        locale="pt-BR",
        viewport={"width": 1366, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    )
    return browser, context


def executar_coletas(
    tarefas: list[dict] = TAREFAS_DE_COLETA, cep: str = config.CEP
) -> list[Produto]:
    todos_produtos: list[Produto] = []

    with sync_playwright() as p:
        browser = None

        if config.USAR_SESSAO_SALVA:
            os.makedirs(config.PERFIL_NAVEGADOR_DIR, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                user_data_dir=config.PERFIL_NAVEGADOR_DIR,
                headless=config.HEADLESS,
                slow_mo=config.SLOW_MO_MS,
                locale="pt-BR",
                viewport={"width": 1366, "height": 900},
                **config.opcoes_navegador(),
            )
            page = context.pages[0] if context.pages else context.new_page()
        else:
            browser, context = criar_browser_context(p)
            page = context.new_page()

        fornecedores_ja_configurados: set[str] = set()

        for tarefa in tarefas:
            nome_fornecedor = tarefa["fornecedor"]
            ScraperClass = SCRAPERS_DISPONIVEIS.get(nome_fornecedor)

            if ScraperClass is None:
                logger.error("Fornecedor '%s' não encontrado.", nome_fornecedor)
                continue

            scraper = ScraperClass(page)

            if nome_fornecedor not in fornecedores_ja_configurados:
                try:
                    scraper.definir_cep(cep)
                except Exception:
                    logger.exception("Falha ao definir CEP para %s", nome_fornecedor)
                fornecedores_ja_configurados.add(nome_fornecedor)

            try:
                produtos = scraper.extrair_produtos_da_pagina(
                    categoria=tarefa["categoria"],
                    url=tarefa["url"],
                    palavras_chave=tarefa.get("palavras_chave"),
                )
                todos_produtos.extend(produtos)
            except Exception:
                logger.exception("Falha ao coletar categoria '%s'", tarefa["categoria"])

        context.close()
        if browser is not None:
            browser.close()

    return todos_produtos
