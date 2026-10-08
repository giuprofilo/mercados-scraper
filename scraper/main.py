import argparse
import logging

import config
import database
from scraper import executar_coletas
import sheets_sync

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def imprimir_tabela(
    titulo: str,
    linhas,
    colunas=(
        "nome",
        "marca",
        "preco",
        "preco_original",
        "preco_atacado",
        "url_produto",
        "imagem_print",
    ),
):
    print(f"\n=== {titulo} ({len(linhas)} itens) ===")
    if not linhas:
        print("  (nenhum registro encontrado)")
        return
    for linha in linhas[:20]:
        valores = []
        for c in colunas:
            val = linha[c]
            if val is None:
                valores.append("-")
            else:
                valores.append(str(val))
        print("  - " + " | ".join(valores))
    if len(linhas) > 20:
        print(
            f"  ... e mais {len(linhas) - 20} itens (veja no banco/planilha completos)"
        )


def rodar_relatorios(termo_filtro: str | None = None):
    imprimir_tabela("Produtos ordenados por nome (A-Z)", database.listar_por_nome())

    if termo_filtro:
        imprimir_tabela(
            f"Produtos filtrados por '{termo_filtro}'",
            database.filtrar_por_categoria_ou_palavra(termo_filtro),
        )


def main():
    parser = argparse.ArgumentParser(
        description="Bot de coleta de preços em sites de atacado"
    )
    parser.add_argument(
        "--sem-sheets", action="store_true", help="Não sincroniza com o Google Sheets"
    )
    parser.add_argument(
        "--salvar-banco",
        action="store_true",
        help="Grava a coleta também no SQLite (por padrão: config.SALVAR_NO_BANCO)",
    )
    parser.add_argument(
        "--so-relatorio",
        action="store_true",
        help="Só exibe relatórios do banco atual, sem coletar",
    )
    parser.add_argument(
        "--filtro",
        type=str,
        default=None,
        help="Termo para o relatório de filtro por palavra-chave",
    )
    args = parser.parse_args()

    salvar_no_banco = args.salvar_banco or config.SALVAR_NO_BANCO
    if salvar_no_banco or args.so_relatorio:
        database.init_db()

    if not args.so_relatorio:
        from data.produtos import TAREFAS_DE_COLETA

        logger.info("Iniciando coleta para %d tarefa(s)...", len(TAREFAS_DE_COLETA))
        produtos = executar_coletas(TAREFAS_DE_COLETA, cep=config.CEP)

        if salvar_no_banco:
            logger.info("Gravando %d produtos no banco SQLite...", len(produtos))
            for produto in produtos:
                database.inserir_produto(produto)
        else:
            logger.info(
                "%d produtos coletados (banco SQLite desabilitado).", len(produtos)
            )

        if not args.sem_sheets:
            try:
                sheets_sync.sincronizar_produtos(produtos)
            except FileNotFoundError:
                logger.error(
                    "Credencial do Google não encontrada em %s. "
                    "Rode com --sem-sheets ou configure as credenciais (veja README.md).",
                    config.GOOGLE_SHEETS_CREDENTIALS_PATH,
                )
            except Exception:
                logger.exception(
                    "Falha ao sincronizar com Google Sheets."
                )
    else:
        logger.info(
            "Modo --so-relatorio: pulando coleta, usando dados já existentes no banco."
        )

    if salvar_no_banco or args.so_relatorio:
        rodar_relatorios(termo_filtro=args.filtro)
    elif args.filtro:
        termo = args.filtro.lower()
        imprimir_tabela(
            f"Produtos coletados filtrados por '{args.filtro}'",
            sorted(
                (
                    vars(p)
                    for p in produtos
                    if termo in p.nome.lower() or termo in (p.categoria or "").lower()
                ),
                key=lambda linha: linha["nome"],
            ),
        )


if __name__ == "__main__":
    main()
