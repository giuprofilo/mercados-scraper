"""
Lista de tarefas de coleta usada por main.py/scraper.py.

Cada fornecedor tem suas tarefas em data/tarefas/<fornecedor>.py; aqui só
se escolhe quais entram na coleta (comente a linha para desativar). A lista
de alimentos de referência fica em data/alimentos.py.
"""

from data.tarefas.armazem import TAREFAS_ARMAZEM
from data.tarefas.atacadao import TAREFAS_ATACADAO

# from data.tarefas.asun import TAREFAS_ASUN
# from data.tarefas.fort import TAREFAS_FORT
from data.tarefas.gimba import TAREFAS_GIMBA
from data.tarefas.rappi import TAREFAS_RAPPI
from data.tarefas.rappi_condor import TAREFAS_RAPPI_CONDOR

# from data.tarefas.stock import TAREFAS_STOCK

TAREFAS_DE_COLETA = [
    # *TAREFAS_ARMAZEM,
    # *TAREFAS_ASUN,
    # *TAREFAS_ATACADAO,
    # *TAREFAS_FORT,
    # *TAREFAS_GIMBA,
    # *TAREFAS_RAPPI,
    *TAREFAS_RAPPI_CONDOR,
    # *TAREFAS_STOCK,
]
