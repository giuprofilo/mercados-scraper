"""
Tarefas de coleta do Atacadista Mega "Mega em Casa" (megaemcasa.atacadistamega.com.br), a partir
dos insumos da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste -
Insumos.csv).

Mesma plataforma (VIP Commerce) e mesma estratégia do Abevê/Leve Max: cada insumo vira uma ou
mais buscas (`/busca?termo=<termo>`) e o filtro de `palavras_chave` descarta o que não é o
alimento. Termos e palavras-chave são os de data/tarefas/abeve.py (importados de lá); o que muda
são os ids de seção (`secoes`), que seguem a árvore do Mega (ver scrapers/mega.py): 122 Fruta,
124 Legume, 126 Verdura folha, 125 Ovo, 17/18 Aves, 21 Bovina, 22 Suína, 23 Churrasco, 26 Peixe,
82 Arroz, 90 Feijão, 111 Manteiga, 118 Queijo, 109 Leite, 160 Leite em pó, 145 Açúcar,
156 Fermento, 179 Óleo, 164 Azeite, 167 Condimento, 183 Tempero e caldo, etc.

Os nomes do Mega vêm sem acento ("Banana Maca", "Cachaca"); as listas de palavras-chave já
trazem as duas grafias. Itens por peso saem com preço por kg (ver docstring de scrapers/abeve.py).
A disponibilidade de cada insumo ainda não foi conferida item a item.
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

_BUSCA = "https://www.megaemcasa.atacadistamega.com.br/busca?termo="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str], secoes: list[int]
) -> list[dict]:
    ids = ",".join(str(i) for i in secoes)
    return [
        {
            "fornecedor": "mega",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}&secoes={ids}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


TAREFAS_MEGA = [
    *_tarefas(
        "FRUTA",
        [
            "abacate", "abacaxi", "banana", "goiaba", "laranja", "limao", "mamao", "manga",
            "maracuja", "maca", "melancia", "melao", "pequi", "pera",
        ],
        _FRUTAS,
        [122],
    ),
    *_tarefas(
        "HORTALIÇAS/VEGETAIS",
        [
            "abobora", "abobrinha", "acelga", "agriao", "alface", "alho", "batata",
            "berinjela", "beterraba", "brocolis", "cebola", "cenoura", "chicoria", "chuchu",
            "couve", "inhame", "mandioca", "mandioquinha", "milho", "quiabo", "repolho",
            "salsa", "tomate", "vagem",
        ],
        _HORTALICAS,
        [124, 126],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        [
            "arroz", "aveia", "canjica", "farinha de mandioca", "farinha de milho", "fuba",
            "flocao", "farinha de trigo", "amido de milho", "maizena",
        ],
        _CEREAIS,
        [82, 84, 86, 88, 91, 81, 148],
    ),
    *_tarefas(
        "ÓLEOS",
        ["azeite", "oleo de soja", "oleo soja"],
        ["azeite", "óleo de soja", "oleo de soja", "óleo soja", "oleo soja"],
        [179, 164],
    ),
    *_tarefas(
        "TEMPEROS",
        ["acafrao", "curcuma"],
        ["açafrão", "acafrao", "cúrcuma", "curcuma"],
        [167, 183],
    ),
    *_tarefas("AÇÚCAR", ["acucar refinado", "acucar"], ["açúcar", "acucar"], [145]),
    *_tarefas(
        "LEGUMINOSA",
        ["feijao carioca", "feijao preto", "feijao"],
        ["feijão", "feijao"],
        [90],
    ),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"], [156]),
    *_tarefas(
        "CARNE AVES",
        ["frango", "coxa", "sobrecoxa", "peito de frango"],
        _AVES,
        [17, 18],
    ),
    *_tarefas(
        "CARNE BOVINA",
        ["carne bov", "carne moida", "carne seca", "acem", "figado bovino", "charque"],
        _BOVINA,
        [21, 23],
    ),
    *_tarefas(
        "CARNE SUÍNA", ["lombo suino", "lombo", "pernil", "carne suina"], _SUINA, [22, 23]
    ),
    *_tarefas(
        "CARNE PEIXE", ["pescada", "merluza", "tilapia", "file de peixe"], _PEIXE, [26]
    ),
    *_tarefas("LATICÍNIOS", ["manteiga"], ["manteiga"], [111]),
    *_tarefas(
        "LATICÍNIOS", ["queijo minas", "queijo frescal"], ["minas", "frescal"], [118]
    ),
    *_tarefas(
        "LEITE",
        ["leite em po", "leite po integral"],
        ["em pó", "em po", "leite pó", "leite po "],
        [160, 109],
    ),
    *_tarefas(
        "MACARRÃO",
        ["macarrao", "espaguete", "parafuso", "penne"],
        ["macarrão", "macarrao", "espaguete", "parafuso", "penne"],
        [169, 170, 171, 172, 174],
    ),
    *_tarefas("OVO DE GALINHA", ["ovo", "ovos"], ["ovo ", "ovos"], [125]),
]
