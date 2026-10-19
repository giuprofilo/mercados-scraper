"""
Tarefas de coleta do Supervi Anápolis (compras.supervi.com.br), a partir dos
insumos da planilha FNDE Centro-Oeste (mesma base do Super Adega).

A URL é `/cat/<departamento>?sub=<slug>`: o scraper usa a query para achar o
subcategory_id da API (ver SUBCATEGORIAS em scrapers/supervi.py).
Nomes no site vêm abreviados e, às vezes, sem acento (ex.: "Acem Bovino Peca").
Sem tarefa (conferido na API em 15/10/2026): ovos (sem subcategoria própria), charque/jerked
beef, lombo/copa-lombo e pescada (suínos e peixaria não têm; só costelinha/bacon e tilápia/
pintado), verduras da lista (só há repolho/jilo, que o filtro de legumes já cobre), açafrão/
cúrcuma e queijo fresco/frescal. Açúcar: não há "refinado"; o equivalente é o "cristal".
"""

_B = "https://www.compras.supervi.com.br/cat"
_HF = f"{_B}/frutas-legumes-e-verduras"
_AC = f"{_B}/acougue-aves-peixaria"
_AB = f"{_B}/alimentos-basicos"
_ME = f"{_B}/mercearia"
_CM = f"{_B}/condimentos-e-molhos"
_FL = f"{_B}/frios-e-laticinios"

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
_AVES = ["peito", "coxa", "sobrecoxa"]
_BOVINA = [
    "acém", "acem", "moído", "moido", "músculo", "musculo", "fígado",
    "figado", "peito", "carne seca", "charque", "jerked",
]


def _t(categoria: str, url: str, palavras_chave: list[str] | None = None) -> dict:
    tarefa = {"fornecedor": "supervi", "categoria": categoria, "url": url}
    if palavras_chave:
        tarefa["palavras_chave"] = palavras_chave
    return tarefa


TAREFAS_SUPERVI = [
    # --- Hortifruti ---
    _t("Hortifruti - frutas", f"{_HF}?sub=frutas", _FRUTAS),
    _t("Hortifruti - legumes", f"{_HF}?sub=legumes", _LEGUMES),
    # --- Açougue ---
    _t("Aves", f"{_AC}?sub=aves-e-frangos-cortes-resfriados-e-congelados", _AVES),
    _t("Carne bovina", f"{_AC}?sub=bovinos-e-cortes", _BOVINA),
    # --- Mercearia ---
    _t("Mercearia", f"{_AB}?sub=arroz", ["arroz"]),
    _t(
        "Mercearia",
        f"{_AB}?sub=feijao",
        ["preto", "carioca"],
    ),
    _t("Mercearia", f"{_ME}?sub=acucares-e-adocantes", ["acucar cristal", "açúcar cristal"]),
    _t("Mercearia", f"{_ME}?sub=cereais-graos-e-sementes", ["canjica", "aveia"]),
    _t(
        "Mercearia",
        f"{_AB}?sub=farinhas-e-farofas",
        ["farinha trigo", "farinha mandioca", "farinha milho", "amido milho"],
    ),
    _t(
        "Massas",
        f"{_AB}?sub=massas-instantaneas-e-tradicionais",
        ["macarrão com ovos", "macarrao com ovos", "com ovos", "c/ovos"],
    ),
    _t(
        "Óleo",
        f"{_ME}?sub=azeites-oleos-e-vinagres",
        ["óleo de soja", "oleo de soja", "extra virgem"],
    ),
    _t("Fermentos", f"{_CM}?sub=fermentos-e-essencias", ["fermento"]),
    # --- Laticínios ---
    _t(
        "Frios e laticínios",
        f"{_FL}?sub=manteigas-margarinas-e-cremes-vegetais",
        ["manteiga"],  # sem sal = "S/Sal" no nome
    ),
    _t("Leite", f"{_ME}?sub=leites", ["integral"]),
]
