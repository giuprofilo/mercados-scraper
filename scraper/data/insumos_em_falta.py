"""
Insumos que ficaram EM FALTA na primeira rodada (06/11/2026) em todos os mercados.

Lista para re-coletar tudo e ver se algum voltou a aparecer. Fica separada de
`data/alimentos.py` (lista geral) e é independente de fornecedor: cada tarefa de
um mercado pode montar seus termos de busca e `palavras_chave` a partir daqui.

Cada insumo tem:
  nome        nome canônico (planilha FNDE, csv/...Insumos.csv)
  categoria   categoria da planilha (a mesma usada nas tarefas)
  busca       termos de busca de UMA palavra para o campo de busca do site
  nomes       nome + aliases que identificam o produto (com a grafia correta);
              as variantes sem acento/hífen são geradas por `_variantes`
  exigir      (opcional) palavra que TEM de aparecer no nome (variedade/espécie)
  excluir     (opcional) palavras que descartam o produto (processados, outros cortes)

Bandeja: permitida nesta lista (não é excluída).
Regra do usuário: o que tem variedade/espécie específica se mantém (manga PALMER,
pêra WILLIAMS, maçã FUJI, banana PRATA, abóbora CABOTIAN, limão TAHITI...).

Uso:
    from data.insumos_em_falta import INSUMOS_EM_FALTA, palavras_chave, termos_busca
    palavras_chave(insumo)            # substring simples (scrapers genéricos)
    palavras_chave(insumo, estrito=True)   # sintaxe "a+b"/"-x" (VIP: Abevê, Mega, Casa Aurora, DelMoro)
"""

import unicodedata

# Exclusões comuns a hortifrúti (só produto cru; bandeja PODE entrar nesta lista).
_EXCLUI_HORTIFRUTI = [
    "conserva",
    "lata",
    "enlatado",
    "calda",
    "suco",
    "polpa",
    "geleia",
    "doce",
    "congelado",
    "palmito",
]
_EXCLUI_CARNE = ["empanado", "hambúrguer", "linguiça", "salsicha", "defumado"]


def _sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in base if not unicodedata.combining(c))


def _variantes(nome: str) -> list[str]:
    """Nome com acento, sem acento e com hífen trocado por espaço (couve-flor, couve flor)."""
    saida: list[str] = []
    for v in (nome, nome.replace("-", " ")):
        for w in (v, _sem_acento(v)):
            if w not in saida:
                saida.append(w)
    return saida


INSUMOS_EM_FALTA: list[dict] = [
    {
        "nome": "pequi",
        "categoria": "FRUTA",
        "busca": ["pequi", "piqui"],
        "nomes": ["pequi", "piqui", "pequi in natura"],
        "excluir": ["conserva", "óleo", "polpa", "licor"],
    },
    {
        "nome": "batata baroa",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["baroa", "mandioquinha", "salsa"],
        "nomes": [
            "batata baroa",
            "batata-baroa",
            "baroa",
            "mandioquinha",
            "mandioquinha salsa",
            "batata salsa",
            "mandioca salsa",
        ],
        "excluir": _EXCLUI_HORTIFRUTI + ["chips", "palha"],
    },
    {
        "nome": "pescada",
        "categoria": "CARNE PEIXE",
        "busca": ["pescada"],
        "nomes": ["pescada", "pescada branca", "filé de pescada", "posta de pescada"],
        "excluir": ["empanado", "nuggets", "hambúrguer", "enlatado", "lata"],
    },
    {
        "nome": "milho verde",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["milho", "espiga"],
        "nomes": ["milho verde", "espiga de milho", "milho verde espiga", "milho in natura"],
        # cru: não vale lata/sachê/conserva/pipoca/fubá/canjica etc.
        "excluir": _EXCLUI_HORTIFRUTI
        + ["sachê", "sache", "cozido", "pipoca", "fubá", "canjica", "creme", "amido", "farinha"],
    },
    {
        "nome": "lombo de porco",
        "categoria": "CARNE SUÍNA",
        "busca": ["lombo", "lombinho", "mignon"],
        "nomes": [
            "lombo de porco",
            "lombo suíno",
            "lombo",
            "lombinho",
            "lombinho suíno",
            "copa lombo",
            "filé mignon suíno",
            "file mignon suino",
        ],
        "excluir": _EXCLUI_CARNE + ["canadense", "bacalhau", "bovino", "frango"],
    },
    {
        "nome": "pêra williams",
        "categoria": "FRUTA",
        "busca": ["pera", "williams"],
        "nomes": ["pêra williams", "pera williams", "pêra william", "pera william"],
        "exigir": "williams|william",  # só serve a williams (alternativas separadas por |)
        "excluir": _EXCLUI_HORTIFRUTI + ["seca", "desidratada"],
    },
    {
        "nome": "chicória",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["chicoria", "escarola"],
        "nomes": ["chicória", "chicória crespa", "escarola"],
        "excluir": _EXCLUI_HORTIFRUTI + ["café", "solúvel", "raiz"],
    },
    # Carnes bovinas (categoria CARNE BOVINA)
    {
        "nome": "carne bovina peito",
        "categoria": "CARNE BOVINA",
        "busca": ["peito"],
        "nomes": ["peito bovino", "carne de peito", "peito de boi", "peito de vaca"],
        "excluir": _EXCLUI_CARNE + ["frango", "peru", "chester", "suíno", "porco"],
    },
    {
        "nome": "carne bovina músculo",
        "categoria": "CARNE BOVINA",
        "busca": ["musculo"],
        "nomes": ["músculo bovino", "músculo", "carne de músculo", "músculo de boi"],
        "excluir": _EXCLUI_CARNE,
    },
    {
        "nome": "carne bovina fígado",
        "categoria": "CARNE BOVINA",
        "busca": ["figado"],
        "nomes": ["fígado bovino", "fígado", "fígado de boi"],
        "excluir": _EXCLUI_CARNE + ["frango", "galinha", "suíno", "porco", "patê"],
    },
    {
        "nome": "carne bovina acém moído",
        "categoria": "CARNE BOVINA",
        "busca": ["acem", "moida"],
        "nomes": ["acém moído", "carne moída de acém", "acém moída", "carne moída acém"],
        "excluir": _EXCLUI_CARNE + ["hambúrguer", "almôndega"],
    },
    {
        "nome": "carne bovina acém",
        "categoria": "CARNE BOVINA",
        "busca": ["acem"],
        "nomes": ["acém", "acém bovino", "acém em cubos", "acém em bifes"],
        "excluir": _EXCLUI_CARNE,
    },
    {
        "nome": "carne bovina seca",
        "categoria": "CARNE BOVINA",
        "busca": ["seca", "jerked", "charque"],
        "nomes": [
            "carne seca",
            "carne-seca",
            "jerked beef",
            "jerked",
            "charque",
            "carne seca dianteiro",
            "carne seca traseiro",
        ],
        "excluir": ["frango", "suíno", "porco", "linguiça", "farofa", "pet"],
    },
    {
        "nome": "acelga",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["acelga", "chinesa"],
        "nomes": ["acelga", "couve chinesa", "couve-chinesa", "acelga chinesa"],
        "excluir": _EXCLUI_HORTIFRUTI,
    },
    {
        "nome": "laranja lima",
        "categoria": "FRUTA",
        "busca": ["laranja", "lima"],
        "nomes": ["laranja lima", "laranja-lima", "laranja lima da pérsia"],
        "exigir": "lima",
        "excluir": _EXCLUI_HORTIFRUTI,
    },
    {
        "nome": "banana da terra",
        "categoria": "FRUTA",
        "busca": ["banana"],
        "nomes": ["banana da terra", "banana-da-terra", "banana terra", "banana comprida"],
        "excluir": _EXCLUI_HORTIFRUTI + ["chips", "passa", "frita"],
    },
    {
        "nome": "agrião",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["agriao"],
        "nomes": ["agrião", "agrião d'água", "agrião hidropônico"],
        "excluir": _EXCLUI_HORTIFRUTI,
    },
    {
        "nome": "quiabo",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["quiabo"],
        "nomes": ["quiabo", "quiabo verde"],
        "excluir": _EXCLUI_HORTIFRUTI,
    },
    {
        "nome": "abacaxi",
        "categoria": "FRUTA",
        "busca": ["abacaxi"],
        "nomes": ["abacaxi", "abacaxi pérola", "abacaxi havaí", "abacaxi havai"],
        "excluir": _EXCLUI_HORTIFRUTI + ["hortelã", "desidratado", "chips"],
    },
    {
        "nome": "abobrinha",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["abobrinha", "abobora"],
        "nomes": [
            "abobrinha",
            "abobrinha italiana",
            "abóbora italiana",
            "abobrinha verde",
            "abobrinha brasileira",
        ],
        "excluir": _EXCLUI_HORTIFRUTI + ["grelhada"],
    },
    {
        "nome": "couve-flor",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["couve", "couveflor"],
        "nomes": ["couve-flor", "couve flor", "couveflor"],
        "excluir": _EXCLUI_HORTIFRUTI + ["empanada", "gratinada"],
    },
    {
        "nome": "salsa",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["salsa", "salsinha"],
        "nomes": ["salsa", "salsinha", "salsa crespa", "salsa lisa", "maço de salsa"],
        "excluir": _EXCLUI_HORTIFRUTI + ["desidratada", "flocos", "tempero", "molho", "sachê"],
    },
    {
        "nome": "couve",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["couve"],
        "nomes": ["couve", "couve manteiga", "couve-manteiga", "couve folha"],
        # couve-flor, brócolis e couve chinesa/acelga são outros insumos
        "excluir": _EXCLUI_HORTIFRUTI + ["flor", "chinesa", "bruxelas", "roxa", "kale"],
    },
    {
        "nome": "maçã fuji",
        "categoria": "FRUTA",
        "busca": ["maca", "fuji"],
        "nomes": ["maçã fuji", "maçã-fuji", "maçãs fuji", "maca fuji"],
        "exigir": "fuji",
        "excluir": _EXCLUI_HORTIFRUTI + ["desidratada", "chips", "do amor"],
    },
    {
        "nome": "banana prata",
        "categoria": "FRUTA",
        "busca": ["banana"],
        "nomes": ["banana prata", "banana-prata", "banana prata anã", "banana prata ana"],
        "exigir": "prata",
        "excluir": _EXCLUI_HORTIFRUTI + ["chips", "passa", "frita", "desidratada"],
    },
    {
        "nome": "abacate",
        "categoria": "FRUTA",
        "busca": ["abacate"],
        "nomes": ["abacate", "abacate avocado", "abacate manteiga", "abacate breda"],
        "excluir": _EXCLUI_HORTIFRUTI + ["óleo", "guacamole"],
    },
    {
        "nome": "manga palmer",
        "categoria": "FRUTA",
        "busca": ["manga", "palmer"],
        "nomes": ["manga palmer", "manga-palmer", "mangas palmer"],
        "exigir": "palmer",
        "excluir": _EXCLUI_HORTIFRUTI + ["desidratada", "seca"],
    },
    {
        "nome": "inhame",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["inhame", "cara"],
        "nomes": ["inhame", "cará", "inhame cará"],
        "excluir": _EXCLUI_HORTIFRUTI + ["chips"],
    },
    {
        "nome": "repolho",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["repolho"],
        "nomes": ["repolho", "repolho branco", "repolho verde", "repolho liso"],
        # só branco/verde (roxo é outro produto)
        "excluir": _EXCLUI_HORTIFRUTI + ["roxo", "chinês", "chines"],
    },
    {
        "nome": "goiaba",
        "categoria": "FRUTA",
        "busca": ["goiaba"],
        "nomes": ["goiaba", "goiaba vermelha", "goiaba branca"],
        "excluir": _EXCLUI_HORTIFRUTI + ["goiabada", "romeu", "desidratada"],
    },
    {
        "nome": "abóbora cabotian",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["cabotian", "cabotia", "kabotian", "japonesa", "abobora"],
        "nomes": [
            "abóbora cabotian",
            "abóbora cabotiá",
            "abóbora kabotian",
            "abóbora kabotiá",
            "abóbora japonesa",
            "cabotian",
            "cabotiá",
            "cabotia",
            "kabotian",
            "kabotiá",
            "japonesa",
            "kabocha",
        ],
        "exigir": "cabotian|cabotia|kabotian|kabotia|japonesa|kabocha",
        "excluir": _EXCLUI_HORTIFRUTI + ["pão", "tempero"],
    },
    {
        "nome": "mamão formosa",
        "categoria": "FRUTA",
        "busca": ["mamao", "formosa"],
        "nomes": ["mamão formosa", "mamão-formosa", "mamão formosa papaya"],
        "exigir": "formosa",
        "excluir": _EXCLUI_HORTIFRUTI + ["papaia", "havaí", "havai", "desidratado"],
    },
    {
        "nome": "limão tahiti",
        "categoria": "FRUTA",
        "busca": ["limao", "tahiti", "taiti"],
        "nomes": ["limão tahiti", "limão taiti", "limão-tahiti", "limão-taiti"],
        "exigir": "tahiti|taiti",
        "excluir": _EXCLUI_HORTIFRUTI + ["siciliano", "galego", "cravo"],
    },
    {
        "nome": "mandioca",
        "categoria": "HORTALIÇAS/VEGETAIS",
        "busca": ["mandioca", "aipim", "macaxeira"],
        "nomes": ["mandioca", "aipim", "macaxeira", "mandioca descascada"],
        "excluir": _EXCLUI_HORTIFRUTI
        + ["farinha", "polvilho", "tapioca", "goma", "frita", "chips", "salsa"],
    },
]


def termos_busca(insumo: dict) -> list[str]:
    """Termos para o campo de busca do site, sem duplicar (com e sem acento)."""
    saida: list[str] = []
    for t in insumo["busca"]:
        for v in (t, _sem_acento(t)):
            if v not in saida:
                saida.append(v)
    return saida


def palavras_chave(insumo: dict, estrito: bool = False) -> list[str]:
    """
    Palavras-chave do insumo, sempre com e sem acento.

    estrito=False: só as inclusões (substring simples dos scrapers genéricos, que não
    entendem "+"/"-"); a variedade ("exigir") já está embutida nos próprios `nomes`.
    estrito=True: sintaxe dos scrapers VIP (por palavra inteira, sem acento): cada nome
    vira uma inclusão, "exigir" vira "<termo>+<variedade>" e cada exclusão vira "-x".
    """
    nomes: list[str] = []
    for n in insumo["nomes"]:
        for v in _variantes(n):
            if v not in nomes:
                nomes.append(v)
    if not estrito:
        return nomes
    exigir = insumo.get("exigir")
    if exigir:
        # produto precisa citar a variedade; o nome do insumo é a 1ª palavra (fruta/legume)
        base = insumo["nome"].split()[0]
        incl = [f"{base}+{e}" for e in exigir.split("|")]
    else:
        incl = nomes
    excl = [f"-{e}" for e in insumo.get("excluir", [])]
    return [*dict.fromkeys(incl)] + excl
