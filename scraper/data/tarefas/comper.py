"""
Tarefas de coleta do Comper (comper.com.br, loja Tamandaré - 67, Campo Grande/MS), a partir
dos insumos da planilha FNDE Centro-Oeste (mesma base do Super Adega e do Supervi).

URL = /categorias/<departamento>/<subcategoria> (listagem completa; o departamento sozinho só
traz carrosséis). Subcategorias conferidas no menu do site em 15/10/2026.
Os filtros por palavra-chave seguem a ordem/grafia dos nomes do Comper (ver conferência
em docs/05-fornecedores.md); palavras-chave com e sem acento.
Sem tarefa (conferido na API em 15/10/2026): pescada (o Comper só tem tilápia, salmão, atum,
merluza, sardinha, manjuba, bacalhau), acém/músculo/fígado (a subcategoria bovina só traz
cortes nobres e moída), canjica (verificar nos grãos), verduras fora das folhas listadas.
"""

_B = "https://www.comper.com.br/categorias"
_HF = f"{_B}/hortifruti"
_CA = f"{_B}/carnes-e-aves"
_ME = f"{_B}/mercearia"
_LF = f"{_B}/laticinios-e-frios"
_PD = f"{_B}/padaria-e-confeitaria"

_FRUTAS = [
    "abacate", "abacaxi", "banana", "goiaba", "laranja pera", "laranja pêra",
    "laranja lima", "limão", "limao", "maçã", "maca", "mamão", "mamao",
    "manga palmer", "maracujá", "maracuja", "pequi", "melancia", "melão",
    "melao", "pêra", "pera",
]
_LEGUMES = [
    "abóbora", "abobora", "abobrinha", "alho", "batata", "berinjela",
    "beterraba", "cebola", "cenoura", "chuchu", "inhame", "mandioca",
    "mandioquinha", "milho", "quiabo", "repolho", "tomate", "vagem",
]
_VERDURAS = [
    "acelga", "agrião", "agriao", "alface", "brócolis", "brocolis",
    "chicória", "chicoria", "couve", "salsa", "salsinha", "cheiro-verde",
    "cheiro verde",
]
_AVES = ["peito", "coxa", "sobrecoxa"]
_BOVINA = [
    "acém", "acem", "moído", "moido", "moída", "moida", "músculo", "musculo",
    "fígado", "figado", "peito", "carne seca", "charque", "jerked",
]
_SUINA = ["lombo", "copa-lombo", "copa lombo"]


def _t(categoria: str, url: str, palavras_chave: list[str] | None = None) -> dict:
    tarefa = {"fornecedor": "comper", "categoria": categoria, "url": url}
    if palavras_chave:
        tarefa["palavras_chave"] = palavras_chave
    return tarefa


TAREFAS_COMPER = [
    # --- Hortifruti ---
    _t("Hortifruti - frutas", f"{_HF}/frutas", _FRUTAS),
    _t("Hortifruti - legumes", f"{_HF}/legumes-e-verduras", _LEGUMES),
    _t("Hortifruti - verduras", f"{_HF}/legumes-e-verduras", _VERDURAS),
    _t("Hortifruti - ovos", f"{_HF}/ovos", ["ovos"]),
    # --- Açougue ---
    _t("Aves", f"{_CA}/aves", _AVES),
    _t("Carne bovina", f"{_CA}/carnes-bovinas", _BOVINA),
    _t("Carne bovina", f"{_CA}/outras-carnes", ["charque", "jerked"]),
    _t("Carne suína", f"{_CA}/carnes-suinas", _SUINA),
    # --- Mercearia ---
    _t("Mercearia", f"{_ME}/graos-arrozes-e-feijoes", [
        "arroz", "feijão preto", "feijao preto", "feijão carioca",
        "feijao carioca", "canjica",
    ]),
    _t("Mercearia", f"{_ME}/acucares-e-adocantes", ["refinado"]),
    _t("Mercearia", f"{_ME}/farinaceos", [
        "farinha de trigo", "farinha de mandioca", "farinha de milho",
        "amido de milho", "aveia",
    ]),
    _t("Massas", f"{_ME}/macarrao-e-sopa", ["macarrão com ovos", "macarrao com ovos", "com ovos", "c/ovos"]),
    _t("Óleo", f"{_ME}/oleos", ["óleo de soja", "oleo de soja"]),
    _t("Óleo", f"{_ME}/azeites", ["extra virgem"]),
    _t("Fermentos", f"{_PD}/fermentos", ["fermento"]),
    _t("Temperos", f"{_ME}/temperos-em-po", ["açafrão", "acafrao", "cúrcuma", "curcuma"]),
    # --- Laticínios ---
    _t("Frios e laticínios", f"{_LF}/manteigas-e-margarinas", ["manteiga"]),  # "sem sal" vem no fim do nome, depois da marca
    _t("Frios e laticínios", f"{_LF}/queijos", ["fresco", "frescal"]),
    _t("Leite", f"{_ME}/leites-em-po", ["integral"]),
]
