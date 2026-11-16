"""
Tarefas de coleta do Abevê (abeve.com.br, loja Albino Torraca, Dourados/MS), a partir dos
insumos da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste
- Insumos.csv).

Busca ABRANGENTE: em vez de listar corredores, cada insumo vira uma ou mais buscas do site
(`/busca?termo=<termo>`, que ignora acentos e varre o catálogo inteiro) e o filtro de
`palavras_chave` descarta o que não é o alimento. Por isso cada grupo traz vários termos
(sinônimos, cortes e substitutos próximos) e palavras-chave com e sem acento (o filtro
não normaliza acentos e os nomes do Abevê misturam as duas grafias, ex.: "Acafrao Terra").
Cada termo gera uma tarefa; a mesma categoria repete o filtro. `secoes` (ids da árvore
mercadológica do site, ver scrapers/abeve.py) limita o resultado ao corredor certo: 131 Fruta,
133 Legume, 135 Verdura folha, 134 Ovo, 85 Carne bovina, 86 Suína, 81/82 Aves, 89 Peixe,
92 Arroz, 100 Feijão, 120 Manteiga, 127 Queijo, 118 Leite, 221 Leite em pó, 153 Açúcar,
164 Fermento, 186/226 Óleo e azeite, 174/189 Condimento e tempero, etc. Produtos repetidos entre
buscas são idênticos (mesmo produto_id) e a categoria é o grupo de insumo do CSV.

O filtro é por substring, então ainda entram itens processados do mesmo ingrediente
(ex.: "tomate" traz tomate pelado; "milho verde" traz o de lata). Itens por peso saem
com preço por kg (ver docstring de scrapers/abeve.py).
Sem tarefa/achados (conferido na API em 19/10/2026): acém só existe moído ("Carne Moida");
não há músculo nem peito bovino cru (só fígado, coração, língua, rins e cortes nobres);
pescada só em filé congelado; abobrinha, acelga, agrião e chicória aparecem quase sempre
indisponíveis; mandioquinha (= batata baroa) só em sopa/indisponível.
"""

from urllib.parse import quote

_BUSCA = "https://www.abeve.com.br/busca?termo="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str], secoes: list[int]
) -> list[dict]:
    ids = ",".join(str(i) for i in secoes)
    return [
        {
            "fornecedor": "abeve",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}&secoes={ids}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


_FRUTAS = [
    "abacate", "abacaxi", "banana", "goiaba", "laranja", "limão", "limao", "mamão",
    "mamao", "manga", "maracujá", "maracuja", "maçã", "maca ", "melancia", "melão",
    "melao", "pequi", "pêra", "pera ",
]
_HORTALICAS = [
    "abóbora", "abobora", "abobrinha", "acelga", "agrião", "agriao", "alface", "alho",
    "batata", "berinjela", "beterraba", "brócolis", "brocolis", "cebola", "cenoura",
    "chicória", "chicoria", "chuchu", "couve", "inhame", "mandioca", "mandioquinha",
    "milho verde", "quiabo", "repolho", "salsa", "tomate", "vagem",
]
_CEREAIS = [
    "arroz", "aveia", "canjica", "farinha de mandioca", "farinha mandioca", "farinha de milho",
    "farinha milho", "fubá", "fuba", "flocão", "flocao", "farinha de trigo", "farinha trigo",
    "amido de milho", "amido milho", "maizena",
]
_AVES = [
    "frango", "coxa", "sobrecoxa", "peito de frango", "peito frango", "filé de peito",
    "file de peito",
]
_BOVINA = [
    "bov", "carne moida", "carne moída", "carne seca", "charque", "jerked", "acém", "acem",
]
_SUINA = ["lombo", "suín", "suin", "porco", "pernil"]
_PEIXE = ["pescada", "merluza", "tilápia", "tilapia", "peixe"]

TAREFAS_ABEVE = [
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
        [92, 94, 96, 97, 101, 91, 156, 169, 182],
    ),
    *_tarefas(
        "ÓLEOS",
        ["azeite", "oleo de soja", "oleo soja"],
        ["azeite", "óleo de soja", "oleo de soja", "óleo soja", "oleo soja"],
        [186, 226],
    ),
    *_tarefas(
        "TEMPEROS",
        ["acafrao", "curcuma"],
        ["açafrão", "acafrao", "cúrcuma", "curcuma"],
        [174, 189],
    ),
    *_tarefas("AÇÚCAR", ["acucar refinado", "acucar"], ["açúcar", "acucar"], [153]),
    *_tarefas(
        "LEGUMINOSA",
        ["feijao carioca", "feijao preto", "feijao"],
        ["feijão", "feijao"],
        [100],
    ),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"], [164]),
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
        [221, 118],
    ),
    *_tarefas(
        "MACARRÃO",
        ["macarrao", "espaguete", "parafuso", "penne"],
        ["macarrão", "macarrao", "espaguete", "parafuso", "penne"],
        [180, 177, 179, 176, 227],
    ),
    *_tarefas("OVO DE GALINHA", ["ovo", "ovos"], ["ovo ", "ovos"], [134]),
]
