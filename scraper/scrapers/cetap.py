"""
Scraper para a Cetap Distribuidora (cetap.lifeappsecommerce.com.br/cetap-online/).
Plataforma: LifeApps e-commerce (SPA React; os cards só existem depois do JavaScript).

Como o site funciona (confirmado contra o site real em 21/10/2026):
- Coleta 100% via API, sem navegador. Base:
  https://admin-ecommerce-02.lifeappsecommerce.com.br/api/v1/app/<token>/listaprodutosf/<id_fornecedor>
  O `<token>` do caminho é gerado a cada visita pelo site e a API aceita qualquer valor
  (confirmado com "sometoken" e "x"); sem cookie, sem Cloudflare no domínio da API, funciona
  com urllib. `id_fornecedor` (8459bce2-...) e `formapagamento` (09a46b24-...) são os ids
  da Cetap que o site envia deslogado.
- Parâmetros: sk=<termo> (busca por nome, ignora acentos; vazio = catálogo inteiro),
  page=N (começa em 0), limit (até 100 funciona), canalVenda=WEB, tipoentrega=RETIRADA.
  Resposta: {"status", "dados": [produto...]}; página vazia = fim. O catálogo inteiro tem
  ~1.400 itens (15 páginas de 100). A URL do site para a busca é
  https://cetap.lifeappsecommerce.com.br/cetap-online?query=<termo>.
- Preço: deslogado a API devolve `preco` = 0 (e o site esconde o preço, `display:none`, sem
  uma loja escolhida). O preço de lista vem em `preco_sem_fator` (= `preco_sem_politica_varejo`,
  sem fator de forma de pagamento nem política de cliente). Usa-se `preco` se vier > 0
  (sessão logada) e senão `preco_sem_fator`. Loja única "CETAP" (retirada na loja), sem CEP.
- O PREÇO É SEMPRE O DA EMBALAGEM DE VENDA, e o `unidade` ("UN"/"KG") da API NÃO diz se é por
  kg: "ARROZ 1KG 01X01KG" = 15.89 (pacote de 1 kg); "BOLACHAO 400GR 20X400GR" = 146 (caixa
  com 20; a unidade avulsa, 01X400GR, custa 7.30). Por isso a quantidade vem do sufixo
  "<N>X<tamanho>" do nome (N x tamanho = conteúdo total, ex.: 20X400GR = 8000 g).
- Itens sem esse sufixo e com `unidade` "KG" são caixas de multiplicador desconhecido
  (ex.: "BISC LIANE RECH LIMAO 115GR - Cód. 10737" = 56.70) e são descartados; sem sufixo e
  "UN" cai no parser genérico do nome.
- Sem promoção (`preco_original` sempre nulo; algumas descrições citam "PROMO R$ 4,49" no
  nome, mas o preço da API é o único considerado) e sem atacado mapeado.
- Disponibilidade: `maximo_disponivel` (string, estoque); <= 0 descartado.
- Mesmo produto aparece em várias embalagens (01X..., 20X...) com `id` distintos; dedupe por
  `id` dentro da tarefa e entre as tarefas da execução (o scraper.py cria uma instância por
  tarefa, então o controle fica na classe).
- Catálogo de industrializados (biscoito, snack, bebida, pet, limpeza); poucos insumos do FNDE.
"""

import json
import logging
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from database import Produto
from scrapers.base import BaseScraper
from setup_sessao import USER_AGENT
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://cetap.lifeappsecommerce.com.br/cetap-online"
API_BASE = "https://admin-ecommerce-02.lifeappsecommerce.com.br/api/v1/app/sometoken"
ID_FORNECEDOR = "8459bce2-b4fb-4214-9d14-ec9685ea8527"
ID_FORMA_PAGAMENTO = "09a46b24-08a2-4bcf-bfe6-617227417c29"
ITENS_POR_PAGINA = 100
MAX_PAGINAS_SEGURANCA = 20
PAUSA_ENTRE_PAGINAS_S = (0.5, 1.2)
STATUS_BLOQUEIO = (403, 429, 503)

# "01X01KG", "20X400GR", "12X60g", "01X1,35L" (o sufixo do nome indica N unidades de tamanho T).
_REGEX_EMBALAGEM = re.compile(
    r"(?P<n>\d+)\s*X\s*(?P<tam>\d+[.,]?\d*)\s*(?P<unid>kg|gr|g|ml|lt|l|un|und)\b",
    re.IGNORECASE,
)
# (fator para a unidade-base, unidade gravada)
_UNIDADES = {
    "kg": (1.0, "kg"),
    "gr": (1.0, "g"),
    "g": (1.0, "g"),
    "ml": (1.0, "ml"),
    "l": (1.0, "L"),
    "lt": (1.0, "L"),
    "un": (1.0, "un"),
    "und": (1.0, "un"),
}


class CetapScraper(BaseScraper):
    nome_fornecedor = "cetap"

    # Em nível de classe: o dedupe vale para a execução inteira (uma instância por tarefa).
    _ja_coletados: set = set()  # `id` do item já devolvido nesta execução

    @staticmethod
    def _termo(url: str) -> Optional[str]:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        termo = (query.get("query") or [""])[0].strip()
        return termo or None

    @staticmethod
    def _embalagem(nome: str) -> Optional[tuple[float, str]]:
        """Conteúdo total da embalagem de venda a partir do sufixo NxTAM do nome."""
        m = _REGEX_EMBALAGEM.search(nome)
        if not m:
            return None
        fator, unidade = _UNIDADES[m.group("unid").lower()]
        tamanho = float(m.group("tam").replace(",", "."))
        return round(int(m.group("n")) * tamanho * fator, 3), unidade

    @staticmethod
    def _buscar_pagina(termo: str, pagina: int) -> list[dict]:
        params = urllib.parse.urlencode(
            {
                "sk": termo,
                "page": pagina,
                "formapagamento": ID_FORMA_PAGAMENTO,
                "canalVenda": "WEB",
                "tipoentrega": "RETIRADA",
                "tagsPesquisa": "",
                "agrupadores": "",
                "ignorepolicy": "false",
                "limit": ITENS_POR_PAGINA,
                "produtoprincipal": "",
                "combo": "false",
            }
        )
        req = urllib.request.Request(
            f"{API_BASE}/listaprodutosf/{ID_FORNECEDOR}?{params}",
            headers={
                "Accept": "application/json",
                "Origin": "https://cetap.lifeappsecommerce.com.br",
                "Referer": f"{BASE_URL}/",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp).get("dados") or []

    @classmethod
    def _produto_da_api(cls, item: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        nome = (item.get("nome") or "").strip()
        if not nome:
            return None
        try:
            if float(item.get("maximo_disponivel") or 0) <= 0:
                return None
            preco = float(item.get("preco") or 0) or float(item.get("preco_sem_fator") or 0)
        except (TypeError, ValueError):
            return None
        if preco <= 0:
            return None

        embalagem = cls._embalagem(nome)
        if embalagem:
            quantidade, unidade = embalagem
        elif item.get("unidade") == "KG":
            return None  # caixa de multiplicador desconhecido: o preço não casa com o nome
        else:
            quantidade, unidade = extrair_quantidade_e_unidade(nome)

        slug = item.get("slug")
        return Produto(
            fornecedor=cls.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=round(preco, 2),
            quantidade=quantidade,
            unidade=unidade,
            url_produto=f"{BASE_URL}/produto/{slug}/" if slug else url_fonte,
        )

    def definir_cep(self, cep: str) -> None:
        logger.info("Cetap: loja única (retirada), sem CEP — nada a definir.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        cls = type(self)
        logger.info("Coletando categoria '%s' -> %s (Cetap)", categoria, url)
        produtos: list[Produto] = []
        vistos: set = set()
        descartados = 0

        termo = self._termo(url)
        if not termo:
            logger.error("Cetap: URL sem termo de busca (use ?query=<termo>): %s", url)
            return produtos

        try:
            for pagina in range(MAX_PAGINAS_SEGURANCA):
                try:
                    itens = self._buscar_pagina(termo, pagina)
                except urllib.error.HTTPError as e:
                    nivel = "bloqueio" if e.code in STATUS_BLOQUEIO else "erro"
                    logger.error("Cetap: HTTP %d (%s) em '%s'.", e.code, nivel, categoria)
                    break
                except (urllib.error.URLError, TimeoutError, ValueError) as e:
                    logger.error("Cetap: falha em '%s': %s", categoria, e)
                    break
                if not itens:
                    break

                for item in itens:
                    id_item = item.get("id")
                    if id_item in vistos or id_item in cls._ja_coletados:
                        continue
                    vistos.add(id_item)
                    produto = cls._produto_da_api(item, categoria, url)
                    if produto is None:
                        descartados += 1
                        continue
                    if palavras_chave and not any(
                        pc.lower() in produto.nome.lower() for pc in palavras_chave
                    ):
                        continue
                    cls._ja_coletados.add(id_item)
                    produtos.append(produto)

                if len(itens) < ITENS_POR_PAGINA:
                    break
                time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS_S))
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Cetap)", categoria)

        logger.info(
            "Cetap: %d produtos em '%s' (%d sem preço/estoque/multiplicador).",
            len(produtos),
            categoria,
            descartados,
        )
        return produtos
