"""
Ferramenta de debug: abre uma URL de verdade, salva o HTML renderizado e
um screenshot em logs/, e mostra no terminal o card de produto encontrado
pelo seletor do scraper certo (escolhido pelo domínio da URL). Uso e
passo a passo completo: ver README, seção "Como achar os seletores".

Uso:
    python debug_inspecionar.py "https://www.fortatacadista.com.br/categorias/mercearia/acucares-e-adocantes"
"""

import sys
import os
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

import config
from scrapers import SCRAPERS_DISPONIVEIS

LOGS_DIR = os.path.join(config.BASE_DIR, "logs")

# Domínio (ou pedaço dele) -> chave do scraper em SCRAPERS_DISPONIVEIS.
# Adicione uma linha aqui pra cada fornecedor novo.
DOMINIO_PARA_FORNECEDOR = {
    # "atacadao.com.br": "atacadao",
    # "stokonline.com.br": "stock",
    # "asunonline.com.br": "asun",
    "fortatacadista.com.br": "fort",
    # "gimba.com.br": "gimba",
}


def descobrir_scraper_pela_url(url: str):
    """Retorna (nome_fornecedor, classe_scraper) a partir do domínio da
    URL, ou (None, None) se não reconhecer o site."""
    host = urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host  # remove "www."

    for pedaco_dominio, fornecedor in DOMINIO_PARA_FORNECEDOR.items():
        if pedaco_dominio in host:
            return fornecedor, SCRAPERS_DISPONIVEIS.get(fornecedor)

    return None, None


def main():
    if len(sys.argv) < 2:
        print(
            'Uso: python debug_inspecionar.py "https://www.asunonline.com.br/categorias/mercearia/acucares"'
        )
        sys.exit(1)

    url = sys.argv[1]
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(config.PERFIL_NAVEGADOR_DIR, exist_ok=True)

    fornecedor, ScraperClass = descobrir_scraper_pela_url(url)
    if ScraperClass is None:
        print(
            f"AVISO: não reconheci o domínio de '{url}' em DOMINIO_PARA_FORNECEDOR "
            f"(conhecidos: {', '.join(DOMINIO_PARA_FORNECEDOR)}). Vou salvar o HTML/"
            "screenshot normalmente, mas sem comparar com nenhum SEL_CARD_PRODUTO "
            "específico — adicione o domínio no dicionário se for um fornecedor novo."
        )
    else:
        print(
            f"Domínio reconhecido -> fornecedor '{fornecedor}' ({ScraperClass.__name__})."
        )

    with sync_playwright() as p:
        if config.USAR_SESSAO_SALVA:
            print(f"Abrindo com perfil persistente: {config.PERFIL_NAVEGADOR_DIR}")
        else:
            print(
                "AVISO: config.USAR_SESSAO_SALVA=False — abrindo perfil limpo, sem CEP/loja definidos."
            )

        context = p.chromium.launch_persistent_context(
            user_data_dir=config.PERFIL_NAVEGADOR_DIR,
            headless=False,
            slow_mo=100,
            locale="pt-BR",
            viewport={"width": 1366, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        print(f"Abrindo: {url}")
        page.goto(url, timeout=config.NAV_TIMEOUT_MS)
        page.wait_for_timeout(3000)

        for _ in range(4):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(1000)

        html_path = os.path.join(LOGS_DIR, "debug_pagina.html")
        screenshot_path = os.path.join(LOGS_DIR, "debug_screenshot.png")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        page.screenshot(path=screenshot_path, full_page=True)

        print(f"\nHTML salvo em:        {html_path}")
        print(f"Screenshot salvo em:  {screenshot_path}")

        if ScraperClass is not None:
            cards = page.locator(ScraperClass.SEL_CARD_PRODUTO)
            total = cards.count()
            print(
                f"\n[{fornecedor}] SEL_CARD_PRODUTO = '{ScraperClass.SEL_CARD_PRODUTO}'"
            )
            print(f"Encontrou {total} elemento(s) com esse seletor.")

            if total > 0:
                print("\n--- HTML do primeiro card encontrado ---\n")
                print(cards.first.inner_html()[:2000])
                print("\n--- fim do trecho (cortado em 2000 caracteres) ---")

        print(
            "\nDeixe a janela aberta e use o DevTools (F12) do navegador que abriu "
            "para inspecionar o elemento real e comparar com o trecho acima."
        )
        input("\nPressione ENTER para fechar o navegador... ")

        context.close()


if __name__ == "__main__":
    main()
