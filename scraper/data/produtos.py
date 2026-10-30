"""
Lista de tarefas de coleta usada por main.py/scraper.py.

Cada fornecedor tem suas tarefas em data/tarefas/<fornecedor>.py; aqui só
se escolhe quais entram na coleta (comente a linha para desativar). A lista
de alimentos de referência fica em data/alimentos.py.
"""

from data.tarefas.abeve import TAREFAS_ABEVE
from data.tarefas.armazem import TAREFAS_ARMAZEM
from data.tarefas.atacadao import TAREFAS_ATACADAO
from data.tarefas.casaaurora import TAREFAS_CASAAURORA
from data.tarefas.cetap import TAREFAS_CETAP
from data.tarefas.comper import TAREFAS_COMPER
from data.tarefas.delmoro import TAREFAS_DELMORO

# from data.tarefas.asun import TAREFAS_ASUN
# from data.tarefas.fort import TAREFAS_FORT
from data.tarefas.gimba import TAREFAS_GIMBA
from data.tarefas.ifood import TAREFAS_IFOOD
from data.tarefas.levemax import TAREFAS_LEVEMAX
from data.tarefas.mega import TAREFAS_MEGA
from data.tarefas.rappi import TAREFAS_RAPPI
from data.tarefas.rappi_barateiro import TAREFAS_RAPPI_BARATEIRO
from data.tarefas.rappi_condor import TAREFAS_RAPPI_CONDOR
from data.tarefas.redemachado import TAREFAS_REDEMACHADO
from data.tarefas.superadega import TAREFAS_SUPERADEGA
from data.tarefas.supervi import TAREFAS_SUPERVI

# from data.tarefas.stock import TAREFAS_STOCK

TAREFAS_DE_COLETA = [
    # *TAREFAS_ABEVE,
    # *TAREFAS_ARMAZEM,
    # *TAREFAS_ASUN,
    # *TAREFAS_ATACADAO,
    # *TAREFAS_CASAAURORA,
    # *TAREFAS_CETAP,
    # *TAREFAS_COMPER,
    *TAREFAS_DELMORO,
    # *TAREFAS_FORT,
    # *TAREFAS_GIMBA,
    # *TAREFAS_IFOOD,
    # *TAREFAS_LEVEMAX,
    # *TAREFAS_MEGA,
    # *TAREFAS_RAPPI,
    # *TAREFAS_RAPPI_CONDOR,
    # *TAREFAS_REDEMACHADO,
    # *TAREFAS_STOCK,
    # *TAREFAS_SUPERADEGA,
    # *TAREFAS_SUPERVI,
    # *TAREFAS_RAPPI_BARATEIRO,
]
