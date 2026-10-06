"""
Tarefas de coleta do iFood Mercado — Macromix Express Canoas - Marechal
Rondon (Canoas/RS), filtradas pela LISTA_ALIMENTOS_PADRAO (data/alimentos.py).

A loja vem na URL. O menu de categorias do iFood é de botões (sem link) e o
uuid do corredor só aparece na home, então cada tarefa usa
"<loja>#corredor=<Nome do corredor>" e o scraper (scrapers/ifood.py) acha o
uuid pelo título e abre o "Ver todos". O nome precisa ser IGUAL ao do menu.

Corredores da loja (menu): Higiene e Cuidados Pessoais, Bazar e Utilidades,
Bebidas, Limpeza, Doces e Sobremesas, Leites, Alimentos Básicos, Padaria,
Frios e Laticínios, Iogurtes, Molhos/Condimentos e Conservas, Congelados e
Resfriados, Bebidas Alcoólicas, Matinais, Pet Shop, Carnes/Aves e Peixes,
Biscoitos e Salgadinhos, Étnicos, Feira, Eletro e Eletrônicos, Brinquedos,
Papelaria e Livros, Comemorativos, Suplementos e Vitaminas, Combos.

Sem tarefa por não terem item da lista de alimentos: Higiene, Bazar, Bebidas,
Limpeza, Doces, Iogurtes, Bebidas Alcoólicas, Pet Shop, Biscoitos, Étnicos,
Eletro, Brinquedos, Papelaria, Comemorativos, Suplementos, Combos, Padaria.
Congelados e Resfriados também ficou de fora (não confirmei se traz carne/
peixe que já não esteja em Carnes, Aves e Peixes).

Onde cada item da lista foi assumido (conferir no 1º teste real e mover se
estiver em outro corredor): ovos em Frios e Laticínios; azeite, óleo,
fermento e farinhas em Alimentos Básicos; milho em Molhos, Condimentos e
Conservas; aveia também em Matinais. Pescada: não confirmada no iFood.
"""

from data.tarefas.rappi import (
    _BOVINA,
    _FERMENTOS,
    _FRUTAS,
    _LEGUMES,
    _SUINA,
    _VERDURAS,
)

_B = (
    "https://www.ifood.com.br/delivery/canoas-rs/"
    "macromix--express-canoas-marechal-rondon/f711ef9e-6eef-4c32-8fdc-f368671bb6b9"
)

_FEIRA = f"{_B}#corredor=Feira"
_CARNES = f"{_B}#corredor=Carnes, Aves e Peixes"
_BASICOS = f"{_B}#corredor=Alimentos Básicos"
_FRIOS = f"{_B}#corredor=Frios e Laticínios"
_LEITES = f"{_B}#corredor=Leites"
_MATINAIS = f"{_B}#corredor=Matinais"
_CONSERVAS = f"{_B}#corredor=Molhos, Condimentos e Conservas"


def _t(categoria: str, url: str, palavras_chave: list[str]) -> dict:
    return {
        "fornecedor": "ifood",
        "categoria": categoria,
        "url": url,
        "palavras_chave": palavras_chave,
    }


TAREFAS_IFOOD = [
    # --- Feira (hortifruti) ---
    _t("Hortifruti - frutas", _FEIRA, _FRUTAS),
    _t("Hortifruti - legumes", _FEIRA, _LEGUMES),
    _t("Hortifruti - verduras", _FEIRA, _VERDURAS),
    # --- Carnes, Aves e Peixes ---
    _t("Carne bovina", _CARNES, _BOVINA),
    _t(
        "Carne bovina - Seca", _CARNES, ["charque", "carne seca", "jerked", "jerk beef"]
    ),
    _t("Carne suína", _CARNES, _SUINA),
    _t("Peixes", _CARNES, ["pescada"]),
    # --- Alimentos Básicos ---
    _t(
        "Mercearia",
        _BASICOS,
        [
            "refinado",
        ],
    ),
    _t("Fermentos", _BASICOS, _FERMENTOS),
    # --- Matinais / Conservas ---
    _t("Mercearia", _CONSERVAS, ["milho"]),
    # --- Frios e laticínios / Leites ---
    _t("Frios e laticínios", _FRIOS, ["queijo minas", "queijo frescal"]),
]
