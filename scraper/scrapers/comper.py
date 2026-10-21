"""
Scraper para o Comper (comper.com.br, Campo Grande/MS).
Plataforma: Osuper (a mesma do Asun/Fort, mas com front novo: Tailwind + modais;
NÃO use os seletores deles).

Como o site funciona (confirmado contra o site real em 15/10/2026):
- Produtos só existem no cliente: o HTML servido não tem cards. Os dados vêm da API
  GET sense.osuper.com.br/335/<loja>/v2/search?categoryId=<id>&size=N&from=M
  (335 = rede Comper; <loja> = id da loja). Resposta: hits[], total, nextFrom,
  hasNext. A API exige o header `x-osuper-search-token` (gerado pela própria página
  e reaproveitável) e o Cloudflare barra requisição fora do navegador (403), por
  isso o scraper abre a página da subcategoria, captura a 1ª chamada `/search` (que
  traz o `categoryId` e o token) e repete as demais páginas com `fetch` DENTRO da
  página (page.evaluate). `size` máximo = 20.
- Headless é barrado (CDN da Osuper devolve 403 e nada renderiza); com Chrome real
  em janela (config.NAVEGADOR_CANAL = "chrome", HEADLESS = False) funciona.
- Loja: fica no cookie `st_335` do perfil persistente. Escolha 1x com
  `python setup_sessao.py` (modal "Selecione uma loja"); `definir_cep` não faz nada e o
  CEP é ignorado. Sem escolha, o site usa a loja por geolocalização (caiu em
  Tamandaré - 67 = id 1584, Campo Grande/MS; outras de Campo Grande: Brilhante - 71,
  Itanhangá - 102). O scraper loga o id da loja usada (path da chamada /search).
- URL da tarefa: /categorias/<departamento>/<subcategoria> (listagem completa da
  subcategoria; `/categorias/<departamento>` só mostra carrossel).
- hit: name, saleUnit ("KG" ou "UN"), pricing{price, promotion, promotionalPrice,
  discount}. saleUnit "KG" = preço já é por kg (grava 1 kg). Promoção: price é o
  cheio e promotionalPrice o ativo. Sem preço atacado. `quantity.inStock` <= 0 é
  tratado como indisponível.
- Produto abre em modal, sem URL própria: `url_produto` = página da subcategoria.
- Dedupe por `id` do hit.
"""

import os
import re
import json
import logging
from typing import Optional

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://www.comper.com.br"
REDE_ID = "335"
API_POR_PAGINA = 20  # limite da API
MAX_PAGINAS_SEGURANCA = 100
ESPERA_API_MS = 25_000

_JS_BUSCAR = """async ([url, token]) => {
    const r = await fetch(url, {headers: {'x-osuper-search-token': token,
                                          'accept': 'application/json'}});
    return [r.status, await r.text()];
}"""


class ComperScraper(BaseScraper):
    nome_fornecedor = "comper"

    _loja_logada: Optional[str] = None

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "Comper: a loja vem do perfil salvo (python setup_sessao.py); CEP %s ignorado.", cep
        )

    @staticmethod
    def _produto_do_hit(hit: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        nome = (hit.get("name") or "").strip()
        precos = hit.get("pricing") or {}
        normal = precos.get("price")
        promo = precos.get("promotionalPrice") if precos.get("promotion") else None
        preco = promo or normal
        estoque = (hit.get("quantity") or {}).get("inStock")
        if not nome or not preco or preco <= 0 or (estoque is not None and estoque <= 0):
            return None

        preco_original = desconto = None
        if promo and normal and normal > promo:
            preco_original = float(normal)
            desconto = f"-{round((1 - promo / normal) * 100)}%"

        if hit.get("saleUnit") == "KG":
            quantidade, unidade = 1.0, "kg"  # preço já é por kg
        else:
            quantidade, unidade = extrair_quantidade_e_unidade(nome)

        return Produto(
            fornecedor=ComperScraper.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=float(preco),
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=url_fonte,
        )

    def _capturar_busca(self, url: str) -> Optional[dict]:
        """Abre a página e devolve {url, token} da 1ª chamada /search com categoryId."""
        captura: dict = {}

        def ao_responder(resp):
            if captura or "sense.osuper.com.br" not in resp.url:
                return
            if "/search" in resp.url and "categoryId=" in resp.url:
                captura["url"] = resp.url
                captura["token"] = resp.request.headers.get("x-osuper-search-token")

        self.page.on("response", ao_responder)
        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            for _ in range(ESPERA_API_MS // 500):
                if captura:
                    break
                self.page.wait_for_timeout(500)
        finally:
            self.page.remove_listener("response", ao_responder)
        return captura or None

    def _buscar(self, url_base: str, token: str, inicio: int) -> Optional[dict]:
        url = re.sub(r"size=\d+", f"size={API_POR_PAGINA}", url_base)
        url = re.sub(r"from=\d+", f"from={inicio}", url)
        status, corpo = self.page.evaluate(_JS_BUSCAR, [url, token])
        if status != 200:
            logger.warning("Comper: API respondeu %s em from=%s", status, inicio)
            return None
        return json.loads(corpo)

    def _salvar_debug_pagina_vazia(self, categoria: str) -> None:
        logs_dir = os.path.join(config.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        nome = re.sub(r"[^\w-]", "_", categoria)
        caminho = os.path.join(logs_dir, f"debug_vazio_comper_{nome}.html")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.page.content())
        logger.error("0 produtos em '%s' (Comper). HTML salvo em %s", categoria, caminho)

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Comper)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = fora_do_filtro = 0

        try:
            busca = self._capturar_busca(url)
            if not busca or not busca.get("token"):
                logger.error("Comper: chamada /search não capturada em %s", url)
            else:
                loja = re.search(rf"/{REDE_ID}/(\d+)/", busca["url"])
                if loja and loja.group(1) != self._loja_logada:
                    self._loja_logada = loja.group(1)
                    logger.info("Comper: coletando na loja id %s (do perfil).", self._loja_logada)

                inicio = 0
                for _ in range(MAX_PAGINAS_SEGURANCA):
                    dados = self._buscar(busca["url"], busca["token"], inicio)
                    if not dados:
                        break
                    for hit in dados.get("hits", []):
                        id_hit = str(hit.get("id"))
                        if id_hit in vistos:
                            continue
                        vistos.add(id_hit)
                        nome = hit.get("name") or ""
                        if palavras_chave and not any(
                            pk.lower() in nome.lower() for pk in palavras_chave
                        ):
                            fora_do_filtro += 1
                            continue
                        produto = self._produto_do_hit(hit, categoria, url)
                        if produto is None:
                            sem_preco += 1
                            continue
                        produtos.append(produto)
                    if not dados.get("hasNext"):
                        break
                    inicio = dados.get("nextFrom") or inicio + API_POR_PAGINA

            logger.info(
                "Categoria '%s' (Comper): %d extraídos, %d sem preço/indisponíveis, "
                "%d fora do filtro.",
                categoria,
                len(produtos),
                sem_preco,
                fora_do_filtro,
            )
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Comper)", categoria)

        if not produtos:
            try:
                self._salvar_debug_pagina_vazia(categoria)
            except Exception:
                logger.exception("Falha ao salvar HTML de debug (Comper)")

        return produtos
