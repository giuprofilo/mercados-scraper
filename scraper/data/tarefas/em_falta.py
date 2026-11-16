"""
Tarefas de coleta SÓ dos insumos que ficaram em falta na 1ª rodada (data/insumos_em_falta.py),
para re-rodar em cada mercado e ver se algo voltou a aparecer. Não substitui os arquivos
data/tarefas/<mercado>.py; são listas à parte (TAREFAS_EM_FALTA_<MERCADO>).

Como cada mercado é montado (URLs/seções reaproveitadas das tarefas já conferidas):
- VIP Commerce (abeve, levemax, mega, casaaurora, delmoro): uma busca de UMA palavra por termo
  (sem acento) + `secoes` do corredor. Abevê/Leve Max/Mega usam o filtro por substring (só inclusões,
  com e sem acento); Casa Aurora/DelMoro usam o filtro estrito ("a+b", "-x").
- Redes Machado e Machadão: busca `/busca?s=<termo>` (sem seção; filtro por substring, só inclusões).
- Atacadão, Super Adega, Supervi, Comper: páginas de corredor + `palavras_chave` (substring, com e sem
  acento). Hortaliças vão para legumes E verduras (cada produto só aparece em uma das páginas).
  Corredores que o mercado não tem (conferido em docs/data de cada mercado) ficam sem tarefa.

Bandeja NÃO é excluída. Sem tarefa: Cetap (só industrializados; nenhum insumo em falta é vendido lá),
Rappi/Barateiro (fora, por decisão do usuário: traz muito resultado de outros mercados).
"""

from urllib.parse import quote

from data.insumos_em_falta import (
    INSUMOS_EM_FALTA,
    _sem_acento,
    palavras_chave,
    termos_busca,
)

_GRUPO_POR_CATEGORIA = {
    "FRUTA": "fruta",
    "HORTALIÇAS/VEGETAIS": "hortalica",
    "CARNE BOVINA": "bovina",
    "CARNE SUÍNA": "suina",
    "CARNE PEIXE": "peixe",
}


def _por_grupo(grupo: str) -> list[dict]:
    return [i for i in INSUMOS_EM_FALTA if _GRUPO_POR_CATEGORIA[i["categoria"]] == grupo]


def _uniao(grupo: str, estrito: bool = False) -> list[str]:
    """Palavras-chave de todos os insumos do grupo, sem repetir (uma tarefa por corredor)."""
    saida: list[str] = []
    for insumo in _por_grupo(grupo):
        for p in palavras_chave(insumo, estrito=estrito):
            if p not in saida:
                saida.append(p)
    return saida


# --- Busca por termo + secoes (VIP Commerce) -----------------------------------------------------
def _vip(fornecedor: str, busca: str, secoes: dict[str, list[int]], estrito: bool) -> list[dict]:
    tarefas = []
    for insumo in INSUMOS_EM_FALTA:
        grupo = _GRUPO_POR_CATEGORIA[insumo["categoria"]]
        ids = ",".join(str(i) for i in secoes[grupo])
        pk = palavras_chave(insumo, estrito=estrito)
        for termo in dict.fromkeys(_sem_acento(t) for t in termos_busca(insumo)):
            tarefas.append(
                {
                    "fornecedor": fornecedor,
                    "categoria": insumo["categoria"],
                    "url": f"{busca}{quote(termo)}&secoes={ids}",
                    "palavras_chave": pk,
                }
            )
    return tarefas


TAREFAS_EM_FALTA_ABEVE = _vip(
    "abeve",
    "https://www.abeve.com.br/busca?termo=",
    {"fruta": [131], "hortalica": [133, 135], "bovina": [85], "suina": [86], "peixe": [89]},
    estrito=False,
)
TAREFAS_EM_FALTA_LEVEMAX = _vip(
    "levemax",
    "https://www.levemaxsuperatacado.com.br/busca?termo=",
    {"fruta": [131], "hortalica": [133, 135], "bovina": [85, 87], "suina": [86, 87], "peixe": [89]},
    estrito=False,
)
TAREFAS_EM_FALTA_MEGA = _vip(
    "mega",
    "https://www.megaemcasa.atacadistamega.com.br/busca?termo=",
    {"fruta": [122], "hortalica": [124, 126], "bovina": [21, 23], "suina": [22, 23], "peixe": [26]},
    estrito=False,
)
_SECOES_AURORA = {
    "fruta": [135],
    "hortalica": [137, 140],
    "bovina": [87, 88],
    "suina": [89],
    "peixe": [92],
}
TAREFAS_EM_FALTA_CASAAURORA = _vip(
    "casaaurora",
    "https://www.casaaurorasupermercados.com.br/busca?termo=",
    _SECOES_AURORA,
    estrito=True,
)
TAREFAS_EM_FALTA_DELMORO = _vip(
    "delmoro",
    "https://www.delmorosupermercados.com.br/busca?termo=",
    _SECOES_AURORA,
    estrito=True,
)


# --- Busca por termo, sem seção (Rede Machado / Machadão) ----------------------------------------
def _busca_simples(fornecedor: str, busca: str) -> list[dict]:
    tarefas = []
    for insumo in INSUMOS_EM_FALTA:
        pk = palavras_chave(insumo)
        for termo in dict.fromkeys(_sem_acento(t) for t in termos_busca(insumo)):
            tarefas.append(
                {
                    "fornecedor": fornecedor,
                    "categoria": insumo["categoria"],
                    "url": f"{busca}{quote(termo)}",
                    "palavras_chave": pk,
                }
            )
    return tarefas


TAREFAS_EM_FALTA_REDEMACHADO = _busca_simples(
    "redemachado", "https://www.redemachado.com.br/busca?s="
)
TAREFAS_EM_FALTA_MACHADAO = _busca_simples("machadao", "https://machadao.com.br/busca?s=")


# --- Páginas de corredor + palavras-chave --------------------------------------------------------
def _corredores(fornecedor: str, urls: dict[str, list[str]], rotulo: dict[str, str]) -> list[dict]:
    """urls: grupo -> páginas do corredor (grupo ausente = mercado não tem o corredor)."""
    tarefas = []
    for grupo, paginas in urls.items():
        pk = _uniao(grupo)
        for url in paginas:
            tarefas.append(
                {
                    "fornecedor": fornecedor,
                    "categoria": rotulo[grupo],
                    "url": url,
                    "palavras_chave": pk,
                }
            )
    return tarefas


_ROTULO = {
    "fruta": "Hortifruti - frutas",
    "hortalica": "Hortifruti - legumes e verduras",
    "bovina": "Carne bovina",
    "suina": "Carne suína",
    "peixe": "Peixes",
}

_A = "https://www.atacadao.com.br"
TAREFAS_EM_FALTA_ATACADAO = _corredores(
    "atacadao",
    {
        "fruta": [f"{_A}/frutas/fruta-fresca"],
        "hortalica": [f"{_A}/verduras-e-hortalicas", f"{_A}/hortifruti/legumes-e-vegetais"],
        "bovina": [f"{_A}/carnes-aves-e-peixes/carnes/carne-bovina"],
        "suina": [f"{_A}/carnes-aves-e-peixes/carnes/carne-suina"],
        "peixe": [f"{_A}/carnes-aves-e-peixes/peixes-e-frutos-do-mar/peixe"],
    },
    _ROTULO,
)

_SA = "https://www.atacadistasuperadega.com.br/sub"
TAREFAS_EM_FALTA_SUPERADEGA = _corredores(
    "superadega",
    {
        "fruta": [f"{_SA}/frutas-legumes-e-verduras/frutas"],
        "hortalica": [
            f"{_SA}/frutas-legumes-e-verduras/legumes",
            f"{_SA}/frutas-legumes-e-verduras/verduras",
        ],
        "bovina": [f"{_SA}/acougue-aves-e-peixaria/bovinos"],
        "suina": [f"{_SA}/acougue-aves-e-peixaria/suinos"],
        "peixe": [f"{_SA}/acougue-aves-e-peixaria/peixaria"],
    },
    _ROTULO,
)

# Supervi: só tem subcategoria de frutas, legumes e bovinos (sem verduras, suínos nem peixaria).
_SV = "https://www.compras.supervi.com.br/cat"
TAREFAS_EM_FALTA_SUPERVI = _corredores(
    "supervi",
    {
        "fruta": [f"{_SV}/frutas-legumes-e-verduras?sub=frutas"],
        "hortalica": [f"{_SV}/frutas-legumes-e-verduras?sub=legumes"],
        "bovina": [f"{_SV}/acougue-aves-peixaria?sub=bovinos-e-cortes"],
    },
    _ROTULO,
)

# Comper: sem peixaria (só tilápia, salmão etc.); charque/jerked estão em "outras-carnes".
_CP = "https://www.comper.com.br/categorias"
TAREFAS_EM_FALTA_COMPER = [
    *_corredores(
        "comper",
        {
            "fruta": [f"{_CP}/hortifruti/frutas"],
            "hortalica": [f"{_CP}/hortifruti/legumes-e-verduras"],
            "bovina": [f"{_CP}/carnes-e-aves/carnes-bovinas", f"{_CP}/carnes-e-aves/outras-carnes"],
            "suina": [f"{_CP}/carnes-e-aves/carnes-suinas"],
        },
        _ROTULO,
    )
]
