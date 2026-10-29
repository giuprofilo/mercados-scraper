"""
Tarefas de coleta da Rede Machado (redemachado.com.br, Machado Supermercados/MT), a partir dos
insumos da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste -
Insumos.csv).

Mesma estratégia do Abevê: cada insumo vira uma ou mais buscas do site (`/busca?s=<termo>`, sem
login) e o filtro de `palavras_chave` descarta o que não é o alimento. Termos e palavras-chave
são os de data/tarefas/abeve.py (importados de lá). A busca é por substring e não filtra por
seção, então entram também itens processados (ex.: "arroz" traz "Arrozina Maizena" e tempero
para arroz, "limao" traz esmalte). Itens por peso (hortifrúti, carnes) saem com preço por kg.
"""

from urllib.parse import quote

from data.tarefas.abeve import (
    _AVES,
    _BOVINA,
    _CEREAIS,
    _FRUTAS,
    _HORTALICAS,
    _PEIXE,
    _SUINA,
)

_BUSCA = "https://www.redemachado.com.br/busca?s="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str]
) -> list[dict]:
    return [
        {
            "fornecedor": "redemachado",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


TAREFAS_REDEMACHADO = [
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
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        [
            "arroz",
            "aveia",
            "canjica branca",
            "farinha de mandioca",
            "farinha de milho",
            "farinha de trigo",
            "amido de milho",
            "maizena",
        ],
        _CEREAIS,
    ),
    *_tarefas(
        "ÓLEOS",
        ["azeite", "oleo de soja", "oleo soja"],
        ["azeite", "óleo de soja", "oleo de soja", "óleo soja", "oleo soja"],
    ),
    *_tarefas(
        "TEMPEROS", ["acafrao", "curcuma"], ["açafrão", "acafrao", "cúrcuma", "curcuma"]
    ),
    *_tarefas("AÇÚCAR", ["acucar refinado", "acucar"], ["açúcar", "acucar"]),
    *_tarefas(
        "LEGUMINOSA", ["feijao carioca", "feijao preto", "feijao"], ["feijão", "feijao"]
    ),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"]),
    *_tarefas("CARNE AVES", ["frango", "coxa", "sobrecoxa", "peito de frango"], _AVES),
    *_tarefas(
        "CARNE BOVINA",
        [
            "carne bov",
            "carne moida",
            "carne seca",
            "acem",
            "peito",
            "musculo",
            "figado bovino",
            "charque",
        ],
        _BOVINA,
    ),
    *_tarefas("CARNE SUÍNA", ["lombo suino", "lombo", "pernil", "carne suina"], _SUINA),
    *_tarefas("CARNE PEIXE", ["pescada"], _PEIXE),
    *_tarefas("LATICÍNIOS", ["manteiga"], ["manteiga"]),
    *_tarefas("LATICÍNIOS", ["queijo minas", "queijo frescal"], ["minas", "frescal"]),
    *_tarefas(
        "LEITE",
        ["leite em po", "leite po integral"],
        ["em pó", "em po", "leite pó", "leite po "],
    ),
    *_tarefas(
        "MACARRÃO",
        ["macarrao"],
        ["macarrão"],
    ),
    *_tarefas(
        "OVO DE GALINHA",
        ["ovo branco", "ovos brancos"],
        ["ovo branco ", "ovos brancos "],
    ),
]
