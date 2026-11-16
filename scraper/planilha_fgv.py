"""
Envio da coleta para a planilha "Pesquisa FNDE Nordeste - Alimentos" (Google Sheets, ID em
GOOGLE_SHEETS_SPREADSHEET_ID). Exemplos exportados dos três layouts: csv/*(Empresas|Insumos|Coleta).csv.

Abas da planilha (nunca são alteradas pelo bot; só lidas):
  Insumos (ID FGV, Categoria, Grupo de Insumo, Descrição, Embalagem, Observações, Busca (dropdown)),
  Empresas (Código Empresa, Nome Empresa, CNPJ, UF Empresa) e, se existir, Pesquisadores.

Cada execução grava numa aba PRÓPRIA, com o nome de GOOGLE_SHEETS_WORKSHEET_NAME
(.env). Se a aba já existe ela é limpa e reescrita; se não, é criada. Nomes das
abas originais são recusados (ver ABAS_PROTEGIDAS).

Uma linha = um produto coletado, nas 20 colunas da aba Coleta (COLUNAS_SAIDA; valores, sem
fórmulas e sem linha de cabeçalho):
  Nome Empresa / CNPJ / UF Empresa / UF Preço   <- aba Empresas (empresa = EMPRESA_COLETA)
  Buscar Insumo / Código FGV / Categoria / Grupo de Insumo / Descrição do insumo  <- aba Insumos
  Pesquisador <- PESQUISADOR (.env) ou 1º nome da aba Pesquisadores
  Data coleta <- dd/mm/aa    FONTE <- url do produto
  PRODUTO PESQUISADO <- nome no site; se a embalagem não é 1 kg / 1 L, termina com
                        " | Unidade do item: 1 KG" (ou "1 l"), como na planilha de referência
  Preço PRODUTO <- preço cheio (ou o atual)    Desconto R$ <- cheio - atual (só em promoção)
  OBS Desconto <- promoção / preço de atacado    PREÇO FINAL <- preço atual
  OBS FRETE <- OBS_FRETE (.env; padrão "retirada na loja do próprio estado: frete não se aplica")
  Desconto %, VALOR FRETE ficam vazios.

Vínculo produto -> insumo, em ordem:
  1. Tarefa com `categoria` no formato do dropdown ("FRUTA ## 39"): o ID FGV vem da tarefa, sem
     adivinhar (data/tarefas/mateusmais.py).
  2. Sem ID: compara as palavras da Descrição do insumo ("ABACATE, CRU" -> abacate; "cru/crua",
     "de", "sem"... são ignoradas) com o nome do produto. A 1ª palavra tem que aparecer; ganha o
     insumo com mais palavras em comum. Sem insumo ou empate entre insumos diferentes (ex.:
     "Banana" pura -> da terra x prata): a linha VAI para a planilha com as colunas de insumo em
     branco (preencher pelo dropdown) e um aviso no log. NADA é descartado por vínculo.

Limite: no máximo MAX_PRECOS_POR_INSUMO (5) linhas por insumo. Ficam os de MAIOR
peso (quantidade normalizada; empate = mais barato) e a saída é ordenada por
insumo (ordem da aba Insumos) e, dentro dele, do MENOR para o MAIOR preço. O mesmo produto
(URL) que aparece em mais de uma tarefa do insumo conta uma vez.
Linhas sem insumo não sofrem limite e vão no fim.

`exportar_csv()` gera o mesmo layout em exports/ (CSV `;`, cp1252, igual ao da planilha) usando
os CSVs de csv/ em vez do Google Sheets: serve para conferir a coleta sem credenciais.
"""

import csv
import glob
import logging
import os
import re
import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING

import gspread
from google.oauth2.service_account import Credentials

import config

if TYPE_CHECKING:
    from database import Produto

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

MAX_PRECOS_POR_INSUMO = 5
ABA_COLETA_MODELO = "Coleta"
ABAS_PROTEGIDAS = {
    "leia-me",
    "coleta",
    "insumos",
    "empresas",
    "pesquisadores",
    "acompanhamento",
}

_PALAVRAS_IGNORADAS = {
    "cru", "crua", "crus", "cruas", "de", "da", "do", "das", "dos", "e", "em",
    "com", "sem", "tipo",
}  # fmt: skip

# Fator p/ comparar pesos na mesma base (g/ml); un/cx/pct = 1.
_FATOR_PESO = {"kg": 1000, "g": 1, "l": 1000, "ml": 1, "dz": 12}


def nome_aba_valido() -> bool:
    nome = (config.GOOGLE_SHEETS_WORKSHEET_NAME or "").strip()
    if not nome:
        logger.error(
            "GOOGLE_SHEETS_WORKSHEET_NAME não definido no .env. Defina um nome novo "
            "para a aba desta coleta (ex.: atacadao-2026-10-01)."
        )
        return False
    if nome.casefold() in ABAS_PROTEGIDAS:
        logger.error(
            "GOOGLE_SHEETS_WORKSHEET_NAME='%s' é uma aba original da planilha. "
            "Use um nome novo para a coleta (a aba é apagada a cada execução).",
            nome,
        )
        return False
    return True


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.casefold()


def _palavras(texto: str) -> list[str]:
    return [
        p
        for p in re.findall(r"[a-z0-9]+", _normalizar(texto))
        if p not in _PALAVRAS_IGNORADAS and not p.isdigit()
    ]


def _casa(palavra: str, palavras_do_nome: list[str]) -> bool:
    # Igualdade ou plural simples: "ovo" casa "ovos", mas "maca" não casa "macarrao".
    return any(p in (palavra, palavra + "s", palavra + "es") for p in palavras_do_nome)


def escolher_insumo(nome_produto: str, insumos: list[dict]) -> dict | None:
    """Insumo que melhor descreve o produto, ou None se não houver / for ambíguo."""
    palavras_nome = _palavras(nome_produto)
    melhor_pontos = 0
    melhores: list[dict] = []
    for insumo in insumos:
        palavras = insumo["_palavras"]
        if not palavras or not _casa(palavras[0], palavras_nome):
            continue
        pontos = sum(_casa(p, palavras_nome) for p in palavras)
        if pontos > melhor_pontos:
            melhor_pontos, melhores = pontos, [insumo]
        elif pontos == melhor_pontos:
            melhores.append(insumo)
    if len(melhores) > 1:
        # Empate: vale o insumo cuja 1ª palavra aparece antes no nome do produto
        # ("Macarrão com Ovos" -> macarrão, não ovo).
        def posicao(insumo: dict) -> int:
            return next(
                i for i, p in enumerate(palavras_nome) if _casa(insumo["_palavras"][0], [p])
            )

        melhor_pos = min(posicao(i) for i in melhores)
        melhores = [i for i in melhores if posicao(i) == melhor_pos]
    return melhores[0] if len(melhores) == 1 else None


_ID_NA_CATEGORIA = re.compile(r"##\s*(\d+)\s*$")
OBS_FRETE_PADRAO = "retirada na loja do próprio estado: frete não se aplica"


def _conectar():
    credenciais = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=_SCOPES
    )
    cliente = gspread.authorize(credenciais)
    return cliente.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)


def _como_dicts(valores: list[list[str]]) -> list[dict]:
    """Linhas (1ª = cabeçalho) como dicts {cabeçalho: valor}, sem as linhas vazias."""
    if not valores:
        return []
    cabecalho = valores[0]
    return [dict(zip(cabecalho, l)) for l in valores[1:] if any(c.strip() for c in l)]


def _ler_tabela(planilha, aba: str) -> list[dict]:
    return _como_dicts(planilha.worksheet(aba).get_all_values())


def _ler_csv_local(aba: str) -> list[dict]:
    """Aba exportada em csv/*(<aba>).csv (CSV `;`, cp1252, como a planilha exporta)."""
    achados = sorted(glob.glob(os.path.join(config.BASE_DIR, "csv", f"*({aba}).csv")))
    if not achados:
        raise FileNotFoundError(f"csv/*({aba}).csv não encontrado.")
    with open(achados[-1], encoding="cp1252", newline="") as f:
        return _como_dicts(list(csv.reader(f, delimiter=";")))


def _id_fgv(insumo: dict) -> str:
    return (insumo.get("ID FGV") or insumo.get("Código do Insumo") or "").strip()


def _preparar_insumos(brutos: list[dict]) -> list[dict]:
    insumos = [i for i in brutos if i.get("Descrição") and _id_fgv(i)]
    for i in insumos:
        i["_palavras"] = _palavras(i["Descrição"])
        if not i.get("Busca (dropdown)", "").strip() or i["Busca (dropdown)"].startswith("#"):
            i["Busca (dropdown)"] = _busca_dropdown(i)
    return insumos


def _busca_dropdown(insumo: dict) -> str:
    """Mesma fórmula da coluna "Busca (dropdown)" da aba Insumos:
    Grupo | Descrição (cortada em 70 caracteres + "...") ## ID. Pela API do Sheets a coluna
    vem como "#ERROR!" (a fórmula usa referência de tabela), então é recalculada aqui."""
    descricao = insumo["Descrição"]
    if len(descricao) > 70:
        descricao = descricao[:70].strip() + "..."
    return f"{insumo.get('Grupo de Insumo', '')} | {descricao} ## {_id_fgv(insumo)}"


def _escolher_empresa(brutas) -> dict:
    """`brutas` = linhas da aba Empresas, ou a planilha aberta (usado pelo ceasa_pdf.py)."""
    if not isinstance(brutas, list):
        brutas = _ler_tabela(brutas, "Empresas")
    empresas = [e for e in brutas if e.get("Nome Empresa")]
    desejada = (getattr(config, "EMPRESA_COLETA", None) or "").strip().casefold()
    if desejada:
        achadas = [e for e in empresas if desejada in e["Nome Empresa"].casefold()]
        if len(achadas) > 1:  # vários contêm o texto: vale o nome exato, se houver
            exatas = [e for e in achadas if e["Nome Empresa"].strip().casefold() == desejada]
            achadas = exatas or achadas
    else:
        achadas = empresas
    if len(achadas) != 1:
        nomes = ", ".join(e["Nome Empresa"] for e in empresas)
        raise ValueError(
            "Defina EMPRESA_COLETA no .env com o nome (ou parte) de UMA empresa "
            f"da aba Empresas. Empresas cadastradas: {nomes}"
        )
    return achadas[0]


def _escolher_pesquisador(nomes: list[str]) -> str:
    nome = (getattr(config, "PESQUISADOR", None) or "").strip()
    if nome:
        return nome
    if not nomes:
        raise ValueError("Defina PESQUISADOR no .env (não há aba Pesquisadores).")
    return nomes[0]


def _pesquisadores(planilha) -> list[str]:
    try:
        return [p["Nome"].strip() for p in _ler_tabela(planilha, "Pesquisadores") if p.get("Nome")]
    except gspread.WorksheetNotFound:
        return []


def _moeda(valor: float | None) -> str:
    """Formato da planilha: "R$ 7,49"."""
    if valor is None:
        return ""
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Colunas da saída = aba Coleta do layout Nordeste (csv/...(Coleta).csv), na ordem.
COLUNAS_SAIDA = [
    "Nome Empresa", "CNPJ", "UF Empresa", "Buscar Insumo", "Código FGV", "Categoria",
    "Grupo de Insumo", "Descrição do insumo", "UF Preço", "Data coleta", "Pesquisador", "FONTE",
    "PRODUTO PESQUISADO", "Preço PRODUTO", "Desconto %", "Desconto R$", "OBS Desconto",
    "PREÇO FINAL", "VALOR FRETE", "OBS FRETE",
]  # fmt: skip


def _peso(p: "Produto") -> float:
    if not p.quantidade:
        return 0.0
    return p.quantidade * _FATOR_PESO.get((p.unidade or "").lower(), 1)


def _insumo_do_produto(p: "Produto", insumos: list[dict], por_id: dict[str, dict]):
    achado = _ID_NA_CATEGORIA.search(p.categoria or "")
    if achado:
        insumo = por_id.get(achado.group(1))
        if insumo:
            return insumo
        logger.warning("ID FGV %s da tarefa não está na aba Insumos: %s", achado.group(1), p.nome)
    return escolher_insumo(p.nome, insumos)


def _selecionar(pares: "list[tuple[Produto, dict | None]]", insumos: list[dict]):
    """Aplica o limite por insumo e a ordenação (ver docstring do módulo)."""
    grupos: dict[int, dict] = {}
    sem_insumo = []
    for p, insumo in pares:
        if insumo is None:
            sem_insumo.append((p, None))
        else:
            # mesmo produto achado por duas buscas da tarefa: conta uma vez
            grupos.setdefault(insumos.index(insumo), {}).setdefault(
                p.url_produto or p.nome, (p, insumo)
            )

    saida = []
    for idx in sorted(grupos):
        mais_pesados = sorted(grupos[idx].values(), key=lambda x: (-_peso(x[0]), x[0].preco))
        escolhidos = mais_pesados[:MAX_PRECOS_POR_INSUMO]
        saida += sorted(escolhidos, key=lambda x: (x[0].preco, -_peso(x[0])))
    return saida + sem_insumo


def _sufixo_unidade(p: "Produto") -> str:
    """Planilha de referência: embalagem diferente de 1 kg / 1 L ganha " | Unidade do item: 1 KG"."""
    unidade = (p.unidade or "").lower()
    if not p.quantidade or unidade not in ("g", "kg", "ml", "l"):
        return ""
    base = p.quantidade * _FATOR_PESO[unidade]
    if base == 1000:
        return ""
    return " | Unidade do item: 1 KG" if unidade in ("g", "kg") else " | Unidade do item: 1 l"


def _montar_linha(
    p: "Produto", insumo: dict | None, empresa: dict, pesquisador: str
) -> dict[str, object]:
    insumo = insumo or {}
    cheio = p.preco_original if p.preco_original and p.preco_original > p.preco else None
    atacado = (
        p.preco_atacado
        if p.preco_atacado and p.qtd_minima_atacado and p.preco_atacado < p.preco
        else None
    )
    base = cheio if cheio is not None else p.preco
    final = atacado if atacado is not None else p.preco
    obs = []
    if cheio is not None:
        obs.append(f"Promoção no site ({p.desconto})" if p.desconto else "Promoção no site")
    if atacado is not None:
        obs.append(
            f"preço de atacado a partir de {p.qtd_minima_atacado} unid.: {_moeda(atacado)}"
        )
    elif p.preco_atacado and p.qtd_minima_atacado:
        obs.append(f"sem faixa de atacado melhor que o preço do site")
    data = datetime.fromisoformat(p.coletado_em).strftime("%d/%m/%y")
    return {
        "Nome Empresa": empresa["Nome Empresa"],
        "CNPJ": empresa.get("CNPJ", ""),
        "UF Empresa": empresa.get("UF Empresa", ""),
        "Buscar Insumo": insumo.get("Busca (dropdown)", ""),
        "Código FGV": _id_fgv(insumo),
        "Categoria": insumo.get("Categoria", ""),
        "Grupo de Insumo": insumo.get("Grupo de Insumo", ""),
        "Descrição do insumo": insumo.get("Descrição", ""),
        "UF Preço": empresa.get("UF Empresa", ""),
        "Data coleta": data,
        "Pesquisador": pesquisador,
        "FONTE": p.url_produto or "",
        "PRODUTO PESQUISADO": p.nome + _sufixo_unidade(p),
        "Preço PRODUTO": _moeda(base),
        "Desconto R$": _moeda(base - final) if base > final else "",
        "OBS Desconto": "; ".join(obs),
        "PREÇO FINAL": _moeda(final),
        "OBS FRETE": (getattr(config, "OBS_FRETE", None) or OBS_FRETE_PADRAO),
    }


def _gerar_linhas(
    produtos: "list[Produto]", insumos: list[dict], empresa: dict, pesquisador: str
) -> list[list[object]]:
    por_id = {_id_fgv(i): i for i in insumos}
    pares = [(p, _insumo_do_produto(p, insumos, por_id)) for p in produtos]
    for p, insumo in pares:
        if insumo is None:
            logger.warning("Sem insumo único (linha enviada sem insumo): %s", p.nome)
    linhas = []
    for p, insumo in _selecionar(pares, insumos):
        campos = _montar_linha(p, insumo, empresa, pesquisador)
        linhas.append([campos.get(col, "") for col in COLUNAS_SAIDA])
    logger.info(
        "%d produto(s) coletados, %d linha(s) no formato da planilha.", len(produtos), len(linhas)
    )
    return linhas


def enviar_coleta(produtos: "list[Produto]") -> None:
    planilha = _conectar()
    insumos = _preparar_insumos(_ler_tabela(planilha, "Insumos"))
    empresa = _escolher_empresa(_ler_tabela(planilha, "Empresas"))
    pesquisador = _escolher_pesquisador(_pesquisadores(planilha))
    cabecalho = COLUNAS_SAIDA

    linhas = _gerar_linhas(produtos, insumos, empresa, pesquisador)
    if not linhas:
        logger.warning("Nenhuma linha para enviar; aba não alterada.")
        return

    nome_aba = config.GOOGLE_SHEETS_WORKSHEET_NAME.strip()
    try:
        aba = planilha.worksheet(nome_aba)
        aba.clear()
    except gspread.WorksheetNotFound:
        aba = planilha.add_worksheet(
            title=nome_aba, rows=len(linhas) + 50, cols=len(cabecalho)
        )
    if aba.row_count < len(linhas):
        aba.resize(rows=len(linhas) + 50)

    aba.update(values=linhas, range_name="A1", value_input_option="USER_ENTERED")
    logger.info("Aba '%s' atualizada com %d linha(s).", nome_aba, len(linhas))


def exportar_csv(produtos: "list[Produto]") -> str | None:
    """Mesmo layout da aba Coleta em exports/coleta_<empresa>_<data>.csv, lendo Insumos e
    Empresas de csv/ (sem Google Sheets). Devolve o caminho, ou None se não houver linhas."""
    insumos = _preparar_insumos(_ler_csv_local("Insumos"))
    empresa = _escolher_empresa(_ler_csv_local("Empresas"))
    pesquisador = _escolher_pesquisador([])
    linhas = _gerar_linhas(produtos, insumos, empresa, pesquisador)
    if not linhas:
        logger.warning("Nenhuma linha para exportar.")
        return None

    pasta = os.path.join(config.BASE_DIR, "exports")
    os.makedirs(pasta, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", _normalizar(empresa["Nome Empresa"])).strip("-")
    caminho = os.path.join(pasta, f"coleta_{slug}_{datetime.now():%Y-%m-%d}.csv")
    with open(caminho, "w", encoding="cp1252", errors="replace", newline="") as f:
        escritor = csv.writer(f, delimiter=";", lineterminator="\r\n")
        escritor.writerow(COLUNAS_SAIDA)
        escritor.writerows(linhas)
    logger.info("CSV da coleta salvo em %s (%d linha(s)).", caminho, len(linhas))
    return caminho
