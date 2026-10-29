"""
Scraper para a Casa Aurora Supermercados (casaaurorasupermercados.com.br), loja Casa Aurora Sinop/MT.
Plataforma: VIP Commerce, a mesma do Abevê, Leve Max e Mega (Angular; HTML vazio, só `<vip-root>`),
então reaproveita a lógica de `AbeveScraper` e só troca os parâmetros da loja e o filtro de nomes.

Como o site funciona (confirmado contra o site real em 29/10/2026):
- Mesma API: https://services.vipcommerce.com.br/api-admin/v1/org/289 (289 = Casa Aurora),
  JWT anônimo (login `loja` + chave pública da plataforma), `DomainKey:
  casaaurorasupermercados.com.br` (sem "www."; com "www." a API devolve erro) e
  `OrganizationId: 289`. Org sai de GET /api-admin/v1/organizacoes/filiais/dominio/<dominio>
  (devolve a filial administrativa 330 "Casa Aurora Sinop"; as rotas de loja com 330 dão 404).
- Rotas de loja: filial 1 / CD 1. Loja única, sem CEP nem login para preço; `definir_cep` não faz nada.
- Busca: GET /filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/<termo>?page=N (20/pág).
  URL da tarefa: https://www.casaaurorasupermercados.com.br/busca?termo=<termo>&secoes=<ids>.
  A busca ignora acentos e trata a frase como OR de palavras ("carne moida" traz TODO o bovino),
  por isso as tarefas usam um termo de uma palavra e dependem do filtro abaixo.
- Árvore de seções (`classificacao_mercadologica_id`, em .../classificacoes_mercadologicas/
  departamentos/arvore): 87 Carne bovina, 89 Suína, 83/84 Ave congelada/resfriada, 92 Peixe,
  88 Exótica, 135 Fruta, 137 Legume, 140 Verdura folha, 138 Ovo, 95 Arroz, 94 Amendoim e canjica,
  97 Farinha de mandioca, 99 Farinha de trigo, 100 Farinha e creme de milho, 103 Feijão,
  104 Fubá, 161 Aveia e mingau, 162 Açúcar, 170 Fermento, 174 Leite em pó, 124 Manteiga,
  131 Queijo, 180 Azeite, 202 Óleo, 184 Condimento, 200 Tempero e caldo, 126 Massa fresca,
  186 Lasanha e grano duro, 187-191 Macarrão (ovos, especial, instantâneo, integral, sêmola).
- Peso: igual ao Abevê. `KG` com `quantidade_unidade_diferente` N = preço de ~N kg (ex.:
  "Banana Prata 700g" 12.59 = 17.99/kg), dividido para gravar por kg. Congelados de ave vêm como
  `UN` com o peso no nome ("Coxa De Frango Sadia Congelada 1kg"): quantidade/unidade do nome.
  Promoção em `oferta.preco_oferta` ("Ofertas"; `preco_antigo` = cheio), sem preço atacado.
- Hortifrúti tem muitas bandejas ("Brócolis Bandeja 300g"); a planilha manda não coletar bandeja,
  então as tarefas excluem "bandeja".

Filtro de nomes (`palavras_chave` das tarefas), mais estrito que o do Abevê:
- Sem acento e sem diferença de maiúscula: "brócolis" e "brocolis" são a mesma palavra.
- Palavra inteira: "maca" (maçã) não casa "macarrão"; "alho" não casa "galho".
- Cada item da lista é uma alternativa (basta uma casar). Dentro do item, "a+b" exige as duas
  (qualquer ordem, ex.: "manteiga+sem sal"). Item começando com "-" é exclusão e vence tudo
  (ex.: "-bandeja", "-orelha"). Lista só com exclusões não aceita nada.
- Massas: todo produto das seções de macarrão/massa/lasanha (SECOES_MACARRAO) sai com a categoria
  "MACARRÃO", seja qual for a categoria da tarefa que o encontrou.
"""

import re
import unicodedata
from functools import lru_cache
from typing import Optional

from database import Produto
from scrapers.abeve import AbeveScraper

SECOES_MACARRAO = {126, 186, 187, 188, 189, 190, 191}
CATEGORIA_MACARRAO = "MACARRÃO"


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


@lru_cache(maxsize=None)
def _palavra(termo: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(_normalizar(termo.strip()))}(?!\w)")


def _casa(nome_normalizado: str, item: str) -> bool:
    return all(_palavra(parte).search(nome_normalizado) for parte in item.split("+"))


class CasaAuroraScraper(AbeveScraper):
    nome_fornecedor = "casaaurora"

    NOME_LOJA = "Casa Aurora"
    DESCRICAO_LOJA = "loja única (Sinop/MT, filial 1 / CD 1)"
    BASE_URL = "https://www.casaaurorasupermercados.com.br"
    DOMINIO = "casaaurorasupermercados.com.br"
    ORG_ID = 289
    FILIAL_ID = 1
    CD_ID = 1

    _token: Optional[str] = None
    _ja_coletados: set = set()

    @staticmethod
    def _nome_confere(nome: str, palavras_chave: list[str]) -> bool:
        normalizado = _normalizar(nome)
        inclusoes = [p for p in palavras_chave if not p.startswith("-")]
        exclusoes = [p[1:] for p in palavras_chave if p.startswith("-")]
        if any(_casa(normalizado, e) for e in exclusoes):
            return False
        return any(_casa(normalizado, i) for i in inclusoes)

    @classmethod
    def _produto_da_api(cls, item: dict, categoria: str, url_fonte: str) -> Optional[Produto]:
        if item.get("classificacao_mercadologica_id") in SECOES_MACARRAO:
            categoria = CATEGORIA_MACARRAO
        return super()._produto_da_api(item, categoria, url_fonte)
