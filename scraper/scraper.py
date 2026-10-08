import os
import logging
from playwright.sync_api import sync_playwright

import config as config
from setup_sessao import USER_AGENT, HEADERS, INIT_SCRIPT
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
        timezone_id="America/Sao_Paulo",
        user_agent=USER_AGENT,
        extra_http_headers=HEADERS,
    )
    context.add_init_script(INIT_SCRIPT)
    return browser, context


def executar_coletas(
    tarefas: list[dict] = TAREFAS_DE_COLETA, cep: str = config.CEP
) -> list[Produto]:
    todos_produtos: list[Produto] = []

    with sync_playwright() as p:
        browser = None

        if config.USAR_SESSAO_SALVA:
            os.makedirs(config.PERFIL_NAVEGADOR_DIR, exist_ok=True)
            # Mesmos UA/Client Hints/init script do setup_sessao.py (Chrome 131);
            # opcoes_navegador() vem por último para não duplicar chaves.
            opcoes = {
                "headless": config.HEADLESS,
                "slow_mo": config.SLOW_MO_MS,
                "locale": "pt-BR",
                "timezone_id": "America/Sao_Paulo",
                "viewport": {"width": 1366, "height": 900},
                "user_agent": USER_AGENT,
                "extra_http_headers": HEADERS,
                **config.opcoes_navegador(),
            }
            context = p.chromium.launch_persistent_context(
                user_data_dir=config.PERFIL_NAVEGADOR_DIR, **opcoes
            )
            context.add_init_script(INIT_SCRIPT)
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
