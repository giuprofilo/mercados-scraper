"""
Tarefas de coleta da SE Distribuidora (sedistribuidora.com.br/se-distribuidora), a partir dos
insumos da planilha FNDE Centro-Oeste (csv/Pesquisa de Precos - Alimentos FNDE Centro-Oeste -
Insumos.csv).

A SE é distribuidora de industrializados (lácteos, congelados, biscoitos, bebidas, higiene):
do FNDE só existem azeite, manteiga e queijo (conferido na API em 21/10/2026, catálogo inteiro
de ~1.340 itens). Não há arroz, feijão, açúcar, óleo de soja, macarrão, farinhas, ovos, frutas,
hortaliças nem carnes in natura (só linguiça, empanados e pratos prontos).

Cada insumo vira uma busca do site (`?query=<termo>`, ignora acentos) e `palavras_chave`
descarta o que só cita o termo. O filtro é por substring, então ainda entram itens
indesejados (ex.: "manteiga" traz margarina sabor manteiga; "azeite" traz salada com atum).
Preço e quantidade são da embalagem de venda (ver docstring de scrapers/sedistribuidora.py).
"""

from urllib.parse import quote

_BUSCA = "https://sedistribuidora.com.br/se-distribuidora?query="


def _tarefas(categoria: str, termos: list[str], palavras_chave: list[str]) -> list[dict]:
    return [
        {
            "fornecedor": "sedistribuidora",
            "categoria": categoria,
            "url": f"{_BUSCA}{quote(termo)}",
            "palavras_chave": palavras_chave,
        }
        for termo in termos
    ]


TAREFAS_SEDISTRIBUIDORA = [
    *_tarefas("ÓLEOS", ["azeite"], ["azeite"]),
    *_tarefas("LATICÍNIOS", ["manteiga"], ["manteiga"]),
    *_tarefas(
        "LATICÍNIOS",
        ["queijo"],
        ["minas", "frescal", "mussarela"],
    ),
]
