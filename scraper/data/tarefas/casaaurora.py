"""
Tarefas de coleta da Casa Aurora (casaaurorasupermercados.com.br, Sinop/MT), a partir dos insumos
da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste - Insumos.csv).

Mesma plataforma (VIP Commerce) do Abevê/Leve Max/Mega, mas com busca RESTRITA ao escopo: a busca
do site trata a frase como OR de palavras e varre tudo (ex.: "carne moida" traz picanha, orelha de
porco e cordeiro), então cada tarefa combina três travas:
  1. termo de busca de UMA palavra (a API ignora acentos: "brocolis" acha "Brócolis");
  2. `secoes` na URL: só itens daquele corredor (ids da árvore em scrapers/casaaurora.py);
  3. `palavras_chave`: filtro do scraper, sem acento e por palavra inteira (então não precisa
     repetir "limão"/"limao"). "a+b" exige as duas palavras; "-x" exclui (ver docstring do scraper).
O que não casar com nenhuma palavra-chave, ou casar com uma exclusão, é descartado.

Hortifrúti exclui "bandeja" (a planilha manda não coletar bandeja). Massas: qualquer produto das
seções de macarrão/massa/lasanha sai com a categoria "MACARRÃO" (o scraper força).

Achados da varredura da API (29/10/2026):
- NÃO existem no catálogo: carne moída (a busca "moida" só acha pimenta, canela e erva-mate) e pescada
  (merluza, tilápia, pangasius etc. existem, mas ficam fora do escopo da planilha). Sem tarefa de
  pescada; acém só existe cru com/sem osso e entra como o mais próximo de "acém moído".
- Peito/músculo/fígado bovino e carne seca/jerked beef existem; pequi não apareceu; frango vem
  congelado (seção 83) e resfriado (84).
- Amido de milho/Maizena está na seção 161 (Aveia e mingau); a seção 74 só tem biscoito Maizena.
- Açúcar: tarefa só "refinado" (o cristal e o demerara são outros insumos); arroz só branco/tipo 1
  (exclui integral, parboilizado, risoto, sushi...); leite em pó só integral, sem lactose excluído.
- Muitos itens de hortifrúti e alguns de outras seções estão indisponíveis (o scraper descarta).
"""

from urllib.parse import quote

_BUSCA = "https://www.casaaurorasupermercados.com.br/busca?termo="


def _tarefas(
    categoria: str, termos: list[str], palavras_chave: list[str], secoes: list[int]
) -> list[dict]:
    ids = ",".join(str(i) for i in secoes)
    return [
        {
            "fornecedor": "casaaurora",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}&secoes={ids}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


_FRUTAS = [
    "abacate", "abacaxi", "banana", "goiaba", "laranja", "limão", "mamão", "manga",
    "maracujá", "maçã", "melancia", "melão", "pequi", "pêra",
    "-kinkam", "-siciliano", "-bandeja",
]
_HORTALICAS = [
    "abóbora", "abobrinha", "acelga", "agrião", "alface", "alho", "batata", "berinjela",
    "beterraba", "brócolis", "cebola", "cenoura", "chicória", "chuchu", "couve", "inhame",
    "mandioca", "mandioquinha", "milho verde", "quiabo", "repolho", "salsa", "tomate", "vagem",
    "-conserva", "-cereja", "-grape", "-uva", "-baby", "-mini", "-bandeja",
]
_AVES = [
    "coxa", "coxas", "sobrecoxa", "sobrecoxas", "peito de frango", "filé de peito",
    "-coxão", "-coxinha", "-empanado", "-desfiado", "-defumado", "-cozido", "-chester",
]
_BOVINA = [
    "acém", "músculo bovino", "peito bovino", "fígado bovino",
    "carne seca", "jerked beef", "charque",
]

TAREFAS_CASAAURORA = [
    *_tarefas(
        "FRUTA",
        [
            "abacate", "abacaxi", "banana", "goiaba", "laranja", "limao", "mamao", "manga",
            "maracuja", "maca", "melancia", "melao", "pequi", "pera",
        ],
        _FRUTAS,
        [135],
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
        [137, 140],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["arroz"],
        [
            "arroz", "-integral", "-parboilizado", "-grãos", "-sushi", "-risoto", "-arbório",
            "-basmati", "-preto", "-caramelizado", "-flocão", "-momiji", "-farinha",
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
        ["farinha de milho", "fubá", "flocão de milho", "flocos de milho", "-pré-cozido"],
        [100, 104],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["farinha", "trigo"],
        ["farinha de trigo", "-integral", "-semolina", "-massa fresca"],
        [99],
    ),
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["amido", "maizena"],
        ["amido de milho"],
        [161],
    ),
    *_tarefas("ÓLEOS", ["azeite"], ["azeite de oliva", "azeite extra virgem", "-dendê"], [180]),
    *_tarefas("ÓLEOS", ["oleo"], ["óleo de soja"], [202]),
    *_tarefas(
        "TEMPEROS", ["acafrao", "curcuma"], ["açafrão", "cúrcuma"], [184, 200]
    ),
    *_tarefas(
        "AÇÚCAR",
        ["acucar"],
        ["açúcar refinado", "-fit", "-cubos"],
        [162],
    ),
    *_tarefas("LEGUMINOSA", ["feijao"], ["carioca", "preto", "-feijoada"], [103]),
    *_tarefas("FERMENTO", ["fermento"], ["fermento"], [170]),
    *_tarefas(
        "CARNE AVES", ["frango", "coxa", "sobrecoxa", "peito"], _AVES, [83, 84]
    ),
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
        "LATICÍNIOS", ["frescal"], ["queijo+frescal", "-creme", "-zero lactose"], [131]
    ),
    *_tarefas(
        "LEITE",
        ["leite", "integral"],
        ["leite+po+integral", "-zero lactose", "-cabra", "-infantil"],
        [174],
    ),
    *_tarefas(
        "MACARRÃO",
        [
            "macarrao", "massa", "espaguete", "lasanha", "instantaneo", "capeleti", "ravioli",
            "nhoque", "talharim", "parafuso", "penne", "fusilli", "fidelinho",
        ],
        [
            "macarrão", "massa", "espaguete", "lasanha", "capeleti", "ravioli", "nhoque",
            "talharim", "tortéi", "linguine", "tagliarini", "fidelinho", "parafuso", "penne",
            "fusilli", "-molho", "-pão de alho", "-farinha", "-mistura", "-missô", "-misso", "-folhada",
        ],
        [126, 186, 187, 188, 189, 190, 191],
    ),
    *_tarefas(
        "OVO DE GALINHA", ["ovos"], ["ovos", "ovo", "-codorna", "-páscoa", "-chocolate"], [138]
    ),
]
