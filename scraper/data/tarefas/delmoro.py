"""
Tarefas de coleta do DelMoro Supermercados (delmorosupermercados.com.br), a partir dos insumos da
planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste - Insumos.csv).

Mesma plataforma (VIP Commerce) do Abevê/Leve Max/Mega/Casa Aurora e mesma árvore de seções da
Casa Aurora (ver scrapers/delmoro.py), mas com tarefas PRÓPRIAS (esta lista não depende da da Casa
Aurora). Cada tarefa combina três travas:
  1. termo de busca de UMA palavra (a API ignora acentos: "brocolis" acha "Brócolis");
  2. `secoes` na URL: só itens daquele corredor (ids da árvore em scrapers/delmoro.py);
  3. `palavras_chave`: filtro estrito do scraper, sem acento e por palavra inteira (não precisa
     repetir "limão"/"limao"). "a+b" exige as duas palavras; "-x" exclui.

Hortifrúti exclui "bandeja" (a planilha manda não coletar bandeja).

Macarrão: só 3 itens, o MAIS BARATO (por kg) de cada formato — espaguete, penne e parafuso. Cada
formato é uma tarefa de categoria "MACARRÃO" e o scraper (CATEGORIAS_SO_MAIS_BARATO) devolve só o
de menor preço por kg. Exclui integral, sem glúten, instantâneo, massa fresca/resfriada e as
versões com legumes/chia/multigrãos; macarrão "com ovos" entra (é o mais barato do formato).

Achados da coleta (29/10/2026):
- Sem produto disponível: açúcar refinado (só há refinado fit e em cubos, excluídos; o resto é
  cristal/demerara), carne moída e pescada (a busca não traz o corte cru), pequi e chicória.
- Acém só existe cru com/sem osso e entra como o mais próximo de "acém moído".
- Amido de milho/Maizena está na seção 161 (Aveia e mingau); a seção 74 só tem biscoito Maizena.
"""

from urllib.parse import quote

_BUSCA = "https://www.delmorosupermercados.com.br/busca?termo="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str], secoes: list[int]
) -> list[dict]:
    ids = ",".join(str(i) for i in secoes)
    return [
        {
            "fornecedor": "delmoro",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}&secoes={ids}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


_FRUTAS = [
    "abacate",
    "abacaxi",
    "banana",
    "goiaba",
    "laranja",
    "limão",
    "mamão",
    "manga",
    "maracujá",
    "maçã",
    "melancia",
    "melão",
    "pequi",
    "pêra",
    "-kinkam",
    "-siciliano",
]
_HORTALICAS = [
    "abóbora",
    "abobrinha",
    "acelga",
    "agrião",
    "alface",
    "alho",
    "batata",
    "berinjela",
    "beterraba",
    "brócolis",
    "cebola",
    "cenoura",
    "chicória",
    "chuchu",
    "couve",
    "inhame",
    "mandioca",
    "mandioquinha",
    "milho verde",
    "quiabo",
    "repolho",
    "salsa",
    "tomate",
    "vagem",
    "-conserva",
    "-cereja",
    "-grape",
    "-uva",
    "-baby",
    "-mini",
]
_AVES = [
    "coxa",
    "coxas",
    "sobrecoxa",
    "sobrecoxas",
    "peito de frango",
    "filé de peito",
    "-coxão",
    "-coxinha",
    "-empanado",
    "-desfiado",
    "-defumado",
    "-cozido",
    "-chester",
]
_BOVINA = [
    "acém",
    "músculo bovino",
    "peito bovino",
    "fígado bovino",
    "carne seca",
    "jerked beef",
    "charque",
]
_MACARRAO_SECOES = [126, 186, 187, 188, 189, 190, 191]
_MACARRAO_EXCLUI = [
    "-integral",
    "-glúten",
    "-instantâneo",
    "-resfriado",
    "-fresca",
    "-vegetais",
    "-chia",
    "-multigrãos",
    "-tricolor",
    "-tricolore",
    "-molho",
    "-farinha",
    "-mistura",
]

TAREFAS_DELMORO = [
    *_tarefas(
        "FRUTA",
        [
            "abacate",
            "abacaxi",
            "banana",
            "goiaba",
            "laranja",
            "limao",
            "mamao",
            "manga",
            "maracuja",
            "maca",
            "melancia",
            "melao",
            "pequi",
            "pera",
        ],
        _FRUTAS,
        [135],
    ),
    *_tarefas(
        "HORTALIÇAS/VEGETAIS",
        [
            "abobora",
            "abobrinha",
            "acelga",
            "agriao",
            "alface",
            "alho",
            "batata",
            "berinjela",
            "beterraba",
            "brocolis",
            "cebola",
            "cenoura",
            "chicoria",
            "chuchu",
            "couve",
            "inhame",
            "mandioca",
            "mandioquinha",
            "milho",
            "quiabo",
            "repolho",
            "salsa",
            "tomate",
            "vagem",
        ],
        _HORTALICAS,
        [137, 140],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["arroz"],
        [
            "arroz",
            "-integral",
            "-parboilizado",
            "-grãos",
            "-sushi",
            "-risoto",
            "-arbório",
            "-basmati",
            "-preto",
            "-caramelizado",
            "-flocão",
            "-momiji",
            "-farinha",
            "-carnaroli",
            "-paella",
            "-curry",
            "-carreteiro",
            "-galinha",
            "-vermelho",
            "-macarrão",
            "-massa",
        ],
        [95],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["aveia"],
        ["aveia+flocos", "-farelo", "-farinha", "-cereal", "-mucilon"],
        [161],
    ),
    *_tarefas("CEREAIS/FARINHAS", ["canjica"], ["canjica branca"], [94]),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["farinha"],
        ["farinha de mandioca", "-puba", "-temperada"],
        [97],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["farinha", "fuba", "flocao"],
        [
            "farinha de milho",
            "fubá",
            "flocão de milho",
            "flocos de milho",
            "-pré-cozido",
        ],
        [100, 104],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["farinha", "trigo"],
        ["farinha de trigo", "-integral", "-semolina", "-massa fresca"],
        [99],
    ),
    *_tarefas("CEREAIS/FARINHAS", ["amido", "maizena"], ["amido de milho"], [161]),
    *_tarefas(
        "ÓLEOS", ["azeite"], ["azeite de oliva", "azeite extra virgem", "-dendê"], [180]
    ),
    *_tarefas("ÓLEOS", ["oleo"], ["óleo de soja"], [202]),
    *_tarefas("TEMPEROS", ["acafrao", "curcuma"], ["açafrão", "cúrcuma"], [184, 200]),
    *_tarefas("AÇÚCAR", ["acucar"], ["açúcar refinado", "-fit", "-cubos"], [162]),
    *_tarefas("LEGUMINOSA", ["feijao"], ["carioca", "preto", "-feijoada"], [103]),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"], [170]),
    *_tarefas("CARNE AVES", ["frango", "coxa", "sobrecoxa", "peito"], _AVES, [83, 84]),
    *_tarefas(
        "CARNE BOVINA",
        ["acem", "musculo", "peito", "figado", "seca", "jerked", "charque"],
        _BOVINA,
        [87, 88],
    ),
    *_tarefas(
        "CARNE SUÍNA",
        ["lombo"],
        ["lombo", "-canadense", "-defumado", "-bacalhau"],
        [89],
    ),
    *_tarefas("LATICÍNIOS", ["manteiga"], ["manteiga+sem sal", "-qualicoco"], [124]),
    *_tarefas(
        "LATICÍNIOS",
        ["frescal"],
        ["queijo+frescal", "-creme", "-zero lactose", "-vegetal"],
        [131],
    ),
    *_tarefas(
        "LEITE",
        ["leite", "integral"],
        ["leite+po+integral", "-zero lactose", "-cabra", "-búfala", "-infantil"],
        [174],
    ),
    *_tarefas(
        "MACARRÃO",
        ["espaguete"],
        ["espaguete", *_MACARRAO_EXCLUI],
        _MACARRAO_SECOES,
    ),
    *_tarefas(
        "MACARRÃO",
        ["penne"],
        ["penne", *_MACARRAO_EXCLUI],
        _MACARRAO_SECOES,
    ),
    *_tarefas(
        "MACARRÃO",
        ["parafuso"],
        ["parafuso", *_MACARRAO_EXCLUI],
        _MACARRAO_SECOES,
    ),
    *_tarefas(
        "OVO DE GALINHA",
        ["ovos"],
        ["ovos", "ovo", "-codorna", "-páscoa", "-chocolate"],
        [138],
    ),
]
