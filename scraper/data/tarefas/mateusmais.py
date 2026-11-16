"""
Tarefas de coleta do Mateus Mais (mateusmais.com.br), loja Mix Mateus José Walter (Fortaleza/CE),
a partir dos insumos da planilha FNDE Nordeste
(csv/Pesquisa FNDE Nordeste - Alimentos(Insumos).csv, 74 insumos).

Uma tarefa por insumo e por termo de busca. Como o bot não sabe qual insumo procurou, a
`categoria` da tarefa leva o ID FGV no formato do dropdown da planilha: "FRUTA ## 39". O
`planilha_fgv.py` usa esse ID para ligar o produto ao insumo certo (sem adivinhar pelo nome).

Cada tarefa tem a URL de busca do próprio site (`/produtos/all?query=<termo>&market_ids=<loja>`)
e `palavras_chave` no filtro estrito do scraper: sem acento, palavra inteira, "a+b" exige as
duas, "-x" exclui. A busca do site é aproximada ("banana" traz barra de cereal), então o filtro
é o que decide. Hortifrúti exclui "bandeja" (a planilha manda não coletar bandeja) e
processados (polpa, suco, doce, conserva...). Variedades ficam (manga PALMER, maçã FUJI, banana
PRATA, abóbora CABOTIAN, limão TAHITI, laranja PÊRA/LIMA...), como nas rodadas anteriores.

Sem produto no Mix José Walter em 16/11/2026 (loja só tem a versão processada ou outra variedade):
acerola, alface lisa (só hidropônica/americana/crespa/roxa), cajá-manga, caju, chicória, feijão
guandu, goiaba, laranja lima/pêra (só "Laranja" genérica), maçã fuji (só nacional/importada/verde),
manteiga sem sal (só com sal), salsa fresca, tangerina poncã (só morgote), umbu, xerém de milho e
acém moído (só "carne moída 1ª/2º"). Variedade/espécie não é relaxada (regra das rodadas anteriores).

Outra loja/região = trocar `_LOJA` (ver docstring de scrapers/mateusmais.py).
"""

from urllib.parse import quote

_LOJA = "8d5dfbd5-2150-43ee-b408-329c576550ea"  # Mix Mateus José Walter (Fortaleza/CE)
_BUSCA = "https://mateusmais.com.br/produtos/all?query="

_HORTI = [
    "@avulso",
    "-bandeja",
    "-conserva",
    "-lata",
    "-enlatado",
    "-calda",
    "-suco",
    "-polpa",
    "-geleia",
    "-doce",
    "-congelado",
    "-sorvete",
    "-iogurte",
    "-biscoito",
    "-chips",
    "-snack",
    "-aroma",
]
_CARNE = ["-empanado", "-empanada", "-hamburguer", "-linguica", "-salsicha", "-defumado"]
_MACARRAO_EXCLUI = [
    "-integral",
    "-gluten",
    "-instantaneo",
    "-fresca",
    "-resfriado",
    "-molho",
    "-farinha",
    "-mistura",
    "-legumes",
    "-chia",
]

# (id FGV, categoria da planilha, termos de busca, palavras_chave). Descrição do insumo ao lado.
_INSUMOS: list[tuple[int, str, list[str], list[str]]] = [
    (39, "FRUTA", ["abacate"], ["abacate", *_HORTI]),  # ABACATE, CRU
    (76, "FRUTA", ["abacaxi"], ["abacaxi", *_HORTI]),  # ABACAXI, CRU
    (279, "HORTALIÇAS/VEGETAIS", ["abobora"],  # ABÓBORA, CABOTIAN, CRUA
     ["abobora+cabotia", "abobora+cabotian", "abobora+japonesa", "abobora+cabocha", *_HORTI]),
    (197, "FRUTA", ["acerola"], ["acerola", *_HORTI]),  # ACEROLA, CRUA
    (198, "AÇÚCAR", ["acucar"],  # AÇÚCAR, REFINADO
     ["acucar+refinado", "-fit", "-cubo", "-cubos", "-light", "-confeiteiro", "-impalpavel"]),
    (224, "HORTALIÇAS/VEGETAIS", ["alface"], ["alface+lisa", *_HORTI]),  # ALFACE, LISA, CRUA
    (186, "HORTALIÇAS/VEGETAIS", ["alho"],  # ALHO, CRU
     ["alho", "-poro", "-frito", "-granulado", "-triturado", "-pasta", "-tempero", "-molho",
      "-po", "-negro", "-picado", "-amassado", "-pao", *_HORTI]),
    (18, "CEREAIS/FARINHAS", ["arroz"],  # ARROZ, TIPO 1, CRU
     ["arroz+tipo 1", "-integral", "-parboilizado", "-parbolizado", "-sushi", "-risoto", "-arboreo", "-basmati",
      "-preto", "-farinha", "-macarrao", "-massa", "-carreteiro", "-vermelho"]),
    (152, "CEREAIS/FARINHAS", ["aveia"],  # AVEIA, FLOCOS, CRUA
     ["aveia+flocos", "-farelo", "-farinha", "-cereal", "-mucilon", "-barra", "-biscoito",
      "-iogurte"]),
    (290, "FRUTA", ["banana"], ["banana+terra", *_HORTI]),  # BANANA, DA TERRA, CRUA
    (167, "FRUTA", ["banana"], ["banana+prata", *_HORTI]),  # BANANA, PRATA, CRUA
    (165, "HORTALIÇAS/VEGETAIS", ["batata"],  # BATATA, DOCE, CRUA (sem "-doce" da lista comum)
     ["batata+doce", *[h for h in _HORTI if h != "-doce"]]),  # BATATA, DOCE, CRUA
    (145, "HORTALIÇAS/VEGETAIS", ["batata"],  # BATATA, INGLESA, CRUA
     ["batata+inglesa", "batata+lavada", "-palha", "-frita", "-doce", "-baroa", "-salsa", *_HORTI]),
    (100, "HORTALIÇAS/VEGETAIS", ["beterraba"], ["beterraba", *_HORTI]),  # BETERRABA, CRUA
    (232, "HORTALIÇAS/VEGETAIS", ["brocolis"], ["brocolis", *_HORTI]),  # BRÓCOLIS, CRU
    (166, "FRUTA", ["caja"], ["caja+manga", "cajamanga", *_HORTI]),  # CAJÁ-MANGA, CRU
    (73, "FRUTA", ["caju"], ["caju", "-castanha", *_HORTI]),  # CAJU, CRU
    (234, "CEREAIS/FARINHAS", ["canjica"],  # CANJICA, BRANCA, CRUA
     ["canjica", "-amarela", "-doce", "-pronta", "-cremosa", "-mingau", "-biscoito"]),
    (212, "CARNE BOVINA", ["acem", "carne moida"],  # CARNE, BOVINA, ACÉM, MOÍDO, CRU
     ["@avulso", "acem+moido", "acem+moida", "carne+moida+acem", "-hamburguer", "-cozida", "-congelada pre"]),
    (117, "CARNE BOVINA", ["acem"],  # CARNE, BOVINA, ACÉM, SEM GORDURA, CRU
     ["@avulso", "acem", "-moido", "-moida", "-hamburguer", "-linguica", "-cozido", "-cozida"]),
    (269, "CARNE BOVINA", ["figado"],  # CARNE, BOVINA, FÍGADO, CRU
     ["@avulso", "figado+bovino", "figado+boi", "figado", "-frango", "-galinha", "-suino", "-bacalhau",
      "-patê", "-pate"]),
    (215, "CARNE BOVINA", ["musculo"],  # CARNE, BOVINA, MÚSCULO, SEM GORDURA, CRU
     ["@avulso", "musculo", "-frango", "-suino", "-hamburguer", "-cozido"]),
    (138, "CARNE BOVINA", ["peito"],  # CARNE, BOVINA, PEITO, SEM GORDURA, CRU
     ["peito+bovino", "peito+boi", "-frango", "-peru", "-suino", "-defumado", "-bacon"]),
    (148, "CARNE BOVINA", ["carne seca", "charque", "jerked"],  # CARNE, BOVINA, SECA, CRUA
     ["carne+seca", "charque", "jerked beef", "-dessalgada pronta", "-cozida", "-desfiada"]),
    (86, "HORTALIÇAS/VEGETAIS", ["cebola"],  # CEBOLA, CRUA
     ["cebola", "-frita", "-crocante", "-po", "-molho", "-palha", "-empanada", "-anel", *_HORTI]),
    (81, "HORTALIÇAS/VEGETAIS", ["cenoura"],  # CENOURA, CRUA
     ["cenoura", "-bolo", "-ralada", "-baby", "-mini", *_HORTI]),
    (12, "HORTALIÇAS/VEGETAIS", ["chicoria"], ["chicoria", *_HORTI]),  # CHICÓRIA, CRUA
    (263, "HORTALIÇAS/VEGETAIS", ["chuchu"], ["chuchu", *_HORTI]),  # CHUCHU, CRU
    (133, "HORTALIÇAS/VEGETAIS", ["couve"],  # COUVE, MANTEIGA, CRUA
     ["couve+folha", "couve+manteiga", "-flor", "-bruxelas", "-roxa", "-chinesa", "-semente",
      "-sementes", *[h for h in _HORTI if h != "@avulso"]]),  # folha vem embalada (com EAN)
    (305, "CEREAIS/FARINHAS", ["tapioca", "goma"],  # FARINHA DE TAPIOCA - (GOMA DE TAPIOCA)
     ["goma+tapioca", "farinha+tapioca", "tapioca+hidratada", "-biscoito", "-pronta"]),
    (113, "CEREAIS/FARINHAS", ["farinha"],  # FARINHA, DE MANDIOCA, CRUA
     ["farinha+mandioca", "-puba", "-temperada", "-farofa", "-pronta"]),
    (56, "CEREAIS/FARINHAS", ["farinha", "flocao", "fuba"],  # FARINHA, DE MILHO, AMARELA
     ["farinha+milho", "flocao", "fuba", "-pre-cozido", "-biscoito", "-bolo", "-mistura"]),
    (9, "CEREAIS/FARINHAS", ["farinha"],  # FARINHA, DE TRIGO, CRUA
     ["farinha+trigo", "-integral", "-semolina", "-massa", "-rosca", "-mistura", "-bolo"]),
    (307, "LEGUMINOSA", ["guandu", "feijao"],  # FEIJÃO GUANDU, CRU
     ["feijao+guandu", "guandu", "-pronto"]),
    (153, "LEGUMINOSA", ["feijao"],  # FEIJÃO, CARIOCA, CRU
     ["feijao+carioca", "-feijoada", "-pronto", "-tempero", "-mistura"]),
    (92, "LEGUMINOSA", ["feijao"],  # FEIJÃO, FRADINHO, CRU
     ["feijao+fradinho", "feijao+corda", "feijao+macassar", "-pronto", "-tempero", "-mistura"]),
    (26, "FERMENTO", ["fermento"],  # FERMENTO EM PÓ, QUÍMICO
     ["fermento+quimico", "fermento+em po", "-biologico"]),
    (308, "FERMENTO", ["fermento"],  # FERMENTO, BIOLÓGICO, LEVEDURA, TABLETE/PÓ
     ["fermento+biologico", "fermento+instantaneo", "fermento+seco", "fermento+fresco"]),
    (31, "CARNE AVES", ["coxa"],  # FRANGO, COXA, SEM PELE, CRUA
     ["coxa+frango", "coxa+sem pele", "-coxinha", "-cozida", "-desfiada", *_CARNE]),
    (219, "CARNE AVES", ["peito"],  # FRANGO, PEITO, SEM PELE, CRU
     ["peito+frango", "file+peito", "-peru", "-cozido", "-desfiado", *_CARNE]),
    (181, "FRUTA", ["goiaba"], ["goiaba", "-goiabada", *_HORTI]),  # GOIABA, VERMELHA, ...
    (4, "HORTALIÇAS/VEGETAIS", ["inhame"], ["inhame", *_HORTI]),  # INHAME, CRU
    (310, "LATICÍNIOS", ["iogurte"],  # IOGURTE, NATURAL
     ["iogurte+natural", "-grego", "-soja", "-vegetal", "-zero", "-polpa"]),
    (259, "FRUTA", ["laranja"], ["laranja+lima", *_HORTI]),  # LARANJA, LIMA, CRUA
    (169, "FRUTA", ["laranja"], ["laranja+pera", *_HORTI]),  # LARANJA, PÊRA, CRUA
    (183, "LEITE", ["leite"],  # LEITE, DE VACA, INTEGRAL, PÓ
     ["leite+po+integral", "-zero", "-cabra", "-infantil", "-composto", "-lacteo", "-formula",
      "-desnatado"]),
    (203, "FRUTA", ["limao"], ["limao+tahiti", "limao+taiti", *_HORTI]),  # LIMÃO, TAHITI, CRU
    (237, "FRUTA", ["maca"], ["maca+fuji", *_HORTI]),  # MAÇÃ, FUJI, COM CASCA, CRUA
    (57, "MACARRÃO", ["macarrao", "espaguete", "penne", "parafuso"],  # MACARRÃO, TRIGO, CRU
     ["macarrao+espaguete", "macarrao+penne", "macarrao+parafuso", "espaguete", "penne",
      "parafuso", *_MACARRAO_EXCLUI]),
    (211, "FRUTA", ["mamao"], ["mamao+formosa", *_HORTI]),  # MAMÃO, FORMOSA, CRU
    (74, "HORTALIÇAS/VEGETAIS", ["mandioca", "macaxeira", "aipim"],  # MANDIOCA, CRUA
     ["mandioca", "macaxeira", "aipim", "-farinha", "-polvilho", "-frita", "-massa", "-palito",
      "-bolo", "-goma", "-tapioca", "-fecula", "-farofa", *_HORTI]),
    (48, "FRUTA", ["manga"], ["manga+palmer", *_HORTI]),  # MANGA, PALMER, CRUA
    (58, "LATICÍNIOS", ["manteiga"],  # MANTEIGA, SEM SAL
     ["manteiga+sem sal", "-ghee", "-coco", "-amendoim", "-cacau", "-karite"]),
    (137, "FRUTA", ["maracuja"], ["maracuja", "-mousse", "-bombom", *_HORTI]),  # MARACUJÁ, CRU
    (230, "HORTALIÇAS/VEGETAIS", ["maxixe"], ["maxixe", *_HORTI]),  # MAXIXE, CRU
    (126, "FRUTA", ["melancia"], ["melancia", *_HORTI]),  # MELANCIA, CRUA
    (43, "FRUTA", ["melao"], ["melao", *_HORTI]),  # MELÃO, CRU
    (55, "CEREAIS/FARINHAS", ["amido"],  # MILHO, AMIDO, CRU
     ["amido+milho", "-biscoito"]),
    (235, "HORTALIÇAS/VEGETAIS", ["milho"],  # MILHO, VERDE, CRU
     ["milho+verde", "-sache", "-grao", "-graos", "-cozido", "-creme", "-pipoca", *_HORTI]),
    (44, "ÓLEOS", ["oleo"], ["oleo+soja", "-spray", "-composto", "-misto"]),  # ÓLEO, DE SOJA
    (141, "OVO DE GALINHA", ["ovos"],  # OVO, DE GALINHA, INTEIRO, CRU
     ["ovos+branco", "ovos+brancos", "ovos+vermelho", "ovos+vermelhos", "ovos+extra",
      "ovos+caipira", "ovos+grande", "ovos+grandes", "ovos+medio", "ovos+jumbo", "ovo+branco",
      "-codorna", "-pascoa", "-chocolate", "-frigideira", "-corante", "-cozido", "-pata",
      "-conserva", "-macarrao", "-massa", "-semola", "-biscoito", "-bolo", "-pao", "-molho",
      "-maionese"]),
    (36, "CARNE PEIXE", ["pescada"],  # PESCADA, BRANCA, CRUA
     ["pescada", "-empanado", "-empanada", "-hamburguer", "-pate", "-patê"]),
    (270, "HORTALIÇAS/VEGETAIS", ["pimentao"], ["pimentao+verde", *_HORTI]),  # PIMENTÃO, VERDE
    (34, "CARNE SUÍNA", ["bisteca"],  # PORCO, BISTECA, CRUA
     ["bisteca+suina", "bisteca+suino", "bisteca+porco", "-defumada", "-defumado"]),
    (192, "CARNE SUÍNA", ["lombo"],  # PORCO, LOMBO, CRU
     ["lombo+suino", "lombo+suina", "lombo+porco", "-canadense", "-defumado", "-bacalhau",
      "-fatiado"]),
    (313, "LATICÍNIOS", ["queijo"],  # QUEIJO, COALHO
     ["queijo+coalho", "-pao", "-biscoito", "-salgadinho", "-requeijao"]),
    (142, "HORTALIÇAS/VEGETAIS", ["quiabo"], ["quiabo", *_HORTI]),  # QUIABO, CRU
    (233, "HORTALIÇAS/VEGETAIS", ["repolho"], ["repolho", "-roxo", *_HORTI]),  # REPOLHO, BRANCO
    (46, "HORTALIÇAS/VEGETAIS", ["salsa"],  # SALSA, CRUA
     ["@avulso", "salsa", "-mandioquinha", "-baroa", "-batata", "-molho", "-maionese", "-queijo",
      "-bandeja"]),
    (62, "FRUTA", ["tangerina", "mexerica", "ponca"],  # TANGERINA (MEXIRICA), PONCÃ, CRUA
     ["tangerina+ponca", "mexerica+ponca", "ponca", *_HORTI]),
    (80, "HORTALIÇAS/VEGETAIS", ["tomate"],  # TOMATE, SALADA
     ["tomate", "-seco", "-cereja", "-grape", "-sweet", "-molho", "-extrato", "-pelado", "-pure",
      "-caja", "-ketchup", "-catchup", "-saladete", "-sache", "-passata", "-temperado",
      "-triturado", *_HORTI]),
    (104, "FRUTA", ["umbu"], ["umbu", *_HORTI]),  # UMBU, CRU
    (1, "HORTALIÇAS/VEGETAIS", ["vagem"], ["vagem", *_HORTI]),  # VAGEM, CRUA
    (317, "CEREAIS/FARINHAS", ["xerem", "canjiquinha"],  # XÉREM DE MILHO (TIPO CANJIQUINHA)
     ["xerem", "canjiquinha"]),
]  # fmt: skip

TAREFAS_MATEUSMAIS = [
    {
        "fornecedor": "mateusmais",
        "categoria": f"{categoria} ## {id_fgv}",
        "url": f"{_BUSCA}{quote(termo)}&market_ids={_LOJA}",
        # a planilha manda não coletar bandeja em todos os insumos, menos no óleo (id 44)
        "palavras_chave": palavras_chave
        if id_fgv == 44 or "-bandeja" in palavras_chave
        else [*palavras_chave, "-bandeja"],
    }
    for id_fgv, categoria, termos, palavras_chave in _INSUMOS
    for termo in termos
]
