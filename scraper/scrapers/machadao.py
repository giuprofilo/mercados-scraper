"""
Scraper do Machadão Atacadista (machadao.com.br).

Reaproveita por completo o `RedeMachadoScraper` (mesma lógica de busca `/busca?s=<termo>`,
paginação, checkpoint e filtro), só trocando o site, por decisão do usuário. ATENÇÃO: o
docstring de `scrapers/redemachado.py` registra que o Machadão é outra plataforma (Osuper);
os seletores (`tr.cart-table__row`...) e a URL de busca NÃO foram conferidos neste site.
Validar na 1ª coleta (`python main.py --sem-sheets --filtro <termo>`) e, se vier 0 produto,
inspecionar o HTML real (`python debug_inspecionar.py "<url>"`) antes de ajustar.
"""

from scrapers.redemachado import RedeMachadoScraper


class MachadaoScraper(RedeMachadoScraper):
    nome_fornecedor = "machadao"
    BASE_URL = "https://machadao.com.br"

    # Estado em nível de classe próprio (senão divide o dedupe/checkpoint com a Rede Machado).
    _ja_coletados: set = set()
    _ultima_navegacao: float = 0.0
    _interrompida: bool = False
    _checkpoint = None
