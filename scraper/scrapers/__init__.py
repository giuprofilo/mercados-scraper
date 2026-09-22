from scrapers.base import BaseScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.stock import StockScraper
from scrapers.asun import AsunScraper
from scrapers.fort import FortScraper
from scrapers.gimba import GimbaScraper
from scrapers.armazem import ArmazemScraper

SCRAPERS_DISPONIVEIS: dict[str, type[BaseScraper]] = {
    "atacadao": AtacadaoScraper,
    "stock": StockScraper,
    "asun": AsunScraper,
    "fort": FortScraper,
    "gimba": GimbaScraper,
    "armazem": ArmazemScraper,
}

__all__ = ["BaseScraper", "SCRAPERS_DISPONIVEIS"]
