"""
Tarefas de coleta do Rappi — Assaí Atacadista Água Verde (Curitiba/PR),
filtradas pela LISTA_ALIMENTOS_PADRAO (data/alimentos.py).

A loja vem na URL (/lojas/900637167-assaiatacadista-nc). Os corredores têm
URL própria (/<departamento>/<corredor>) e, onde não há corredor, uso a
busca da loja (/s?term=...), que traz resultados aproximados — as
palavras_chave filtram.

Diferenças do Rappi em relação aos outros sites:
- Tomate, cebola, cenoura, pimentão etc. ficam em "Vegetais" junto com as
  verduras, por isso legumes e verduras são buscados nos dois corredores.
- Não existe "charque": a carne seca aparece como "jerked beef".
- Lentilha não tem corredor (só a de vapor aparece em Grãos) — vai pela busca.
- Pescada existe (Costa Sul Pescada Espalmada), mas estava esgotada no
  levantamento; a tarefa fica para quando voltar ao estoque.
"""

_B = "https://www.rappi.com.br/lojas/900637167-assaiatacadista-nc"

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
    "fígado",
    "acem",
    "moido",
    "moida",
    "musculo",
    "figado",
    "dianteiro",
    "paleta",
]
_SUINA = ["lombo", "copa lombo"]
_FERMENTOS = [
    "químico",
    "quimico",
    "biologico",
    "biológico",
    "instantâneo",
    "instantaneo",
]

TAREFAS_RAPPI = [
    # --- Mercearia ---
    {
        "fornecedor": "rappi",
        "categoria": "Mercearia",
        "url": f"{_B}/mercearia/arroz",
        "palavras_chave": ["arroz branco"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Mercearia",
        "url": f"{_B}/mercearia/graos-e-cereais",
        "palavras_chave": [
            "feijão preto",
            "feijão carioca",
            "feijão carioquinha",
            "aveia em flocos",
            "aveia flocos",
        ],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Mercearia",
        "url": f"{_B}/s?term=lentilha",
        "palavras_chave": ["lentilha"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Mercearia",
        "url": f"{_B}/mercearia/acucar-e-adocante",
        "palavras_chave": ["refinado"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Massas",
        "url": f"{_B}/mercearia/massas",
        "palavras_chave": ["espaguete", "parafuso", "penne"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Mercearia",
        "url": f"{_B}/mercearia/farinhas",
        "palavras_chave": [
            "amido de milho",
            "farinha de trigo",
            "farinha de milho",
            "farinha de mandioca",
        ],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Fermentos",
        "url": f"{_B}/mercearia/confeitaria",
        "palavras_chave": _FERMENTOS,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Azeites",
        "url": f"{_B}/mercearia/oleos-azeites-e-vinagres",
        "palavras_chave": ["oliva"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Óleo",
        "url": f"{_B}/mercearia/oleos-azeites-e-vinagres",
        "palavras_chave": ["soja"],
    },
    # --- Açougue ---
    {
        "fornecedor": "rappi",
        "categoria": "Aves",
        "url": f"{_B}/acougue-e-peixaria/aves",
        "palavras_chave": _AVES,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Carne bovina",
        "url": f"{_B}/acougue-e-peixaria/bovinos",
        "palavras_chave": _BOVINA,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Carne bovina - Seca",
        "url": f"{_B}/s?term=carne%20seca",
        "palavras_chave": ["charque", "carne seca", "jerked", "jerk beef"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Carne suína",
        "url": f"{_B}/acougue-e-peixaria/suinos",
        "palavras_chave": _SUINA,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Peixes",
        "url": f"{_B}/s?term=pescada",
        "palavras_chave": ["pescada", "polaca"],
    },
    # --- Hortifruti ---
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - frutas",
        "url": f"{_B}/hortifruti/frutas",
        "palavras_chave": _FRUTAS,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - legumes",
        "url": f"{_B}/hortifruti/legumes",
        "palavras_chave": _LEGUMES,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - legumes",
        "url": f"{_B}/hortifruti/vegetais",
        "palavras_chave": _LEGUMES,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - verduras",
        "url": f"{_B}/hortifruti/vegetais",
        "palavras_chave": _VERDURAS,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - verduras",
        "url": f"{_B}/hortifruti/ervas-e-aromaticos",
        "palavras_chave": _VERDURAS,
    },
    {
        "fornecedor": "rappi",
        "categoria": "Hortifruti - ovos",
        "url": f"{_B}/laticinios-e-ovos/ovos",
        "palavras_chave": ["branco", "brancos", "ovo branco", "ovos brancos"],
    },
    # --- Frios e laticínios ---
    {
        "fornecedor": "rappi",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/laticinios-e-ovos/manteiga-e-margarina",
        "palavras_chave": ["s sal", "sem sal"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/queijos-e-frios/queijos",
        "palavras_chave": ["minas", "frescal"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Frios e laticínios",
        "url": f"{_B}/queijos-e-frios/queijos-frescos",
        "palavras_chave": ["minas", "frescal"],
    },
    {
        "fornecedor": "rappi",
        "categoria": "Leite",
        "url": f"{_B}/laticinios-e-ovos/leite-em-po",
        "palavras_chave": ["leite em pó", "leite em po", "leite pó", "leite po"],
    },
]
