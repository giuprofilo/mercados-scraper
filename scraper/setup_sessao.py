import os
import random
from playwright.sync_api import sync_playwright
import config as config

CHROME_VERSION = "147"
USER_AGENT = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION}.0.0.0 Safari/537.36"

HEADERS = {
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-CH-UA": f'"Chromium";v="{CHROME_VERSION}", "Google Chrome";v="{CHROME_VERSION}", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
window.chrome = window.chrome || {};
"""

SITES = {
    "superadega": "https://atacadistasuperadega.com.br",
}


def main():
    os.makedirs(config.PERFIL_NAVEGADOR_DIR, exist_ok=True)

    # config.opcoes_navegador() já traz o channel (Chrome comercial instalado);
    # mesclar em vez de **kwargs evita "multiple values" em user_agent/channel.
    opcoes = {
        "channel": "chrome",  # Força o uso do Chrome comercial instalado na sua máquina
        "headless": False,  # Precisa ser False para você interagir
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        "viewport": {"width": 1366, "height": 900},
        "user_agent": USER_AGENT,
        "extra_http_headers": HEADERS,
        **config.opcoes_navegador(),
    }

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.PERFIL_NAVEGADOR_DIR, **opcoes
        )

        context.add_init_script(INIT_SCRIPT)

        for nome, url in SITES.items():
            page = context.new_page()
            page.goto(url, timeout=60_000)

            print("\n" + "=" * 70)
            print(f"[{nome}] Uma janela do navegador foi aberta em: {url}")
            print("1) Digite o CEP e selecione a loja mais próxima manualmente")
            print("2) Confirme que os produtos aparecem com preço normalmente.")
            print("3) Volte aqui e aperte ENTER para salvar os cookies da sessão.")
            print("=" * 70)
            input(f"\nPressione ENTER quando terminar em [{nome}]... ")
            page.close()

        print(f"\nPerfil salvo em: {config.PERFIL_NAVEGADOR_DIR}")
        context.close()


if __name__ == "__main__":
    main()
