from scrapers.base import BaseScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.stock import StockScraper
from scrapers.asun import AsunScraper
from scrapers.fort import FortScraper
from scrapers.gimba import GimbaScraper
from scrapers.armazem import ArmazemScraper
from scrapers.ifood import IfoodScraper
from scrapers.superadega import SuperAdegaScraper
from scrapers.supervi import SuperviScraper
from scrapers.comper import ComperScraper
from scrapers.abeve import AbeveScraper
from scrapers.levemax import LevemaxScraper
from scrapers.mega import MegaScraper
from scrapers.machadao import MachadaoScraper
from scrapers.cetap import CetapScraper
from scrapers.rappi import RappiScraper, RappiCondorScraper, RappiBarateiroScraper

SCRAPERS_DISPONIVEIS: dict[str, type[BaseScraper]] = {
    "atacadao": AtacadaoScraper,
    "stock": StockScraper,
    "asun": AsunScraper,
    "fort": FortScraper,
    "gimba": GimbaScraper,
    "armazem": ArmazemScraper,
    "ifood": IfoodScraper,
    "rappi": RappiScraper,
    "rappi_condor": RappiCondorScraper,
    "rappi_barateiro": RappiBarateiroScraper,
    "superadega": SuperAdegaScraper,
    "supervi": SuperviScraper,
    "comper": ComperScraper,
    "abeve": AbeveScraper,
    "levemax": LevemaxScraper,
    "mega": MegaScraper,
    "machadao": MachadaoScraper,
    "cetap": CetapScraper,
}

__all__ = ["BaseScraper", "SCRAPERS_DISPONIVEIS"]
