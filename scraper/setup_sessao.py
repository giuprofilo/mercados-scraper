import os
from playwright.sync_api import sync_playwright

import config as config

# Como o projeto usa UM único perfil de navegador persistente
# (config.PERFIL_NAVEGADOR_DIR) para todos os fornecedores na mesma
# execução, dá pra configurar o CEP/loja de todos os sites de uma vez só
# aqui — cada site guarda cookies/sessionStorage no seu próprio domínio,
# então não há conflito entre eles dentro do mesmo perfil.
SITES = {
    # "stock": "https://www.stokonline.com.br/",
    # "atacadao": "https://www.atacadao.com.br/",
    # "asun": "https://www.levemaisonline.com.br/",
    # "fort": "https://www.fortatacadista.com.br/",
    "gimba": "https://www.gimba.com.br/",
}


def main():
    os.makedirs(config.PERFIL_NAVEGADOR_DIR, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.PERFIL_NAVEGADOR_DIR,
            headless=False,
            locale="pt-BR",
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        for nome, url in SITES.items():
            page = context.new_page()
            page.goto(url, timeout=60_000)

            print("\n" + "=" * 70)
            print(f"[{nome}] Uma janela do navegador foi aberta em: {url}")
            if nome == "gimba":
                print(
                    "   GIMBA: não tem CEP. Clique em 'Olá, faça login', entre com a "
                    "conta do CNPJ (e-mail + código de 6 dígitos) e confirme que o "
                    "cabeçalho deixou de mostrar 'faça login' antes de apertar ENTER."
                )
            print("1) Digite o CEP e selecione a loja mais próxima manualmente")
            print("   (se o site já mostrar uma loja padrão por geolocalização,")
            print("   confirme se é a loja certa e pule este passo).")
            if nome == "fort":
                print(
                    "   ATENÇÃO: em teste manual, o Fort caiu por padrão numa loja "
                    "de Balneário Camboriú/SC — confirme que a loja trocou para "
                    "Porto Alegre/RS antes de apertar ENTER."
                )
            print("2) Confirme que os produtos aparecem com preço normalmente.")
            print("3) Navegue até uma categoria e confirme que os produtos")
            print("   aparecem normalmente ali também.")
            print("4) Volte aqui e aperte ENTER para ir para o próximo site.")
            print("=" * 70)
            input(f"\nPressione ENTER quando terminar em [{nome}]... ")
            page.close()

        print(f"\nPerfil salvo em: {config.PERFIL_NAVEGADOR_DIR}")
        print("Agora rode `python main.py` normalmente — o CEP não será mais pedido.")

        context.close()


if __name__ == "__main__":
    main()
