"""
Tarefas de coleta da Cetap Distribuidora (cetap.lifeappsecommerce.com.br/cetap-online/), a partir
dos insumos da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste -
Insumos.csv).

A Cetap é distribuidora de industrializados (biscoito, snack, bebida, pet, limpeza): do FNDE só
existem arroz, aveia, amido de milho e macarrão (conferido na API em 21/10/2026, catálogo inteiro
de ~1.400 itens). Não há frutas, hortaliças, carnes, ovos, óleo, açúcar, feijão, fermento,
farinha de trigo/mandioca/milho, fubá nem leite em pó.

Cada insumo vira uma busca do site (`?query=<termo>`, ignora acentos) e `palavras_chave`
descarta o que só cita o termo. O filtro é por substring, então ainda entram itens
indesejados (ex.: "aveia" traz biscoito de aveia). Para "arroz" a busca traz ração
"FRANGO&ARROZ" e vinagre de arroz, então as palavras-chave são "arroz <tipo>" (só o Sakura
existe hoje; incluir novos tipos/marcas se aparecerem).
Preço e quantidade são da embalagem de venda (unidade avulsa 01X... e caixas 20X...; ver
docstring de scrapers/cetap.py).
"""

from urllib.parse import quote

_BUSCA = "https://cetap.lifeappsecommerce.com.br/cetap-online?query="


def _tarefas(categoria: str, termos: list[str], palavras_chave: list[str]) -> list[dict]:
    return [
        {
            "fornecedor": "cetap",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


TAREFAS_CETAP = [
    *_tarefas(
        "CEREAIS/FARINHAS",
        ["arroz", "aveia", "amido de milho"],
        [
            "arroz sakura", "arroz tipo", "arroz grao", "arroz integral", "arroz parboilizado",
            "arroz agulhinha", "aveia", "amido de milho",
        ],
    ),
    *_tarefas(
        "MACARRÃO",
        ["espaguete", "parafuso"],
        ["macarrão", "macarrao", "espaguete", "parafuso", "penne"],
    ),
]
