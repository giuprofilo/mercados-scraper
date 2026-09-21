"""
Tarefas de coleta do Gimba (gimba.com.br), filtradas pela
LISTA_ALIMENTOS_PADRAO (data/alimentos.py).

O Gimba é distribuidor de não perecíveis: NÃO vende hortifruti, carnes,
aves, peixes, ovos nem queijos/frios frescos — esses itens da lista só
existem nos outros fornecedores. Também não achei no site: amido de milho,
lentilha e aveia (a busca só devolve itens sem relação, ex: luvas "sem
amido"), por isso não têm tarefa própria.
"""

TAREFAS_GIMBA = [
    # --- Mercearia ---
    {
        "fornecedor": "gimba",
        "categoria": "Mercearia",
        "url": "https://www.gimba.com.br/alimenticios/farinaceos-e-graos/graos/?DID=8781",
        "palavras_chave": [
            "arroz branco",
            "feijão preto",
            "feijão carioca",
            "feijão carioquinha",
            "lentilha",
        ],
    },
    {
        "fornecedor": "gimba",
        "categoria": "Mercearia",
        "url": "https://www.gimba.com.br/alimenticios/acucar/?DID=8530",
        "palavras_chave": ["refinado"],
    },
    {
        "fornecedor": "gimba",
        "categoria": "Massas",
        "url": "https://www.gimba.com.br/alimenticios/massas-e-molhos/macarrao/?DID=8936",
        "palavras_chave": ["espaguete", "parafuso", "penne"],
    },
    {
        "fornecedor": "gimba",
        "categoria": "Mercearia",
        "url": "https://www.gimba.com.br/alimenticios/farinaceos-e-graos/farinaceos/?DID=8771",
        "palavras_chave": ["amido", "trigo", "milho", "mandioca", "fermento"],
    },
    {
        "fornecedor": "gimba",
        "categoria": "Azeites",
        "url": "https://www.gimba.com.br/alimenticios/azeites-oleos-e-vinagres/?DID=8531",
        "palavras_chave": ["oliva"],
    },
    {
        "fornecedor": "gimba",
        "categoria": "Óleo",
        "url": "https://www.gimba.com.br/alimenticios/azeites-oleos-e-vinagres/?DID=8531",
        "palavras_chave": ["soja"],
    },
    # --- Frios e laticínios ---
    {
        "fornecedor": "gimba",
        "categoria": "Leite",
        "url": "https://www.gimba.com.br/alimenticios/leites/leite-em-po/?DID=8668",
        "palavras_chave": ["integral"],
    },
    {
        # a manteiga do Gimba (Aviação, lata) está em Enlatados e conservas
        "fornecedor": "gimba",
        "categoria": "Frios e laticínios",
        "url": "https://www.gimba.com.br/alimenticios/enlatados-e-conservas/?DID=8498",
        "palavras_chave": ["manteiga"],
    },
]


# Catálogo completo (todos os produtos de cada departamento, sem filtro de
# palavras-chave). Não é usado por padrão — para coletar tudo, troque
# TAREFAS_GIMBA por esta lista em data/produtos.py.
# TAREFAS_GIMBA_CATALOGO_COMPLETO = [
#     # --- Gimba (catálogo completo por departamento) ---
#     {
#         "fornecedor": "gimba",
#         "categoria": "Alimentícios",
#         "url": "https://www.gimba.com.br/alimenticios/?DID=1",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Bebidas",
#         "url": "https://www.gimba.com.br/bebidas/?DID=5011",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Limpeza",
#         "url": "https://www.gimba.com.br/limpeza/?DID=9",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Descartáveis e embalagens",
#         "url": "https://www.gimba.com.br/descartaveis-e-embalagens/?DID=4955",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Elétrica e manutenção",
#         "url": "https://www.gimba.com.br/eletrica-e-manutencao/?DID=1962",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Eletrodomésticos e eletroportáteis",
#         "url": "https://www.gimba.com.br/eletrodomesticos-e-eletroportateis/?DID=6079",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "EPIs e segurança",
#         "url": "https://www.gimba.com.br/epis-e-equipamentos-de-seguranca/?DID=2326",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Escolar",
#         "url": "https://www.gimba.com.br/escolar/?DID=7",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Escritório e papelaria",
#         "url": "https://www.gimba.com.br/escritorio-e-papelaria/?DID=3356",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Higiene e cuidados pessoais",
#         "url": "https://www.gimba.com.br/higiene-e-cuidados-pessoais/?DID=2606",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Informática e tecnologia",
#         "url": "https://www.gimba.com.br/informatica-e-tecnologia/?DID=3355",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Suplementos",
#         "url": "https://www.gimba.com.br/suplementos/?DID=9387",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Telefonia",
#         "url": "https://www.gimba.com.br/telefonia/?DID=16",
#     },
#     {
#         "fornecedor": "gimba",
#         "categoria": "Utilidades e cia",
#         "url": "https://www.gimba.com.br/utilidades-e-cia/?DID=2697",
#     },
# ]
