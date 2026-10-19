"""
Tarefas de coleta do Rappi — Pão de Açúcar Barateiro Asa Norte (Brasília/DF),
loja 900659399-pao-de-azucar-barateiro-nc.

Os corredores do Rappi têm os mesmos nomes em todas as lojas, então as
tarefas são as do Assaí (data/tarefas/rappi.py) trocando só a loja na URL e
o fornecedor. Só entram itens cujo store_id é o da loja da URL.
"""

from data.tarefas.rappi import TAREFAS_RAPPI, _B as _B_ASSAI

_B = "https://www.rappi.com.br/lojas/900659399-pao-de-azucar-barateiro-nc"

TAREFAS_RAPPI_BARATEIRO = [
    {**tarefa, "fornecedor": "rappi_barateiro", "url": tarefa["url"].replace(_B_ASSAI, _B)}
    for tarefa in TAREFAS_RAPPI
]
