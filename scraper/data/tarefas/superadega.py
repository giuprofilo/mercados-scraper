"""
Tarefas de coleta do Super Adega Atacadista (atacadistasuperadega.com.br),
montadas a partir dos insumos da aba "Insumos" da planilha FNDE Centro-Oeste
(csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste - Insumos.csv).

Hortifruti usa as subcategorias confirmadas no site (/sub/<cat>/<slug>:
frutas, legumes, verduras, ovos). As demais categorias (açougue, básicos,
laticínios, mercearia) usam /cat/<slug>, que só mostra carrosséis com poucos
itens por subcategoria: NÃO confirmado — trocar por /sub/<cat>/<slug> assim
que o slug da subcategoria for visto no site, e conferir quais itens existem.

Observação do CSV: "não coletar bandeja" (itens em bandeja/embalados não valem;
o filtro por nome não separa isso, conferir na planilha). Sem tarefa dedicada:
pequi e açafrão só entram se o site tiver (busca por palavra-chave nas
categorias abaixo; se não aparecer, o item não existe na loja).
"""

_B = "https://www.atacadistasuperadega.com.br"
_HF = f"{_B}/sub/frutas-legumes-e-verduras"

_FRUTAS = [
    "abacate",
    "abacaxi",
    "banana",
    "goiaba",
    "laranja",
    "limão",
    "limao",
    "maçã",
    "maca",
    "mamão",
    "mamao",
    "manga",
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
_SUINA = ["lombo"]
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
    _t("Aves", f"{_B}/cat/acougue-aves-e-peixaria", _AVES),
    _t("Carne bovina", f"{_B}/cat/acougue-aves-e-peixaria", _BOVINA),
    _t("Carne suína", f"{_B}/cat/acougue-aves-e-peixaria", _SUINA),
    _t("Peixes", f"{_B}/cat/acougue-aves-e-peixaria", _PEIXE),
    # --- Mercearia ---
    _t(
        "Mercearia",
        f"{_B}/cat/alimentos-basicos",
        [
            "arroz",
            "feijão preto",
            "feijao preto",
            "feijão carioca",
            "feijao carioca",
            "canjica",
            "açúcar refinado",
            "acucar refinado",
            "farinha de trigo",
            "farinha de mandioca",
            "farinha de milho",
            "amido de milho",
            "aveia",
        ],
    ),
    _t("Massas", f"{_B}/cat/mercearia", ["macarrão", "macarrao", "espaguete"]),
    _t(
        "Óleo",
        f"{_B}/cat/mercearia",
        ["óleo de soja", "oleo de soja", "azeite"],
    ),
    _t(
        "Fermentos",
        f"{_B}/cat/mercearia",
        ["fermento"],
    ),
    _t("Temperos", f"{_B}/cat/mercearia", ["açafrão", "acafrao", "cúrcuma"]),
    # --- Laticínios ---
    _t("Frios e laticínios", f"{_B}/cat/laticinios", ["manteiga sem sal"]),
    _t("Frios e laticínios", f"{_B}/cat/queijos", ["minas", "frescal"]),
    _t("Leite", f"{_B}/cat/matinais", ["leite em pó", "leite em po"]),
]
