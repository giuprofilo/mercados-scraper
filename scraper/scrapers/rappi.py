"""
Scraper para lojas no Rappi (rappi.com.br). Uma classe por loja, que só
muda o nome do fornecedor gravado; a loja em si vem na URL das tarefas:
- "rappi": Assaí Atacadista Água Verde (Curitiba/PR),
  loja 900637167-assaiatacadista-nc.
- "rappi_condor": Condor (Curitiba/PR),
  loja 900685906-condor-supermer-alpormayor-nc.
Plataforma: Next.js + API "web-gateway" do Rappi. Os produtos são lidos
do JSON (não do HTML), então não há seletor CSS de preço a manter.

Como o site funciona (confirmado contra o site real):
- A loja vem na URL (/lojas/<id>-<store_type>) e o preço é o daquela loja;
  não precisa definir CEP/endereço (o CEP 80730-420 cai na área das lojas).
- Subcategorias têm URL própria: /lojas/<loja>/<departamento>/<corredor>.
  A busca também: /lojas/<loja>/s?term=<termo> (lista única, sem "Ver mais").
  Os nomes dos corredores são do Rappi, iguais em todas as lojas.
- A página traz os primeiros 24 produtos no JSON do __NEXT_DATA__
  (fallback -> aisle_detail_response). O resto vem do botão "Ver mais",
  que faz POST em services.rappi.com.br/.../dynamic/context/content/ com
  context "aisle_detail" e offset 6, 12, 18... (cada "linha" são 6
  produtos). O infinite scroll do site para antes do fim, então aqui a
  requisição é capturada no 1º clique e repetida trocando o offset até a
  API responder 204 (fim). Qualquer outro erro (ex: limite de requisições)
  é repetido — antes, isso cortava a categoria no meio sem aviso.
- sale_type: "U" = unidade/pacote (price é o do pacote); "WB", "WP", "WW"
  = vendido por peso — nesses, balance_price é o preço POR KG (price é o
  de uma unidade/bandeja aproximada), então é ele que é gravado, com
  quantidade 1 kg.
- Promoção: real_price (ou real_balance_price, no peso) é o preço cheio e
  "discount" é a fração de desconto (0.34 = -34%).
- Quando a loja não tem o item, o Rappi completa a lista (principalmente
  no "Ver mais" e na busca) com produtos de OUTRAS lojas (ex: "Coxa Seara
  Iqf 1 Kg" do Sam's Club aparecendo no Condor). Cada produto traz
  store_id, então só entra o que for da loja da URL da tarefa.
- Os corredores misturam coisas (ex: "Bovinos" tem hambúrguer e suíno),
  por isso as palavras_chave das tarefas importam. Um produto pode vir
  repetido entre blocos — dedupe por product_id.
"""

import json
import os
import re
import logging
import unicodedata
from typing import Optional
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://www.rappi.com.br"
# a página já vem com 4 blocos de 6; com menos que isso não há "Ver mais"
# de produtos (o botão que aparecer é de outra seção)
ITENS_NA_PAGINA = 24
MAX_PAGINAS_SEGURANCA = 50
TENTATIVAS_VER_MAIS = 3
TENTATIVAS_API = 4


class RappiScraper(BaseScraper):
    nome_fornecedor = "rappi"
    nome_loja = "Assaí Água Verde, Curitiba/PR"

    SEL_CARD_PRODUTO = 'a[href^="/p/"]'
    SEL_VER_MAIS = "button:has-text('Ver mais')"

    def definir_cep(self, cep: str) -> None:
        logger.info(
            "Rappi: a loja vem na URL (%s) — nada a definir.", self.nome_loja
        )

    @staticmethod
    def _eh_carregar_mais(request) -> bool:
        return (
            "dynamic/context/content" in request.url
            and '"aisle_detail"' in (request.post_data or "")
        )

    @staticmethod
    def _produtos_do_data(data: dict) -> list[dict]:
        return [
            p
            for comp in data.get("components") or []
            for p in (comp.get("resource") or {}).get("products") or []
        ]

    def _produtos_iniciais(self) -> list[dict]:
        bruto = self.page.locator("script#__NEXT_DATA__").text_content()
        fallback = json.loads(bruto)["props"]["pageProps"].get("fallback") or {}
        produtos = []
        for valor in fallback.values():
            valor = valor or {}
            resposta = valor.get("aisle_detail_response") or {}
            produtos += self._produtos_do_data(resposta.get("data") or {})
            # página de busca (/s?term=...): lista direta, sem blocos
            produtos += valor.get("products") or []
        return produtos

    def _fechar_modal_login(self) -> None:
        """A partir do 2º "Ver mais" da sessão o site abre o modal "Confirme
        sua identidade" (pede login), sem botão de fechar e que ignora Esc.
        A API responde mesmo assim; o modal só escurece a página e estraga
        os prints, então é removido do DOM (a próxima categoria abre com
        goto, que recarrega a página inteira)."""
        self.page.wait_for_timeout(1000)
        self.page.evaluate(
            """() => {
                document.querySelectorAll('.chakra-portal').forEach(e => e.remove());
                document.body.style.removeProperty('overflow');
            }"""
        )

    def _produtos_restantes(self) -> list[dict]:
        """Clica em "Ver mais" e repete a chamada da API trocando o offset."""
        botao = self.page.locator(self.SEL_VER_MAIS)
        if botao.count() == 0:
            return []

        # depois de algumas páginas o site abre um modal (chakra) por cima de
        # tudo, que bloqueia o clique normal; o dispatch_event não passa
        # pela sobreposição. Às vezes o clique não faz nada (a página ainda
        # não hidratou) — aí recarrega e tenta de novo.
        req = None
        for tentativa in range(1, TENTATIVAS_VER_MAIS + 1):
            if tentativa > 1:
                logger.info("'Ver mais' sem resposta — recarregando (%d).", tentativa)
                self.page.reload(timeout=config.NAV_TIMEOUT_MS)
                self.page.wait_for_timeout(3000)
            self.page.keyboard.press("Escape")
            try:
                with self.page.expect_request(
                    self._eh_carregar_mais, timeout=8000
                ) as info:
                    botao.first.dispatch_event("click")
                req = info.value
                break
            except PlaywrightTimeoutError:
                continue
        if req is None:
            raise RuntimeError("o botão 'Ver mais' não disparou a requisição")
        self._fechar_modal_login()
        corpo = json.loads(req.post_data)
        # só os headers da aplicação (token, deviceid...); os sec-*/CORS
        # são do navegador
        headers = {
            k: v
            for k, v in req.headers.items()
            if not k.startswith(("sec-", "access-control"))
        }

        produtos = []
        offset, passo = corpo["offset"], corpo["limit"]
        for _ in range(MAX_PAGINAS_SEGURANCA):
            corpo["offset"] = offset
            resp = self._post_com_retentativa(req.url, corpo, headers)
            if resp is None:
                logger.warning(
                    "API do Rappi falhou no offset %d — categoria incompleta "
                    "(%d itens via 'Ver mais').",
                    offset,
                    len(produtos),
                )
                break
            # depois do último bloco a API responde 204, sem corpo
            if resp.status == 204 or not resp.text().strip():
                break
            lote = self._produtos_do_data(resp.json().get("data") or {})
            if not lote:
                break
            produtos += lote
            offset += passo
        return produtos

    def _post_com_retentativa(self, url: str, corpo: dict, headers: dict):
        """POST na API; em erro (429/5xx, rede) espera e tenta de novo.
        Devolve a resposta, ou None se todas as tentativas falharem."""
        for tentativa in range(1, TENTATIVAS_API + 1):
            try:
                resp = self.page.request.post(
                    url, data=json.dumps(corpo), headers=headers
                )
                if resp.ok:
                    return resp
                logger.info(
                    "API do Rappi respondeu %d (offset %d, tentativa %d).",
                    resp.status,
                    corpo["offset"],
                    tentativa,
                )
            except Exception as e:
                logger.info(
                    "Erro na API do Rappi (offset %d, tentativa %d): %s",
                    corpo["offset"],
                    tentativa,
                    e,
                )
            self.page.wait_for_timeout(2000 * tentativa)
        return None

    @staticmethod
    def _slug(nome: str) -> str:
        """Mesma regra do site para o slug do link /p/<slug>-<id> (conferida
        em 205 produtos): sem acento, minúsculo, pontuação removida (não
        vira hífen), espaços viram hífen, corta em 35 caracteres — mesmo que
        o corte termine em hífen."""
        s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
        s = re.sub(r"[^a-z0-9\s-]", "", s.lower())
        return re.sub(r"[\s-]+", "-", s.strip())[:35]

    def _url_produto(self, p: dict, hrefs: dict[str, str]) -> str:
        # link do card na página (o mesmo do "copiar endereço do link");
        # para o que veio só pela API, monta com a regra do site
        mpid = str(p["master_product_id"])
        href = hrefs.get(mpid) or f"/p/{self._slug(p['name'])}-{mpid}"
        return f"{BASE_URL}{href}"

    def _hrefs_da_pagina(self) -> dict[str, str]:
        """master_product_id -> href de cada card renderizado."""
        hrefs = self.page.eval_on_selector_all(
            self.SEL_CARD_PRODUTO, "els => els.map(e => e.getAttribute('href'))"
        )
        return {h.rsplit("-", 1)[1]: h for h in hrefs if "-" in h}

    def _montar_produto(
        self, p: dict, categoria: str, hrefs: dict[str, str]
    ) -> Optional[Produto]:
        nome = (p.get("name") or "").strip()
        if not nome or not p.get("price"):
            return None

        por_peso = str(p.get("sale_type", "")).startswith("W")
        if por_peso:
            preco = round(p["balance_price"], 2)
            cheio = round(p.get("real_balance_price") or 0, 2)
            quantidade, unidade = 1.0, "kg"
        else:
            preco = round(p["price"], 2)
            cheio = round(p.get("real_price") or 0, 2)
            quantidade, unidade = extrair_quantidade_e_unidade(nome)
            if quantidade is None:
                # "presentation" traz a embalagem: "150 g", "1 X 16 Und"
                quantidade, unidade = extrair_quantidade_e_unidade(
                    p.get("presentation") or ""
                )

        preco_original = desconto = None
        if cheio > preco:
            preco_original = cheio
            fracao = p.get("discount") or (1 - preco / cheio)
            desconto = f"-{round(fracao * 100)}%"

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
            url_produto=self._url_produto(p, hrefs),
        )

    def _tirar_print(self, p: dict) -> Optional[str]:
        """Print do card do produto, se ele estiver na página. None se falhar."""
        nome = p["name"]
        try:
            seletor = f'{self.SEL_CARD_PRODUTO}[href$="-{p["master_product_id"]}"]'
            links = self.page.locator(seletor)
            if links.count() == 0:
                # veio só pela API (depois do que o site renderizou)
                return None
            os.makedirs(config.PRINTS_DIR, exist_ok=True)
            nome_seguro = re.sub(r'[\\/*?:"<>|]', "", nome).replace(" ", "_")[:60]
            caminho = os.path.join(
                config.PRINTS_DIR, f"{self.nome_fornecedor}_{p['product_id']}_{nome_seguro}.png"
            )
            # cada card tem 2 links para o produto: a imagem (caixa 0x0,
            # "invisível") e o bloco de preço/nome. O card é o primeiro
            # ancestral que contém os dois.
            card = links.first.evaluate_handle(
                """(el, sel) => {
                    let n = el.parentElement;
                    while (n && n.querySelectorAll(sel).length < 2) n = n.parentElement;
                    return n || el;
                }""",
                seletor,
            ).as_element()
            card.scroll_into_view_if_needed(timeout=5000)
            self.page.wait_for_timeout(100)
            card.screenshot(path=caminho, timeout=5000)
            return caminho
        except Exception as e:
            logger.warning("Falha ao tirar print de '%s' (Rappi): %s", nome, e)
            return None

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        logger.info("Coletando categoria '%s' -> %s (Rappi)", categoria, url)
        produtos: list[Produto] = []
        vistos: set[str] = set()
        sem_preco = indisponiveis = 0
        de_outra_loja: dict[str, int] = {}
        loja = re.search(r"/lojas/(\d+)-", url)
        store_id = loja.group(1) if loja else None

        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            self.page.wait_for_selector(
                "script#__NEXT_DATA__", state="attached", timeout=15000
            )
            self.page.wait_for_timeout(3000)

            iniciais = self._produtos_iniciais()
            restantes: list[dict] = []
            try:
                if len(iniciais) >= ITENS_NA_PAGINA:
                    restantes = self._produtos_restantes()
            except Exception as e:
                logger.warning(
                    "Falha ao carregar mais produtos de '%s' (Rappi): %s — "
                    "seguindo só com os iniciais.",
                    categoria,
                    e,
                )
            self.page.wait_for_timeout(1000)
            logger.info(
                "%d itens na página + %d via 'Ver mais'.",
                len(iniciais),
                len(restantes),
            )

            hrefs = self._hrefs_da_pagina()
            for p in iniciais + restantes:
                pid = str(p.get("product_id"))
                if pid in vistos:
                    continue
                vistos.add(pid)

                if store_id and str(p.get("store_id")) != store_id:
                    outra = p.get("store_type") or str(p.get("store_id"))
                    de_outra_loja[outra] = de_outra_loja.get(outra, 0) + 1
                    continue

                if not (p.get("in_stock") and p.get("is_available", True)):
                    indisponiveis += 1
                    continue

                produto = self._montar_produto(p, categoria, hrefs)
                if produto is None:
                    sem_preco += 1
                    continue

                if palavras_chave and not any(
                    pk.lower() in produto.nome.lower() for pk in palavras_chave
                ):
                    continue

                if getattr(config, "SALVAR_PRINTS_ITENS", False):
                    produto.imagem_print = self._tirar_print(p)

                produtos.append(produto)

            if de_outra_loja:
                logger.info(
                    "Categoria '%s' (Rappi): %d itens de outras lojas "
                    "descartados: %s",
                    categoria,
                    sum(de_outra_loja.values()),
                    de_outra_loja,
                )
            logger.info(
                "Categoria '%s' (Rappi): %d produtos extraídos, %d sem preço, "
                "%d indisponíveis.",
                categoria,
                len(produtos),
                sem_preco,
                indisponiveis,
            )
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Rappi)", categoria)

        return produtos


class RappiCondorScraper(RappiScraper):
    nome_fornecedor = "rappi_condor"
    nome_loja = "Condor, Curitiba/PR"
