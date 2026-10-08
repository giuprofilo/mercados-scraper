"""
Scraper para o Super Adega Atacadista (atacadistasuperadega.com.br).
Plataforma: Instabuy/Ibecom (Next.js app router, sem __NEXT_DATA__; dados em
api.ibecom.com.br/api_ecommerce/v5/items). Os seletores usam só `data-testid`
(estáveis); as classes Tailwind do card não são usadas, exceto o parágrafo
do nome (`p.line-clamp-2`), com fallback no `alt` da imagem.

Coleta via API: URLs listadas em SUBCATEGORIAS_API usam
GET api.ibecom.com.br/api_ecommerce/v5/items?subcategory_id=..&limit=20&page=N
(headers x-store-id, Origin e, opcional, IBSessionId vindo do .env). Resposta:
data[] (name, brand, unit_type, price_config.price / price_discount.promo_price /
promo_wholesale{price,min_qtd_to_apply}) e pagination.total_pages. As demais URLs
seguem pelo navegador. Cada caminho tem seu próprio cooldown de bloqueio.
"""

import os
import sys
import re
import json
import logging
import random
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup

if __name__ == "__main__":  # permite `python scrapers/superadega.py` (imports a partir de scraper/)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config as config
from database import Produto
from scrapers.base import BaseScraper
from setup_sessao import USER_AGENT
from utils.parsers import (
    parse_preco,
    extrair_quantidade_e_unidade,
    extrair_marca,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.atacadistasuperadega.com.br"
MAX_PAGINAS_SEGURANCA = 100
ROLAGENS_SEM_NOVOS_PARA_PARAR = 4
PAUSA_ENTRE_TAREFAS_MS = 30_000
# Após um bloqueio (403/429/503 ou desafio do Cloudflare) a coleta não tenta de
# novo antes desse prazo, nem em outra execução. Para liberar antes, apague o
# arquivo ARQUIVO_BLOQUEIO.
COOLDOWN_BLOQUEIO_H = 12
STATUS_BLOQUEIO = (403, 429, 503)
ARQUIVO_BLOQUEIO = os.path.join(
    config.BASE_DIR, "credentials", "superadega_bloqueio.json"
)
# A API tem cooldown próprio: um bloqueio do site (Cloudflare) não suspende a API
# e vice-versa.
ARQUIVO_BLOQUEIO_API = os.path.join(
    config.BASE_DIR, "credentials", "superadega_bloqueio_api.json"
)

# Coleta via API (api.ibecom.com.br), usada quando a URL da tarefa tem um
# subcategory_id conhecido (copiado do Network do site); as demais caem no fluxo
# do navegador. Chave = caminho da URL (sem domínio nem query).
API_URL = "https://api.ibecom.com.br/api_ecommerce/v5/items"
API_STORE_ID = "67e4246870f36a70e0746d56"
API_POR_PAGINA = 20
API_PAUSA_ENTRE_PAGINAS_S = (1.5, 3.0)
PAUSA_ENTRE_TAREFAS_API_MS = 5_000
SUBCATEGORIAS_API = {
    "/sub/frutas-legumes-e-verduras/frutas": "6824c4a987820670c37dc760",
    "/sub/frutas-legumes-e-verduras/legumes": "6824c4a987820670c37dc763",
    "/sub/frutas-legumes-e-verduras/verduras": "6824c4a987820670c37dc765",
    "/sub/frutas-legumes-e-verduras/ovos": "6824c4a987820670c37dc764",
    "/sub/laticinios/manteigas-e-margarinas": "6824c4ab87820670c37dc778",
    "/sub/matinais/cereais": "6824c4ab87820670c37dc789",
    "/sub/matinais/leites-em-po": "6824c4ab87820670c37dc78c",
    "/sub/alimentos-basicos/arroz": "6824c4a687820670c37dc71a",
    "/sub/alimentos-basicos/acucar": "6824c4a687820670c37dc719",
    "/sub/alimentos-basicos/farinhas-e-farofas": "6824c4a687820670c37dc71c",
    "/sub/alimentos-basicos/feijao": "6824c4a687820670c37dc71d",
    "/sub/alimentos-basicos/graos": "6824c4a687820670c37dc71e",
    "/sub/alimentos-basicos/oleo": "6824c4a687820670c37dc71f",
    "/sub/mercearia/azeites": "6824c4ac87820670c37dc790",
    "/sub/mercearia/especiarias-e-temperos": "6824c4ac87820670c37dc797",
    "/sub/mercearia/massas-tradicionais-e-instantaneas": "6824c4ac87820670c37dc79c",
    "/sub/queijos/queijos-encartelados": "6a86f19827e5f861887d1a62",
    "/sub/padaria/bolos": "6824c4ad87820670c37dc7a5",
    "massas-tradicionais-e-instantanea": "6824c4ac87820670c37dc79c",
}


class SuperAdegaScraper(BaseScraper):
    nome_fornecedor = "superadega"

    SEL_CARD_PRODUTO = '[data-testid="product-card"]'
    SEL_NOME_PRODUTO = "p.line-clamp-2"
    SEL_PRECO = '[data-testid="price-display-price"]'
    SEL_PRECO_ORIGINAL = '[data-testid="price-display-original"]'
    SEL_DESCONTO = '[data-testid="price-display-badge"]'

    _bloqueado = False  # Estado global da classe para evitar insistência após block
    _ja_coletou = False
    _api_bloqueado = False
    _api_ja_coletou = False

    _RE_DESCONTO = re.compile(r"-\s*(\d+)\s*%")
    _RE_UNIDADE_NO_NOME = re.compile(r"\b(un|unid|unidade)$", re.IGNORECASE)

    @staticmethod
    def _bloqueio_ate(api: bool = False) -> Optional[datetime]:
        """Fim do cooldown gravado por uma execução anterior (None = liberado)."""
        try:
            with open(
                ARQUIVO_BLOQUEIO_API if api else ARQUIVO_BLOQUEIO, encoding="utf-8"
            ) as f:
                ate = datetime.fromisoformat(json.load(f)["ate"])
            return ate if ate > datetime.now() else None
        except (OSError, ValueError, KeyError):
            return None

    @staticmethod
    def _registrar_bloqueio(motivo: str, espera_s: int = 0, api: bool = False) -> None:
        arquivo = ARQUIVO_BLOQUEIO_API if api else ARQUIVO_BLOQUEIO
        if api:
            SuperAdegaScraper._api_bloqueado = True
        else:
            SuperAdegaScraper._bloqueado = True
        espera = max(timedelta(hours=COOLDOWN_BLOQUEIO_H), timedelta(seconds=espera_s))
        ate = datetime.now() + espera
        try:
            os.makedirs(os.path.dirname(arquivo), exist_ok=True)
            with open(arquivo, "w", encoding="utf-8") as f:
                json.dump({"ate": ate.isoformat(), "motivo": motivo}, f)
        except OSError as e:
            logger.warning("Não foi possível gravar o bloqueio do Super Adega: %s", e)
        logger.error(
            "Super Adega: %s. Coleta suspensa até %s (apague %s para liberar antes).",
            motivo,
            ate.strftime("%d/%m %H:%M"),
            arquivo,
        )

    @staticmethod
    def _subcategoria_api(url: str) -> Optional[str]:
        caminho = urllib.parse.urlparse(url).path.rstrip("/")
        return SUBCATEGORIAS_API.get(caminho)

    @staticmethod
    def _produto_da_api(
        item: dict, categoria: str, url_fonte: Optional[str] = None
    ) -> Optional[Produto]:
        nome = (item.get("name") or "").strip()
        config_preco = item.get("price_config") or {}
        normal = config_preco.get("price")
        promo = (config_preco.get("price_discount") or {}).get("promo_price")
        preco = promo or normal
        if not nome or not preco:
            return None

        preco_original = desconto = None
        if promo and normal and normal > promo:
            preco_original = normal
            desconto = f"-{round((1 - promo / normal) * 100)}%"

        atacado = config_preco.get("promo_wholesale") or {}
        preco_atacado = atacado.get("price")
        qtd_minima = atacado.get("min_qtd_to_apply")

        quantidade, unidade = extrair_quantidade_e_unidade(nome)
        if quantidade is None and item.get("unit_type") == "KG":
            quantidade, unidade = 1.0, "kg"
        elif quantidade is None and SuperAdegaScraper._RE_UNIDADE_NO_NOME.search(nome):
            quantidade, unidade = 1.0, "un"

        return Produto(
            fornecedor=SuperAdegaScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=item.get("brand") or extrair_marca(nome),
            preco=float(preco),
            quantidade=quantidade,
            unidade=unidade,
            preco_atacado=float(preco_atacado) if preco_atacado else None,
            qtd_minima_atacado=int(qtd_minima) if qtd_minima else None,
            preco_original=preco_original,
            desconto=desconto,
            # A API não traz o link do produto: a fonte é a URL do grupo/subgrupo.
            url_produto=url_fonte,
        )

    @staticmethod
    def _buscar_pagina_api(subcategory_id: str, pagina: int) -> dict:
        query = urllib.parse.urlencode(
            {
                "subcategory_id": subcategory_id,
                "limit": API_POR_PAGINA,
                "sort": "popular",
                "page": pagina,
            }
        )
        headers = {
            "Accept": "application/json",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "User-Agent": USER_AGENT,
            "x-store-id": API_STORE_ID,
        }
        sessao = os.environ.get("SUPERADEGA_SESSION_ID")
        if sessao:
            headers["IBSessionId"] = sessao
        req = urllib.request.Request(f"{API_URL}?{query}", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)

    def _extrair_via_api(
        self,
        categoria: str,
        subcategory_id: str,
        palavras_chave: Optional[list[str]],
        url_fonte: Optional[str] = None,
    ) -> list[Produto]:
        produtos: list[Produto] = []

        if not SuperAdegaScraper._api_bloqueado:
            ate = self._bloqueio_ate(api=True)
            if ate:
                SuperAdegaScraper._api_bloqueado = True
                logger.error(
                    "API do Super Adega em cooldown até %s.",
                    ate.strftime("%d/%m %H:%M"),
                )
        if SuperAdegaScraper._api_bloqueado:
            logger.error("API do Super Adega bloqueada. Pulando '%s'.", categoria)
            return produtos

        if SuperAdegaScraper._api_ja_coletou:
            self.page.wait_for_timeout(
                PAUSA_ENTRE_TAREFAS_API_MS + random.randint(-1000, 1000)
            )
        SuperAdegaScraper._api_ja_coletou = True

        pagina, total_paginas = 1, 1
        while pagina <= min(total_paginas, MAX_PAGINAS_SEGURANCA):
            try:
                dados = self._buscar_pagina_api(subcategory_id, pagina)
            except urllib.error.HTTPError as e:
                if e.code in STATUS_BLOQUEIO:
                    retry = e.headers.get("Retry-After", "")
                    self._registrar_bloqueio(
                        f"HTTP {e.code} na API do Super Adega",
                        int(retry) if retry.isdigit() else 0,
                        api=True,
                    )
                else:
                    logger.error("API do Super Adega: HTTP %d (%s).", e.code, categoria)
                break
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                logger.error("API do Super Adega: falha em '%s': %s", categoria, e)
                break

            for item in dados.get("data", []):
                produto = self._produto_da_api(item, categoria, url_fonte)
                if produto is None:
                    continue
                if palavras_chave and not any(
                    pc.lower() in produto.nome.lower() for pc in palavras_chave
                ):
                    continue
                produtos.append(produto)

            total_paginas = (dados.get("pagination") or {}).get("total_pages", 1)
            pagina += 1
            if pagina <= total_paginas:
                self.page.wait_for_timeout(
                    int(random.uniform(*API_PAUSA_ENTRE_PAGINAS_S) * 1000)
                )

        logger.info("API: %d produtos em '%s'.", len(produtos), categoria)
        return produtos

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "Super Adega: o CEP de entrega fica no perfil persistente "
            "(setup_sessao.py) — nada a definir."
        )

    def _extrair_card(
        self, card, categoria: str, url_fonte: Optional[str] = None
    ) -> Optional[Produto]:
        nome_el = card.select_one(self.SEL_NOME_PRODUTO)
        nome = nome_el.get_text(" ", strip=True) if nome_el else ""
        if not nome:
            img = card.select_one("img[alt]")
            nome = (img.get("alt") or "").strip() if img else ""
        preco_el = card.select_one(self.SEL_PRECO)
        if not nome or preco_el is None:
            return None

        preco = parse_preco("".join(preco_el.find_all(string=True, recursive=False)))
        if not preco:
            return None
        unidade_el = preco_el.find("span")
        por_kg = bool(unidade_el and "kg" in unidade_el.get_text().lower())

        preco_original = desconto = None
        original_el = card.select_one(self.SEL_PRECO_ORIGINAL)
        original = parse_preco(original_el.get_text()) if original_el else None
        if original and original > preco:
            preco_original = original
            badge = card.select_one(self.SEL_DESCONTO)
            m = self._RE_DESCONTO.search(badge.get_text()) if badge else None
            desconto = (
                f"-{m.group(1)}%" if m else f"-{round((1 - preco / original) * 100)}%"
            )

        quantidade, unidade = extrair_quantidade_e_unidade(nome)
        if quantidade is None and por_kg:
            quantidade, unidade = 1.0, "kg"
        elif quantidade is None and self._RE_UNIDADE_NO_NOME.search(nome):
            quantidade, unidade = 1.0, "un"

        href = card.get("href", "")
        url_produto = (
            href if href.startswith("http") else f"{BASE_URL}{href}" if href else url_fonte
        )

        return Produto(
            fornecedor=self.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=preco,
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=url_produto,
        )

    def _carregar_todos_os_cards(self) -> None:
        """Rola a página de maneira suave e clica em 'ver mais' de forma humanizada."""
        anterior = -1
        sem_novos = 0

        for _ in range(MAX_PAGINAS_SEGURANCA):
            total = self.page.locator(self.SEL_CARD_PRODUTO).count()
            if total == anterior:
                sem_novos += 1
                if sem_novos >= ROLAGENS_SEM_NOVOS_PARA_PARAR:
                    break
            else:
                sem_novos = 0
            anterior = total

            botao = self.page.get_by_role(
                "button", name=re.compile(r"(ver|carregar|mostrar) mais", re.I)
            )
            if botao.count() > 0:
                try:
                    # Pequeno delay simulando reação humana antes de clicar
                    self.page.wait_for_timeout(random.randint(400, 800))
                    botao.first.click(timeout=3000)
                except Exception:
                    pass

            # Rola em pequenos passos em vez de um salto gigantesco brusco
            for _ in range(3):
                self.page.mouse.wheel(0, 800)
                self.page.wait_for_timeout(random.randint(300, 500))

            self.page.wait_for_timeout(random.randint(1000, 1500))

        logger.info("%d cards detectados na visualização.", max(anterior, 0))

    def _tirar_print(self, indice: int, nome: str) -> Optional[str]:
        try:
            os.makedirs(config.PRINTS_DIR, exist_ok=True)
            nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(" ", "_")[:60]
            caminho = os.path.join(
                config.PRINTS_DIR, f"superadega_{indice}_{nome_seguro}.png"
            )
            card = self.page.locator(self.SEL_CARD_PRODUTO).nth(indice)
            card.evaluate(
                "el => el.scrollIntoView({block: 'center', inline: 'center'})"
            )
            self.page.wait_for_timeout(200)
            card.screenshot(path=caminho)
            return caminho
        except Exception as e:
            logger.warning("Falha ao tirar print de '%s' (Super Adega): %s", nome, e)
            return None

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Super Adega)", categoria, url)
        produtos: list[Produto] = []

        subcategory_id = self._subcategoria_api(url)
        if subcategory_id:
            return self._extrair_via_api(
                categoria, subcategory_id, palavras_chave, url
            )

        if not SuperAdegaScraper._bloqueado:
            ate = self._bloqueio_ate()
            if ate:
                SuperAdegaScraper._bloqueado = True
                logger.error(
                    "Super Adega em cooldown por bloqueio anterior, até %s.",
                    ate.strftime("%d/%m %H:%M"),
                )

        if SuperAdegaScraper._bloqueado:
            logger.error(
                "Super Adega bloqueou o acesso em uma requisição anterior. Pulando '%s'.",
                categoria,
            )
            return produtos

        try:
            if SuperAdegaScraper._ja_coletou:
                # Variação no delay entre tarefas para quebrar padrões lineares
                tempo_espera = PAUSA_ENTRE_TAREFAS_MS + random.randint(-3000, 3000)
                self.page.wait_for_timeout(tempo_espera)

            SuperAdegaScraper._ja_coletou = True

            # Navega até a URL da categoria
            resposta = self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)

            # Verifica se o Cloudflare barrou a requisição logo na entrada
            if resposta and resposta.status in STATUS_BLOQUEIO:
                retry = resposta.headers.get("retry-after", "")
                self._registrar_bloqueio(
                    f"HTTP {resposta.status} no Super Adega",
                    int(retry) if retry.isdigit() else 0,
                )
                return produtos

            # Aguarda a estrutura básica de cards renderizar na árvore DOM
            self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=15000)

            # Processa a rolagem dinâmica da página
            self._carregar_todos_os_cards()

            # Captura o HTML final renderizado e faz o parse com BeautifulSoup
            html = self.page.content()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(self.SEL_CARD_PRODUTO)

            for card in cards:
                produto = self._extrair_card(card, categoria, url)
                if produto:
                    # Aplicação do filtro de palavras-chave caso exista na tarefa
                    if palavras_chave:
                        nome_minusculo = produto.nome.lower()
                        if not any(
                            pc.lower() in nome_minusculo for pc in palavras_chave
                        ):
                            continue
                    produtos.append(produto)

            logger.info(
                "Sucesso: %d produtos extraídos da categoria '%s'.",
                len(produtos),
                categoria,
            )

        except Exception as e:
            logger.error("Erro inesperado ao processar a página do Super Adega: %s", e)
            # Verifica visualmente se caiu no desafio do Cloudflare "Verify you are human"
            if (
                "cloudflare" in self.page.content().lower()
                or "challenge-running" in self.page.content().lower()
            ):
                self._registrar_bloqueio("desafio ativo do Cloudflare")

        return produtos


if __name__ == "__main__":
    # Execução direta (`python scrapers/superadega.py` ou `python -m scrapers.superadega`):
    # coleta só as tarefas do Super Adega, sem Sheets nem SQLite.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    from data.tarefas.superadega import TAREFAS_SUPERADEGA
    from scraper import executar_coletas

    resultado = executar_coletas(TAREFAS_SUPERADEGA, cep=config.CEP)
    logger.info("%d produtos coletados.", len(resultado))
