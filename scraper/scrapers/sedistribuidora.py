"""
Scraper para a SE Distribuidora de Alimentos (sedistribuidora.com.br/se-distribuidora).
Plataforma: LifeApps e-commerce (a mesma da Cetap; SPA React, cards só depois do JavaScript).

Como o site funciona (confirmado contra o site real em 21/10/2026):
- Coleta 100% via API, sem navegador, mesma API da Cetap (ver scrapers/cetap.py):
  https://admin-ecommerce-02.lifeappsecommerce.com.br/api/v1/app/<token>/listaprodutosf/<id_fornecedor>
  O `<token>` do caminho aceita qualquer valor; `id_fornecedor` = ed603ae5-... (SE) e
  `formapagamento` = 41235035-... (PIX/TRANSF, a forma padrão que o site envia deslogado;
  um id inválido dá HTTP 500). `tipoentrega` (DELIVERY/RETIRADA) não altera o preço.
  Parâmetros: sk=<termo> (busca por nome; vazio = catálogo inteiro), page=N (de 0),
  limit até 100; página vazia = fim. Catálogo de ~1.340 itens (14 páginas de 100). A busca
  do site é https://sedistribuidora.com.br/se-distribuidora?query=<termo> e o produto abre em
  /se-distribuidora/produto/<slug>/.
- Preço: a API devolve `preco` nulo mesmo logado ou não (o site esconde o preço, R$ 0,00),
  mas o preço aparece nos campos `preco_sem_politica_varejo` e `preco_sem_fator`. O primeiro
  já traz o fator da forma de pagamento enviada (PIX = 1,045 sobre o de lista; alguns itens
  têm fator maior: 1,161/1,229) e é o que o cliente paga na forma padrão, por isso é o usado;
  `preco_sem_fator` é o preço de lista e só serve de reserva. Usa-se `preco` se vier > 0.
- O PREÇO É DA EMBALAGEM DE VENDA e `unidade` ("UN"/"KG") não diz nada sobre peso. O conteúdo
  da embalagem vem em `mensagemcardproduto` = "Código:<n> - <conteúdo>", onde o conteúdo é
  "125GR", "1KGR" (sim, KGR), "6X80ML" (display de 6) ou "+/-300GR" (peso aproximado).
  Quantidade = N x tamanho (6X80ML = 480 ml). Sem conteúdo reconhecível, grava-se quantidade
  e unidade nulas (o preço continua válido).
- Sem promoção (`preco_original` sempre nulo) e sem atacado mapeado. Pedido mínimo de R$ 40
  não afeta o preço.
- Disponibilidade: `maximo_disponivel` (string, estoque); <= 0 descartado.
- Dedupe por `id` dentro da tarefa e entre as tarefas da execução (o scraper.py cria uma
  instância por tarefa, então o controle fica na classe).
- Catálogo de industrializados refrigerados/secos (lácteos, congelados, biscoitos, bebidas,
  higiene); quase nenhum insumo do FNDE (sem arroz, feijão, açúcar, macarrão, farinha).
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
from utils.parsers import extrair_marca

logger = logging.getLogger(__name__)

BASE_URL = "https://sedistribuidora.com.br/se-distribuidora"
API_BASE = "https://admin-ecommerce-02.lifeappsecommerce.com.br/api/v1/app/sometoken"
ID_FORNECEDOR = "ed603ae5-14bf-4b66-ab19-5cab7d4c1a37"
ID_FORMA_PAGAMENTO = "41235035-ff2b-4e20-a00a-87c11c5d2ab3"
ITENS_POR_PAGINA = 100
MAX_PAGINAS_SEGURANCA = 20
PAUSA_ENTRE_PAGINAS_S = (0.5, 1.2)
STATUS_BLOQUEIO = (403, 429, 503)

# "6X80ML", "125GR", "1KGR", "+/-300GR", "1,5LT": N opcional x tamanho + unidade.
_REGEX_CONTEUDO = re.compile(
    r"(?:(?P<n>\d+)\s*X\s*)?(?P<tam>\d+[.,]?\d*)\s*(?P<unid>kgr|kg|gr|g|ml|lt|l|un)\b",
    re.IGNORECASE,
)
_UNIDADES = {
    "kgr": "kg",
    "kg": "kg",
    "gr": "g",
    "g": "g",
    "ml": "ml",
    "lt": "L",
    "l": "L",
    "un": "un",
}


class SeDistribuidoraScraper(BaseScraper):
    nome_fornecedor = "sedistribuidora"

    # Em nível de classe: o dedupe vale para a execução inteira (uma instância por tarefa).
    _ja_coletados: set = set()  # `id` do item já devolvido nesta execução

    @staticmethod
    def _termo(url: str) -> Optional[str]:
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        termo = (query.get("query") or [""])[0].strip()
        return termo or None

    @staticmethod
    def _conteudo(mensagem: str) -> tuple[Optional[float], Optional[str]]:
        """Conteúdo total da embalagem a partir de 'Código:<n> - <conteúdo>'."""
        if " - " not in mensagem:
            return None, None
        m = _REGEX_CONTEUDO.search(mensagem.split(" - ", 1)[1])
        if not m:
            return None, None
        tamanho = float(m.group("tam").replace(",", "."))
        quantidade = int(m.group("n") or 1) * tamanho
        return round(quantidade, 3), _UNIDADES[m.group("unid").lower()]

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
                "Origin": "https://sedistribuidora.com.br",
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
            preco = (
                float(item.get("preco") or 0)
                or float(item.get("preco_sem_politica_varejo") or 0)
                or float(item.get("preco_sem_fator") or 0)
            )
        except (TypeError, ValueError):
            return None
        if preco <= 0:
            return None

        quantidade, unidade = cls._conteudo(item.get("mensagemcardproduto") or "")
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
        logger.info("SE Distribuidora: sem CEP/loja a definir — nada a fazer.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        cls = type(self)
        logger.info("Coletando categoria '%s' -> %s (SE Distribuidora)", categoria, url)
        produtos: list[Produto] = []
        vistos: set = set()
        descartados = sem_conteudo = 0

        termo = self._termo(url)
        if not termo:
            logger.error("SE Distribuidora: URL sem termo de busca (?query=<termo>): %s", url)
            return produtos

        try:
            for pagina in range(MAX_PAGINAS_SEGURANCA):
                try:
                    itens = self._buscar_pagina(termo, pagina)
                except urllib.error.HTTPError as e:
                    nivel = "bloqueio" if e.code in STATUS_BLOQUEIO else "erro"
                    logger.error("SE Distribuidora: HTTP %d (%s) em '%s'.", e.code, nivel, categoria)
                    break
                except (urllib.error.URLError, TimeoutError, ValueError) as e:
                    logger.error("SE Distribuidora: falha em '%s': %s", categoria, e)
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
                    if produto.quantidade is None:
                        sem_conteudo += 1
                    cls._ja_coletados.add(id_item)
                    produtos.append(produto)

                if len(itens) < ITENS_POR_PAGINA:
                    break
                time.sleep(random.uniform(*PAUSA_ENTRE_PAGINAS_S))
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (SE Distribuidora)", categoria)

        logger.info(
            "SE Distribuidora: %d produtos em '%s' (%d sem preço/estoque, %d sem conteúdo da embalagem).",
            len(produtos),
            categoria,
            descartados,
            sem_conteudo,
        )
        return produtos
