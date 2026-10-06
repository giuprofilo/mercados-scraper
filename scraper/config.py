import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# CEP / Loja
CEP = "90560-005"

# Banco de dados na raiz do projeto
DB_PATH = os.path.join(BASE_DIR, "atacado_precos.db")

# Playwright
HEADLESS = True
NAV_TIMEOUT_MS = 45_000
SLOW_MO_MS = 0

# Navegador usado no perfil persistente (setup_sessao.py E coleta devem usar o
# mesmo, senão o cf_clearance do Cloudflare não vale). "chrome" = Google Chrome
# instalado na máquina (necessário p/ o iFood); None = Chromium do Playwright.
# Com "chrome" o user-agent não é forçado (usa o real do navegador) e a flag
# --enable-automation é removida. Ao trocar, apague credentials/perfil_atacadao.
NAVEGADOR_CANAL = "chrome"


def opcoes_navegador() -> dict:
    """Argumentos extras do launch_persistent_context conforme NAVEGADOR_CANAL."""
    if NAVEGADOR_CANAL:
        return {
            "channel": NAVEGADOR_CANAL,
            "ignore_default_args": ["--enable-automation"],
        }
    return {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }


USAR_SESSAO_SALVA = True
PERFIL_NAVEGADOR_DIR = os.path.join(BASE_DIR, "credentials", "perfil_atacadao")

MAX_PAGINAS_POR_CATEGORIA = 5

# Google Sheets
# ATENÇÃO: GOOGLE_SHEETS_SPREADSHEET_ID vem do .env
# Veja o arquivo .env.example para o formato esperado.
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEETS_CREDENTIALS_PATH = os.path.join(
    BASE_DIR, "credentials", "google_service_account.json"
)
GOOGLE_SHEETS_SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
# Nome da aba NOVA desta coleta (apagada/reescrita a cada execução; as abas
# originais da planilha são recusadas). Troque a cada coleta.
GOOGLE_SHEETS_WORKSHEET_NAME = os.environ.get("GOOGLE_SHEETS_WORKSHEET_NAME")
# Empresa pesquisada (nome ou parte do nome na aba Empresas) e pesquisador
# (vazio = 1º nome da aba Pesquisadores).
EMPRESA_COLETA = os.environ.get("EMPRESA_COLETA")
PESQUISADOR = os.environ.get("PESQUISADOR")

# Screenshots de Produtos
SALVAR_PRINTS_ITENS = False
PRINTS_DIR = os.path.join(BASE_DIR, "screenshots")
