"""
Tarefas de coleta do Super Adega Atacadista (atacadistasuperadega.com.br),
montadas a partir dos insumos da aba "Insumos" da planilha FNDE Centro-Oeste
(csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste - Insumos.csv).
"""

_B = "https://www.atacadistasuperadega.com.br"
_HF = f"{_B}/sub/frutas-legumes-e-verduras"
_AC = f"{_B}/sub/acougue-aves-e-peixaria"
_AB = f"{_B}/sub/alimentos-basicos"
_MT = f"{_B}/sub/matinais"
_MC = f"{_B}/sub/mercearia"

_FRUTAS = [
    "abacate",
    "abacaxi",
    "banana",
    "goiaba",
    "laranja pera",
    "laranja pêra",
    "laranja lima",
    "limão",
    "limao",
    "maçã",
    "maca",
    "mamão",
    "mamao",
    "manga palmer",
    "maracujá",
    "maracuja",
    "pequi",
    "melancia",
    "melão",
    "melao",
    "pêra",
    "pera",
]
_LEGUMES = [
    "abóbora",
    "abobora",
    "abobrinha",
    "alho",
    "batata",
    "berinjela",
    "beterraba",
    "cebola",
    "cenoura",
    "chuchu",
    "inhame",
    "mandioca",
    "mandioquinha",
    "milho",
    "quiabo",
    "repolho",
    "tomate",
    "vagem",
]
_VERDURAS = [
    "acelga",
    "agrião",
    "agriao",
    "alface",
    "brócolis",
    "brocolis",
    "chicória",
    "chicoria",
    "couve",
    "salsa",
    "salsinha",
    "cheiro-verde",
    "cheiro verde",
]
_AVES = ["peito", "coxa", "sobrecoxa"]
_BOVINA = [
    "acém",
    "acem",
    "moído",
    "moido",
    "músculo",
    "musculo",
    "fígado",
    "figado",
    "peito",
    "carne seca",
    "charque",
]
_SUINA = ["lombo, copa-lombo"]
_PEIXE = ["pescada"]


def _t(categoria: str, url: str, palavras_chave: list[str] | None = None) -> dict:
    tarefa = {"fornecedor": "superadega", "categoria": categoria, "url": url}
    if palavras_chave:
        tarefa["palavras_chave"] = palavras_chave
    return tarefa


TAREFAS_SUPERADEGA = [
    # --- Hortifruti ---
    _t("Hortifruti - frutas", f"{_HF}/frutas", _FRUTAS),
    _t("Hortifruti - legumes", f"{_HF}/legumes", _LEGUMES),
    _t("Hortifruti - verduras", f"{_HF}/verduras", _VERDURAS),
    _t("Hortifruti - ovos", f"{_HF}/ovos", ["ovo", "ovos"]),
    # --- Açougue ---
    _t("Aves", f"{_AC}/aves-e-frangos", _AVES),
    _t("Carne bovina", f"{_AC}/bovinos", _BOVINA),
    _t("Carne suína", f"{_AC}/suinos", _SUINA),
    _t("Peixes", f"{_AC}/peixaria", _PEIXE),
    # --- Mercearia ---
    _t(
        "Mercearia",
        f"{_AB}/arroz",
        [
            "arroz",
        ],
    ),
    _t(
        "Mercearia",
        f"{_AB}/feijao",
        [
            "feijão preto",
            "feijao preto",
            "feijão carioca",
            "feijao carioca",
        ],
    ),
    _t(
        "Mercearia",
        f"{_AB}/acucar",
        [
            "refinado",
        ],
    ),
    _t(
        "Mercearia",
        f"{_AB}/graos",
        [
            "canjica",
        ],
    ),
    _t(
        "Mercearia",
        f"{_AB}/farinhas-e-farofas",
        [
            "farinha de trigo",
            "farinha de mandioca",
            "farinha de milho",
            "amido de milho",
        ],
    ),
    _t(
        "Mercearia",
        f"{_MT}/cereais",
        [
            "aveia",
        ],
    ),
    _t(
        "Massas",
        f"{_MC}/massas-tradicionais-e-instantaneas",
        ["macarrão com ovos", "com ovos", "c/ovos"],
    ),
    _t(
        "Óleo",
        f"{_AB}/oleo",
        ["óleo de soja", "oleo de soja"],
    ),
    _t(
        "Óleo",
        f"{_MC}/azeites",
        [
            "extra virgem",
        ],
    ),
    _t(
        "Fermentos",
        f"{_B}/sub/padaria/bolos?page=2",
        ["fermento"],
    ),
    _t("Temperos", f"{_MC}/especiarias-e-temperos", ["açafrão", "acafrao", "cúrcuma"]),
    # --- Laticínios ---
    _t(
        "Frios e laticínios",
        f"{_B}/sub/laticinios/manteigas-e-margarinas",
        ["manteiga sem sal"],
    ),
    _t(
        "Frios e laticínios",
        f"{_B}/sub/queijos/queijos-encartelados?page=3",
        ["fresco", "frescal"],
    ),
    _t("Leite", f"{_MT}/leites-em-po", ["integral"]),
]
