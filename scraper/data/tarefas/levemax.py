"""
Tarefas de coleta do Leve Max SuperAtacado (levemaxsuperatacado.com.br), a partir dos insumos da
planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste - Insumos.csv).

Mesma plataforma (VIP Commerce) e mesma estratégia do Abevê: cada insumo vira uma ou mais buscas
(`/busca?termo=<termo>`) e o filtro de `palavras_chave` descarta o que não é o alimento. Termos e
palavras-chave são os mesmos de data/tarefas/abeve.py (importados de lá); o que muda são os ids
de seção (`secoes`), que seguem a árvore mercadológica do Leve Max (ver scrapers/levemax.py):
131 Fruta, 133 Legume, 135 Verdura folha, 134 Ovo, 81/82 Aves, 85 Bovina, 86 Suína, 87 Churrasco,
89 Peixe, 92 Arroz, 100 Feijão, 120 Manteiga, 127 Queijo, 118 Leite, 169 Leite em pó, 154 Açúcar,
165 Fermento, 191 Óleo, 174 Azeite, 178 Condimento, 195 Tempero e caldo, etc.

Itens por peso saem com preço por kg (ver docstring de scrapers/abeve.py). A disponibilidade de
cada insumo ainda não foi conferida por item (ver "Sem tarefa/achados" em data/tarefas/abeve.py
para o que faltou no Abevê).
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

_BUSCA = "https://www.levemaxsuperatacado.com.br/busca?termo="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str], secoes: list[int]
) -> list[dict]:
    ids = ",".join(str(i) for i in secoes)
    return [
        {
            "fornecedor": "levemax",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}&secoes={ids}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


TAREFAS_LEVEMAX = [
    *_tarefas(
        "FRUTA",
        [
            "abacate", "abacaxi", "banana", "goiaba", "laranja", "limao", "mamao", "manga",
            "maracuja", "maca", "melancia", "melao", "pequi", "pera",
        ],
        _FRUTAS,
        [131],
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
        [133, 135],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        [
            "arroz", "aveia", "canjica", "farinha de mandioca", "farinha de milho", "fuba",
            "flocao", "farinha de trigo", "amido de milho", "maizena",
        ],
        _CEREAIS,
        [92, 94, 96, 97, 101, 91, 157, 73],
    ),
    *_tarefas(
        "ÓLEOS",
        ["azeite", "oleo de soja", "oleo soja"],
        ["azeite", "óleo de soja", "oleo de soja", "óleo soja", "oleo soja"],
        [191, 174],
    ),
    *_tarefas(
        "TEMPEROS",
        ["acafrao", "curcuma"],
        ["açafrão", "acafrao", "cúrcuma", "curcuma"],
        [178, 195],
    ),
    *_tarefas("AÇÚCAR", ["acucar refinado", "acucar"], ["açúcar", "acucar"], [154]),
    *_tarefas(
        "LEGUMINOSA",
        ["feijao carioca", "feijao preto", "feijao"],
        ["feijão", "feijao"],
        [100],
    ),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"], [165]),
    *_tarefas(
        "CARNE AVES",
        ["frango", "coxa", "sobrecoxa", "peito de frango"],
        _AVES,
        [81, 82],
    ),
    *_tarefas(
        "CARNE BOVINA",
        ["carne bov", "carne moida", "carne seca", "acem", "figado bovino", "charque"],
        _BOVINA,
        [85, 87],
    ),
    *_tarefas(
        "CARNE SUÍNA", ["lombo suino", "lombo", "pernil", "carne suina"], _SUINA, [86, 87]
    ),
    *_tarefas(
        "CARNE PEIXE", ["pescada", "merluza", "tilapia", "file de peixe"], _PEIXE, [89]
    ),
    *_tarefas("LATICÍNIOS", ["manteiga"], ["manteiga"], [120]),
    *_tarefas(
        "LATICÍNIOS", ["queijo minas", "queijo frescal"], ["minas", "frescal"], [127]
    ),
    *_tarefas(
        "LEITE",
        ["leite em po", "leite po integral"],
        ["em pó", "em po", "leite pó", "leite po "],
        [169, 118],
    ),
    *_tarefas(
        "MACARRÃO",
        ["macarrao", "espaguete", "parafuso", "penne"],
        ["macarrão", "macarrao", "espaguete", "parafuso", "penne"],
        [180, 181, 182, 183, 184, 185],
    ),
    *_tarefas("OVO DE GALINHA", ["ovo", "ovos"], ["ovo ", "ovos"], [134]),
]
