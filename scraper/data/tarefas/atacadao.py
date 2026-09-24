"""
Tarefas de coleta do Atacadão (atacadao.com.br), filtradas pela
LISTA_ALIMENTOS_PADRAO (data/alimentos.py).
"""

_A = "https://www.atacadao.com.br"

_FRUTAS = [
    "abacate",
    "abacaxi",
    "banana",
    "bergamota",
    "goiaba",
    "laranja",
    "limão",
    "limao",
    "maçã",
    "maca",
    "maçãs",
    "mamão",
    "mamao",
    "manga",
    "maracujá",
    "maracuja",
    "melancia",
    "melão",
    "melao",
    "pêra",
    "tanjerina",
    "uva",
]
_LEGUMES = [
    "abóbora",
    "abobora",
    "abobrinha",
    "aipim",
    "alho",
    "batata",
    "batata doce",
    "batata inglesa",
    "batata baroa",
    "berinjela",
    "beterraba",
    "cebola",
    "cenoura",
    "chuchu",
    "inhame",
    "mandioca",
    "milho",
    "pimentão",
    "pimentao",
    "tomate",
    "vagem",
]
_VERDURAS = [
    "acelga",
    "agrião",
    "agriao",
    "alface",
    "couve",
    "couve chinesa",
    "couve flor",
    "espinafre",
    "brócolis",
    "brocolis",
    "chicória",
    "chicoria",
    "salsa",
    "salsinha",
    "cheiro verde",
]

_AVES = ["peito", "coxa", "sobrecoxa", "filé"]
_BOVINA = [
    "acém",
    "moído",
    "moída",
    "músculo",
    "acem",
    "moido",
    "moida",
    "musculo",
    "fígado",
    "figado",
    "dianteiro",
    "paleta",
]
_SUINA = (["lombo", "copa lombo"],)
_PEIXE = ["pescada"]

TAREFAS_ATACADAO = [
    # --- Mercearia ---
    {
        "fornecedor": "atacadao",
        "categoria": "Mercearia",
        "url": f"{_A}/mercearia/graos",
        "palavras_chave": ["arroz", "feijão preto", "feijão carioca", "lentilha"],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Mercearia",
        "url": f"{_A}/mercearia/acucar-e-adocantes/acucar",
        "palavras_chave": ["refinado"],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Massas",
        "url": f"{_A}/mercearia/massas-e-molhos/massa-seca",
        "palavras_chave": ["espaguete", "penne", "parafuso"],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Óleo",
        "url": f"{_A}/mercearia/azeites-oleos-e-vinagres",
        "palavras_chave": ["soja", "extra virgem", "virgem"],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Mercearia",
        "url": f"{_A}/mercearia/farinhas",
        "palavras_chave": [
            "farinha de trigo",
            "farinha de mandioca",
            "farinha de milho",
            "amido de milho",
        ],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Mercearia",
        "url": f"{_A}/padaria-e-matinais/aveias-e-cereais/aveia",
        "palavras_chave": ["flocos"],
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Fermentos",
        "url": f"{_A}/mercearia/confeitaria/fermento",
        "palavras_chave": ["fermento químico", "fermento biológico", "fermento em pó"],
    },
    # --- Açougue ---
    {
        "fornecedor": "atacadao",
        "categoria": "Aves",
        "url": f"{_A}/carnes-aves-e-peixes/aves/corte-de-frango",
        "palavras_chave": _AVES,
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Carne bovina",
        "url": f"{_A}/carnes-aves-e-peixes/carnes/carne-bovina",
        "palavras_chave": _BOVINA,
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Carne suína",
        "url": f"{_A}/carnes-aves-e-peixes/carnes/carne-suina",
        "palavras_chave": _SUINA,
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Peixes",
        "url": f"{_A}/carnes-aves-e-peixes/peixes-e-frutos-do-mar/peixe",
        "palavras_chave": _PEIXE,
    },
    # --- Hortifruti ---
    {
        "fornecedor": "atacadao",
        "categoria": "Hortifruti - ovos",
        "url": f"{_A}/hortifruti/ovos/ovo-branco",
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Hortifruti - frutas",
        "url": f"{_A}/frutas/fruta-fresca",
        "palavras_chave": _FRUTAS,
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Hortifruti - verduras",
        "url": f"{_A}/verduras-e-hortalicas",
        "palavras_chave": _VERDURAS,
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Hortifruti - legumes",
        "url": f"{_A}/hortifruti/legumes-e-vegetais",
        "palavras_chave": _LEGUMES,
    },
    # --- Frios e laticínios ---
    {
        "fornecedor": "atacadao",
        "categoria": "Frios e laticínios",
        "url": f"{_A}/frios-e-congelados/margarinas-e-manteigas/manteiga-sem-sal",
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Frios e laticínios",
        "url": f"{_A}/frios-e-congelados/queijos/queijo-minas-frescal-e-padrao",
    },
    {
        "fornecedor": "atacadao",
        "categoria": "Leite",
        "url": f"{_A}/padaria-e-matinais/leites/leite-em-po",
        "palavras_chave": ["integral"],
    },
]
