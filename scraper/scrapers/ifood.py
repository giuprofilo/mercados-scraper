"""
Scraper para o iFood Mercado (ifood.com.br/delivery/...). Uma loja por
tarefa: hoje o Macromix Express Canoas - Marechal Rondon (Canoas/RS).

Como o site funciona (confirmado contra o HTML real da loja; o que NÃO foi
visto está marcado "não confirmado"):
- Plataforma: Next.js atrás de Cloudflare + PerimeterX. O Playwright
  automatizado cai no desafio "Um momento…" e não passa — por isso a sessão
  é feita à mão: `python setup_sessao.py` (site "ifood"), que salva o
  desafio resolvido e o endereço de entrega no perfil persistente.
- Loja/região: a loja vai na URL (/delivery/<cidade>/<slug>/<uuid>); o
  preço é o da loja. O endereço de entrega do perfil só afeta frete/
  disponibilidade (não confirmado); o CEP de config.py é ignorado.
- Os produtos vêm no HTML renderizado, sem href nos cards (a URL do produto
  gravada é a da página da tarefa). Seletores semânticos (BEM), não hash:
  card `.product-card-wrapper`, nome `.product-card__description`
  (atributo title), detalhe `.product-card__details` (ex: "Embalagem
  325ml"), preço `.product-card__price`.
- Preço por quantidade (atacado): `.product-card-scale-price` traz
  "R$ 13,15 cada" (preço unitário), `...__scale-price` o preço da
  quantidade mínima ("R$ 12,37") e `...-tag` o texto "A PARTIR 3 UN.".
  Vira preco / preco_atacado / qtd_minima_atacado.
- Card sem esse bloco (preço simples, promoção "de/por", item por peso):
  HTML não confirmado — usa o 1º "R$ x,xx" do bloco de preço e loga aviso
  quando houver mais de um valor.
- Categorias: a home da loja lista corredores `.market-catalog-aisle`
  (título `.market-catalog-aisle__title`) com ~10 itens cada e um link
  "Ver todos" para `?corredor=<uuid>` (outro layout: `h2.catalog-group__title`
  com o uuid no id). O menu rápido de categorias é de botões, sem link, por
  isso as tarefas usam "<loja>#corredor=<Nome>" e o scraper acha o uuid na
  home pelo título. Lista de corredores: Higiene, Bazar, Bebidas, Limpeza,
  Doces, Leites, Alimentos Básicos, Padaria, Frios e Laticínios, Iogurtes,
  Molhos/Condimentos/Conservas, Congelados e Resfriados, Bebidas Alcoólicas,
  Matinais, Pet Shop, Carnes/Aves/Peixes, Biscoitos, Étnicos, Feira, Eletro,
  Brinquedos, Papelaria, Comemorativos, Suplementos, Combos. A página "Ver todos" não foi
  inspecionada: assume os mesmos cards e rola a página até parar de crescer
  (não confirmado — validar com `main.py --sem-sheets`).
"""

import logging
import os
import re
from typing import Optional
from urllib.parse import parse_qs

from bs4 import BeautifulSoup

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import extrair_marca, extrair_quantidade_e_unidade, parse_preco

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ifood.com.br"
MAX_PAGINAS_SEGURANCA = 30  # rolagens da página, no máximo
_REGEX_PRECO = re.compile(r"R\$\s*\d[\d.]*,\d{2}")
_REGEX_QTD_MIN = re.compile(r"(\d+)\s*UN", re.IGNORECASE)


class IfoodScraper(BaseScraper):
    nome_fornecedor = "ifood"
    nome_loja = "Macromix Express Canoas - Marechal Rondon, Canoas/RS"

    SEL_CARD_PRODUTO = ".product-card-wrapper"
    SEL_NOME = ".product-card__description"
    SEL_DETALHE = ".product-card__details"
    SEL_PRECO = ".product-card__price"
    SEL_ESCALA = ".product-card-scale-price"
    SEL_ESCALA_PRECO = ".product-card-scale-price__scale-price"
    SEL_ESCALA_TAG = ".product-card-scale-price-tag"
    SEL_ESCALA_UNIDADE = ".product-card-scale-price__price-unit"
    SEL_CORREDOR = ".market-catalog-aisle"
    SEL_CORREDOR_TITULO = ".market-catalog-aisle__title"

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "iFood: a loja vem na URL (%s); endereço vem da sessão salva "
            "(setup_sessao.py) — nada a definir.",
            self.nome_loja,
        )

    # ------------------------------------------------------------------
    def _extrair_precos(self, card) -> tuple[Optional[float], Optional[float], Optional[int], Optional[str]]:
        """-> (preco, preco_atacado, qtd_minima_atacado, aviso)"""
        escala = card.select_one(self.SEL_ESCALA)
        if escala:
            principal = escala.find("span", recursive=False)
            if principal:
                for un in principal.select(self.SEL_ESCALA_UNIDADE):
                    un.extract()  # "cada"
            preco = parse_preco(principal.get_text(" ", strip=True)) if principal else None
            el_atacado = escala.select_one(self.SEL_ESCALA_PRECO)
            atacado = parse_preco(el_atacado.get_text(strip=True)) if el_atacado else None
            tag = escala.select_one(self.SEL_ESCALA_TAG)
            m = _REGEX_QTD_MIN.search(tag.get_text(" ", strip=True)) if tag else None
            qtd_min = int(m.group(1)) if m else None
            if atacado is not None and preco is not None and atacado >= preco:
                atacado = qtd_min = None
            return preco, atacado, qtd_min, None

        bloco = card.select_one(self.SEL_PRECO)
        valores = _REGEX_PRECO.findall(bloco.get_text(" ", strip=True)) if bloco else []
        if not valores:
            return None, None, None, None
        aviso = None
        if len(valores) > 1:
            aviso = f"{len(valores)} valores no bloco de preço: {valores}"
        return parse_preco(valores[0]), None, None, aviso

    def _extrair_card(self, card, categoria: str, url: str) -> Optional[Produto]:
        el_nome = card.select_one(self.SEL_NOME)
        nome = (el_nome.get("title") or el_nome.get_text(strip=True)) if el_nome else ""
        nome = nome.strip()
        if not nome:
            return None

        preco, atacado, qtd_min, aviso = self._extrair_precos(card)
        if not preco:
            return None
        if aviso:
            logger.warning("iFood '%s': %s (usei o 1º) — conferir HTML.", nome, aviso)

        quantidade, unidade = extrair_quantidade_e_unidade(nome)
        if quantidade is None:
            el_det = card.select_one(self.SEL_DETALHE)
            if el_det:
                quantidade, unidade = extrair_quantidade_e_unidade(el_det.get_text(" ", strip=True))

        return Produto(
            fornecedor=self.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=preco,
            quantidade=quantidade,
            unidade=unidade,
            preco_atacado=atacado,
            qtd_minima_atacado=qtd_min,
            url_produto=url,
        )

    def _tirar_print(self, nome: str) -> Optional[str]:
        try:
            card = self.page.locator(
                f'{self.SEL_CARD_PRODUTO}:has({self.SEL_NOME}[title="{nome}"])'
            ).first
            os.makedirs(config.PRINTS_DIR, exist_ok=True)
            seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(" ", "_")[:60]
            caminho = os.path.join(config.PRINTS_DIR, f"{self.nome_fornecedor}_{seguro}.png")
            card.scroll_into_view_if_needed(timeout=5000)
            card.screenshot(path=caminho, timeout=5000)
            return caminho
        except Exception as e:
            logger.warning("Falha ao tirar print de '%s' (iFood): %s", nome, e)
            return None

    def _carregar_tudo(self) -> None:
        """Rola até a quantidade de cards parar de crescer."""
        anterior = -1
        for _ in range(MAX_PAGINAS_SEGURANCA):
            atual = self.page.locator(self.SEL_CARD_PRODUTO).count()
            if atual == anterior:
                break
            anterior = atual
            self.page.mouse.wheel(0, 3000)
            self.page.wait_for_timeout(1200)

    @staticmethod
    def _titulo_limpo(el) -> str:
        """Texto próprio do título (sem o botão/link "Ver todos")."""
        partes = [t for t in el.find_all(string=True, recursive=False)]
        return " ".join(p.strip() for p in partes).strip().lower()

    def _url_do_corredor(self, nome: str, url_base: str) -> Optional[str]:
        """Rola a home da loja até achar o corredor `nome` e devolve a URL do
        seu "Ver todos". Dois layouts vistos no HTML real:
        - `.market-catalog-aisle` com `a.market-catalog-aisle__see-all-items`
          (href com ?corredor=<uuid>);
        - `h2.catalog-group__title` com o uuid no id ("<uuid>-section-id")
          e "Ver todos" como botão (sem href)."""
        alvo = nome.strip().lower()
        for _ in range(MAX_PAGINAS_SEGURANCA):
            soup = BeautifulSoup(self.page.content(), "html.parser")
            for aisle in soup.select(self.SEL_CORREDOR):
                titulo = aisle.select_one(self.SEL_CORREDOR_TITULO)
                if titulo and self._titulo_limpo(titulo) == alvo:
                    link = aisle.select_one(".market-catalog-aisle__see-all-items")
                    if link and link.get("href"):
                        return BASE_URL + link["href"]
            for h2 in soup.select("h2.catalog-group__title"):
                if self._titulo_limpo(h2) == alvo:
                    uuid = (h2.get("id") or "").removesuffix("-section-id")
                    if uuid:
                        return f"{url_base}?originArea=Home&corredor={uuid}"
            self.page.mouse.wheel(0, 2500)
            self.page.wait_for_timeout(1000)
        return None

    # ------------------------------------------------------------------
    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (iFood)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = 0

        # "<loja>#corredor=<Nome do corredor>": o nome vem do menu da loja e
        # o uuid do corredor é descoberto na home (o menu não expõe links)
        url, _, fragmento = url.partition("#")
        nome_corredor = parse_qs(fragmento).get("corredor", [None])[0]

        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            if nome_corredor:
                self.page.wait_for_timeout(3000)
                destino = self._url_do_corredor(nome_corredor, url)
                if not destino:
                    logger.error(
                        "iFood: corredor '%s' não encontrado na home de %s — "
                        "nome mudou ou sessão bloqueada.",
                        nome_corredor, url,
                    )
                    self._salvar_debug_vazio(categoria)
                    return produtos
                url = destino
                self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            try:
                self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=20000)
            except Exception:
                logger.error(
                    "iFood: nenhum card em %s — provável desafio Cloudflare/"
                    "PerimeterX ou sessão expirada. Rode `python setup_sessao.py`.",
                    url,
                )
                self._salvar_debug_vazio(categoria)
                return produtos
            self._carregar_tudo()

            soup = BeautifulSoup(self.page.content(), "html.parser")
            cards = soup.select(self.SEL_CARD_PRODUTO)
            for card in cards:
                produto = self._extrair_card(card, categoria, url)
                if produto is None:
                    sem_preco += 1
                    continue
                if produto.nome in vistos:
                    continue
                vistos.add(produto.nome)

                if palavras_chave and not any(
                    pk.lower() in produto.nome.lower() for pk in palavras_chave
                ):
                    continue
                if getattr(config, "SALVAR_PRINTS_ITENS", False):
                    produto.imagem_print = self._tirar_print(produto.nome)
                produtos.append(produto)

            logger.info(
                "Categoria '%s' (iFood): %d cards, %d produtos extraídos, %d sem preço.",
                categoria, len(cards), len(produtos), sem_preco,
            )
            if cards and not produtos and not palavras_chave:
                self._salvar_debug_vazio(categoria)
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (iFood)", categoria)
        return produtos

    def _salvar_debug_vazio(self, categoria: str) -> None:
        try:
            pasta = os.path.join(config.BASE_DIR, "logs")
            os.makedirs(pasta, exist_ok=True)
            seguro = re.sub(r"[^\w-]", "_", categoria)
            with open(os.path.join(pasta, f"debug_vazio_{seguro}.html"), "w", encoding="utf-8") as f:
                f.write(self.page.content())
        except Exception:
            logger.warning("Não consegui salvar o HTML de debug (iFood).")
