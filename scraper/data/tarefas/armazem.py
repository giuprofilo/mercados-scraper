"""
Tarefas de coleta do Armazém da Maria (armazemdamaria.com.br), filtradas
pela LISTA_ALIMENTOS_PADRAO (data/alimentos.py).

A loja vem na URL: /loja-1 é Curitiba/PR (a outra é Campinas/SP; não há
loja em Porto Alegre). As subcategorias têm URL própria (/loja-1/<slug>-<id>)
e, onde não achei subcategoria, uso a busca do site (/loja-1/busca?q=...).

Sem tarefa por não existir no site: pescada e polaca (a categoria Pescados
só tem tilápia e camarão) e aveia (só aparece espalhada em vários setores).
"""

_B = "https://www.armazemdamaria.com.br/loja-1"

_FRUTAS = [
    "abacate",
    "abacaxi",
    "banana",
    "bergamota",
    "goiaba",
    "laranja",
    "limão tahiti",
    "maçã",
    "maçãs",
    "mamão",
    "manga",
    "maracujá",
    "melancia",
    "melão",
    "pêra",
    "tanjerina",
    "uva",
]
_LEGUMES = [
    "abóbora",
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
    "tomate",
    "vagem",
]
_VERDURAS = [
    "acelga",
    "agrião",
    "alface",
    "couve",
    "couve chinesa",
    "couve flor",
    "espinafre",
    "brócolis",
    "chicória",
    "salsa",
    "salsinha",
    "cheiro verde",
]
_AVES = ["peito", "coxa", "sobrecoxa", "sassami", "filézinho", "filé"]
_BOVINA = ["acém", "moído", "moída", "músculo", "fígado", "dianteiro", "paleta"]
_SUINA = ["lombo", "copa lombo"]
_FERMENTOS = [
    "químico",
    "quimico",
    "biologico",
    "biológico",
    "instantâneo",
    "instantaneo",
]

TAREFAS_ARMAZEM = [
    # --- Mercearia ---
    {
        "fornecedor": "armazem",
        "categoria": "Mercearia",
        "url": f"{_B}/arroz-e-feijao-2354",
        "palavras_chave": [
            "arroz branco",
            "feijão preto",
            "feijão carioca",
            "feijão carioquinha",
        ],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Mercearia",
        "url": f"{_B}/graos-e-cereais-2370",
        "palavras_chave": ["lentilha"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Mercearia",
        "url": f"{_B}/acucares-e-adocantes-2366",
        "palavras_chave": ["refinado"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Massas",
        "url": f"{_B}/massas-tradicionais-2302",
        "palavras_chave": ["espaguete", "parafuso", "penne"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Mercearia",
        "url": f"{_B}/farinaceos-e-amidos-2363",
        "palavras_chave": [
            "amido de milho",
            "farinha de trigo",
            "farinha de milho",
            "farinha de mandioca",
        ],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Fermentos",
        "url": f"{_B}/busca?q=fermento",
        "palavras_chave": _FERMENTOS,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Azeites",
        "url": f"{_B}/oleos-e-azeites-2371",
        "palavras_chave": ["oliva"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Óleo",
        "url": f"{_B}/oleos-e-azeites-2371",
        "palavras_chave": ["soja"],
    },
    # --- Açougue ---
    {
        "fornecedor": "armazem",
        "categoria": "Aves",
        "url": f"{_B}/frango-2058",
        "palavras_chave": _AVES,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Aves",
        "url": f"{_B}/frango-in-natura-2425",
        "palavras_chave": _AVES,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Carne bovina",
        "url": f"{_B}/carne-bovina-2060",
        "palavras_chave": _BOVINA,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Carne bovina",
        "url": f"{_B}/acougue-black-2462",
        "palavras_chave": _BOVINA,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Carne bovina - Seca",
        "url": f"{_B}/busca?q=charque",
        "palavras_chave": ["charque"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Carne suína",
        "url": f"{_B}/carnes-suinas-2383",
        "palavras_chave": _SUINA,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Carne suína",
        "url": f"{_B}/suinos-black-2472",
        "palavras_chave": _SUINA,
    },
    # --- Hortifruti ---
    {
        "fornecedor": "armazem",
        "categoria": "Hortifruti - frutas",
        "url": f"{_B}/frutas-2247",
        "palavras_chave": _FRUTAS,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Hortifruti - legumes",
        "url": f"{_B}/legumes-2255",
        "palavras_chave": _LEGUMES,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Hortifruti - verduras",
        "url": f"{_B}/verduras-2251",
        "palavras_chave": _VERDURAS,
    },
    {
        "fornecedor": "armazem",
        "categoria": "Hortifruti - ovos",
        "url": f"{_B}/ovos-2250",
        "palavras_chave": ["branco", "brancos", "ovo branco", "ovos brancos"],
    },
    # --- Frios e laticínios ---
    {
        "fornecedor": "armazem",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/menteigas-e-margarinas-2317",
        "palavras_chave": ["s sal", "sem sal"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/queijos-2457",
        "palavras_chave": ["minas", "frescal"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/queijos-pedaco-2455",
        "palavras_chave": ["minas", "frescal"],
    },
    {
        "fornecedor": "armazem",
        "categoria": "Leite",
        "url": f"{_B}/matinais-2342",
        "palavras_chave": ["leite em pó", "leite em po", "leite pó", "leite po"],
    },
]
