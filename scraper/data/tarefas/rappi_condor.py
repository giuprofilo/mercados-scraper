"""
Tarefas de coleta do Rappi — Condor (Curitiba/PR), loja
900685906-condor-supermer-alpormayor-nc.

Os corredores do Rappi têm os mesmos nomes em todas as lojas, então as
tarefas são as do Assaí (data/tarefas/rappi.py) trocando só a loja na URL e
o fornecedor — ajustar palavras_chave lá vale para as duas. Se o Condor
precisar de uma tarefa só dele, acrescente na lista abaixo.
"""

from data.tarefas.rappi import TAREFAS_RAPPI, _B as _B_ASSAI

_B = "https://www.rappi.com.br/lojas/900685906-condor-supermer-alpormayor-nc"

TAREFAS_RAPPI_CONDOR = [
    {**tarefa, "fornecedor": "rappi_condor", "url": tarefa["url"].replace(_B_ASSAI, _B)}
    for tarefa in TAREFAS_RAPPI
]
