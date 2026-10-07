"""
Envio da coleta para a planilha "Pesquisa de Preços - Alimentos FNDE Centro-Oeste"
(Google Sheets, ID em GOOGLE_SHEETS_SPREADSHEET_ID).

Abas da planilha (nunca são alteradas pelo bot; só lidas):
  Insumos, Empresas, Pesquisadores, Coleta (usada só para copiar o cabeçalho).

Cada execução grava numa aba PRÓPRIA, com o nome de GOOGLE_SHEETS_WORKSHEET_NAME
(.env). Se a aba já existe ela é limpa e reescrita; se não, é criada. Nomes das
abas originais são recusados (ver ABAS_PROTEGIDAS).

Uma linha = um produto coletado. O bot grava VALORES nas 22 colunas da aba
Coleta (as fórmulas da aba-modelo não são copiadas):
  Buscar Empresa / CNPJ / Nome Empresa / UF Empresa / UF Preço  <- aba Empresas
                                                  (empresa = EMPRESA_COLETA)
  Buscar Insumo / Código FGV / Categoria / Grupo / Descrição / Observações
                                                  <- aba Insumos
  Pesquisador <- PESQUISADOR (.env) ou 1º nome da aba Pesquisadores
  Data coleta <- dd-mm-aaaa    FONTE <- url do produto
  PRODUTO PESQUISADO <- nome no site    Preço PRODUTO <- preço cheio (ou o atual)
  Desconto R$ <- cheio - atual (só em promoção)   PREÇO FINAL <- preço atual
  Desconto %, VALOR FRETE, OBS FRETE ficam vazios.

Vínculo produto -> insumo (o scraper não sabe qual insumo procurou): compara as
palavras da Descrição do insumo ("ABACATE, CRU" -> abacate; "cru/crua", "de",
"sem"... são ignoradas) com o nome do produto. A 1ª palavra tem que aparecer;
ganha o insumo com mais palavras em comum. Sem insumo ou empate entre insumos
diferentes (ex.: "Banana" pura -> da terra x prata): a linha VAI para a planilha
com as colunas de insumo em branco (preencher pelo dropdown) e um aviso no log.
NADA é descartado por vínculo.

Limite: no máximo MAX_PRECOS_POR_INSUMO (5) linhas por insumo. Ficam os de MAIOR
peso (quantidade normalizada; empate = mais barato) e a saída é ordenada por
insumo (ordem da aba Insumos) e, dentro dele, do MENOR para o MAIOR preço.
Linhas sem insumo não sofrem limite e vão no fim.
"""

import logging
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
    # startswith cobre plural: "ovo" casa "ovos".
    return any(p.startswith(palavra) for p in palavras_do_nome)


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
    return melhores[0] if len(melhores) == 1 else None


def _conectar():
    credenciais = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=_SCOPES
    )
    cliente = gspread.authorize(credenciais)
    return cliente.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)


def _ler_tabela(planilha, aba: str) -> list[dict]:
    """Linhas da aba como dicts {cabeçalho: valor}, sem as linhas vazias."""
    valores = planilha.worksheet(aba).get_all_values()
    cabecalho = valores[0]
    linhas = []
    for linha in valores[1:]:
        if any(c.strip() for c in linha):
            linhas.append(dict(zip(cabecalho, linha)))
    return linhas


def _carregar_insumos(planilha) -> list[dict]:
    insumos = [i for i in _ler_tabela(planilha, "Insumos") if i.get("Descrição")]
    for i in insumos:
        i["_palavras"] = _palavras(i["Descrição"])
    return insumos


def _escolher_empresa(planilha) -> dict:
    empresas = [e for e in _ler_tabela(planilha, "Empresas") if e.get("Nome Empresa")]
    desejada = (getattr(config, "EMPRESA_COLETA", None) or "").strip().casefold()
    if desejada:
        achadas = [e for e in empresas if desejada in e["Nome Empresa"].casefold()]
    else:
        achadas = empresas
    if len(achadas) != 1:
        nomes = ", ".join(e["Nome Empresa"] for e in empresas)
        raise ValueError(
            "Defina EMPRESA_COLETA no .env com o nome (ou parte) de UMA empresa "
            f"da aba Empresas. Empresas cadastradas: {nomes}"
        )
    return achadas[0]


def _escolher_pesquisador(planilha) -> str:
    nome = (getattr(config, "PESQUISADOR", None) or "").strip()
    if nome:
        return nome
    nomes = [p["Nome"].strip() for p in _ler_tabela(planilha, "Pesquisadores")]
    if not nomes:
        raise ValueError("Nenhum pesquisador na aba Pesquisadores nem PESQUISADOR no .env.")
    return nomes[0]


def _moeda(valor: float | None) -> float | str:
    return round(valor, 2) if valor is not None else ""


def _peso(p: "Produto") -> float:
    if not p.quantidade:
        return 0.0
    return p.quantidade * _FATOR_PESO.get((p.unidade or "").lower(), 1)


def _selecionar(pares: "list[tuple[Produto, dict | None]]", insumos: list[dict]):
    """Aplica o limite por insumo e a ordenação (ver docstring do módulo)."""
    grupos: dict[int, list] = {}
    sem_insumo = []
    for p, insumo in pares:
        if insumo is None:
            sem_insumo.append((p, None))
        else:
            grupos.setdefault(insumos.index(insumo), []).append((p, insumo))

    saida = []
    for idx in sorted(grupos):
        mais_pesados = sorted(grupos[idx], key=lambda x: (-_peso(x[0]), x[0].preco))
        escolhidos = mais_pesados[:MAX_PRECOS_POR_INSUMO]
        saida += sorted(escolhidos, key=lambda x: (x[0].preco, -_peso(x[0])))
    return saida + sem_insumo


def _limpar_observacao(texto: str) -> str:
    """Tira da observação do insumo a instrução interna "não coletar bandeja"
    (serve só para quem coleta; não deve ir para a aba de coleta)."""
    partes = [t.strip() for t in re.split(r"[;\n]", texto or "")]
    return "; ".join(t for t in partes if t and t.lower() != "não coletar bandeja")


def _montar_linha(
    p: "Produto", insumo: dict | None, empresa: dict, pesquisador: str
) -> dict[str, object]:
    insumo = insumo or {}
    cheio = p.preco_original if p.preco_original and p.preco_original > p.preco else None
    obs = []
    if cheio is not None:
        obs.append(f"Promoção no site ({p.desconto})" if p.desconto else "Promoção no site")
    if p.preco_atacado and p.qtd_minima_atacado:
        obs.append(
            f"Atacado: R$ {p.preco_atacado:.2f} a partir de {p.qtd_minima_atacado} un."
        )
    data = datetime.fromisoformat(p.coletado_em).strftime("%d-%m-%Y")
    return {
        "Buscar Empresa": empresa["Busca (dropdown)"],
        "CNPJ": empresa["CNPJ"],
        "Nome Empresa": empresa["Nome Empresa"],
        "UF Empresa": empresa["UF Empresa"],
        "Buscar Insumo": insumo.get("Busca (dropdown)", ""),
        "Código FGV": insumo.get("Código do Insumo", ""),
        "Categoria": insumo.get("Categoria", ""),
        "Grupo de Insumo": insumo.get("Grupo de Insumo", ""),
        "Descrição do insumo": insumo.get("Descrição", ""),
        "Observações": _limpar_observacao(insumo.get("Observações", "")),
        "UF Preço": empresa["UF Empresa"],
        "Data coleta": data,
        "Pesquisador": pesquisador,
        "FONTE": p.url_produto or "",
        "PRODUTO PESQUISADO": p.nome,
        "Preço PRODUTO": _moeda(cheio if cheio is not None else p.preco),
        "Desconto R$": _moeda(cheio - p.preco) if cheio is not None else "",
        "OBS Desconto": "; ".join(obs),
        "PREÇO FINAL": _moeda(p.preco),
    }


def enviar_coleta(produtos: "list[Produto]") -> None:
    planilha = _conectar()
    insumos = _carregar_insumos(planilha)
    empresa = _escolher_empresa(planilha)
    pesquisador = _escolher_pesquisador(planilha)
    cabecalho = planilha.worksheet(ABA_COLETA_MODELO).row_values(1)

    pares = [(p, escolher_insumo(p.nome, insumos)) for p in produtos]
    for p, insumo in pares:
        if insumo is None:
            logger.warning("Sem insumo único (linha enviada sem insumo): %s", p.nome)
    linhas = []
    for p, insumo in _selecionar(pares, insumos):
        campos = _montar_linha(p, insumo, empresa, pesquisador)
        linhas.append([campos.get(col, "") for col in cabecalho])

    logger.info(
        "%d produto(s) coletados, %d linha(s) vão para a planilha.",
        len(produtos),
        len(linhas),
    )
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
    if aba.row_count < len(linhas) + 1:
        aba.resize(rows=len(linhas) + 50)

    aba.update(values=[cabecalho] + linhas, range_name="A1", value_input_option="RAW")
    logger.info("Aba '%s' atualizada com %d linha(s).", nome_aba, len(linhas))
