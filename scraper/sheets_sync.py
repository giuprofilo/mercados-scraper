import logging
import sqlite3
from typing import TYPE_CHECKING

import gspread
from google.oauth2.service_account import Credentials

import config as config
import planilha_fgv
from database import get_connection, init_db

if TYPE_CHECKING:
    from database import Produto

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Colunas do produto, na ordem em que viram colunas na planilha. Usado
# tanto por sincronizar_planilha() (lê do SQLite, então inclui "id")
# quanto por sincronizar_produtos() (lê direto da memória, sem "id").
_CAMPOS_PRODUTO = [
    "fornecedor",
    "categoria",
    "nome",
    "marca",
    "preco",
    "preco_original",
    "quantidade",
    "unidade",
    "preco_atacado",
    "qtd_minima_atacado",
    "desconto",
    "url_produto",
    "imagem_print",
    "coletado_em",
]
_CABECALHO = ["id"] + _CAMPOS_PRODUTO


def _conectar_planilha(num_colunas: int):
    credenciais = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=_SCOPES
    )
    cliente = gspread.authorize(credenciais)
    planilha = cliente.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)

    try:
        aba = planilha.worksheet(config.GOOGLE_SHEETS_WORKSHEET_NAME)
    except gspread.WorksheetNotFound:
        aba = planilha.add_worksheet(
            title=config.GOOGLE_SHEETS_WORKSHEET_NAME, rows=1000, cols=num_colunas
        )
    return aba


def _pronto_para_sincronizar() -> bool:
    if not config.GOOGLE_SHEETS_ENABLED:
        logger.info(
            "Sincronização com Google Sheets desabilitada em config.py — pulando."
        )
        return False

    if not config.GOOGLE_SHEETS_SPREADSHEET_ID:
        logger.error(
            "GOOGLE_SHEETS_SPREADSHEET_ID não definido. Crie um arquivo .env na raiz "
            "do projeto (copie .env.example) e preencha essa variável — veja a "
            "seção 2 do README."
        )
        return False

    return planilha_fgv.nome_aba_valido()


def _enviar_linhas(linhas: list[list]) -> None:
    logger.info("Conectando ao Google Sheets...")
    aba = _conectar_planilha(num_colunas=len(linhas[0]))

    logger.info("Enviando %d linhas para a planilha...", len(linhas))
    aba.clear()
    aba.update(values=linhas, range_name="A1")
    logger.info("Sincronização concluída com sucesso.")


def sincronizar_produtos(produtos: "list[Produto]") -> None:
    """
    Manda a coleta que acabou de rodar para uma aba própria (nome em
    GOOGLE_SHEETS_WORKSHEET_NAME) da planilha de pesquisa, no formato da aba
    "Coleta". A aba é limpa e reescrita a cada execução. Detalhes do formato
    e do vínculo produto -> insumo em planilha_fgv.py. É o que main.py chama.
    """
    if not _pronto_para_sincronizar():
        return

    if not produtos:
        logger.warning("Nenhum produto coletado para sincronizar.")
        return

    logger.info("Conectando ao Google Sheets...")
    planilha_fgv.enviar_coleta(produtos)


def _buscar_todos_os_registros() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM produtos ORDER BY coletado_em DESC"
        ).fetchall()


def sincronizar_planilha() -> None:
    """
    Manda o HISTÓRICO INTEIRO do banco SQLite pra planilha (todas as
    coletas já feitas, não só a última). Mantido pra quem quiser esse
    comportamento antigo — chame manualmente com
    `python sheets_sync.py`. O fluxo padrão do main.py usa
    sincronizar_produtos(), que é mais simples e não depende do banco.
    """
    if not _pronto_para_sincronizar():
        return

    init_db()
    registros = _buscar_todos_os_registros()
    if not registros:
        logger.warning("Nenhum registro no banco para sincronizar.")
        return

    linhas = [_CABECALHO]
    for r in registros:
        linhas.append([r[col] for col in _CABECALHO])

    _enviar_linhas(linhas)


if __name__ == "__main__":
    sincronizar_planilha()
