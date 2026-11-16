"""
Scraper para o DelMoro Supermercados (delmorosupermercados.com.br).
Plataforma: VIP Commerce, a mesma do Abevê, Leve Max, Mega e Casa Aurora (Angular; HTML vazio, só
`<vip-root>`), então reaproveita a lógica de `AbeveScraper` e, do filtro estrito de nomes, a de
`CasaAuroraScraper` (palavra inteira, sem acento, "a+b" e "-x"; ver docstring de
scrapers/casaaurora.py). Só troca os parâmetros da loja.

Como o site funciona (confirmado contra o site real em 29/10/2026):
- Mesma API: https://services.vipcommerce.com.br/api-admin/v1/org/287 (287 = DelMoro),
  JWT anônimo (login `loja` + chave pública da plataforma), `DomainKey:
  delmorosupermercados.com.br` (sem "www."; com "www." a API devolve erro) e
  `OrganizationId: 287`. Org sai de GET /api-admin/v1/organizacoes/filiais/dominio/<dominio>
  (devolve a filial administrativa 328 "DelMoro Supermercados").
- ATENÇÃO aos ids: as rotas de loja usam filial 1 / CD 1. Filial 328 dá 404 e CD 328 devolve
  busca vazia. Loja única, sem CEP nem login para preço; `definir_cep` não faz nada.
- Busca: GET /filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/<termo>?page=N (20/pág).
  URL da tarefa: https://www.delmorosupermercados.com.br/busca?termo=<termo>&secoes=<ids>.
- Árvore de seções (`classificacao_mercadologica_id`, em .../classificacoes_mercadologicas/
  departamentos/arvore): é a MESMA da Casa Aurora (87 Carne bovina, 89 Suína, 83/84 Ave
  congelada/resfriada, 92 Peixe, 135 Fruta, 137 Legume, 140 Verdura folha, 138 Ovo, 95 Arroz,
  97 Farinha de mandioca, 99 Farinha de trigo, 100 Farinha e creme de milho, 103 Feijão, 104 Fubá,
  161 Aveia e mingau, 162 Açúcar, 170 Fermento, 174 Leite em pó, 124 Manteiga, 131 Queijo,
  180 Azeite, 202 Óleo, 184 Condimento, 200 Tempero e caldo, 186-191 Macarrão...), por isso as
  tarefas de data/tarefas/delmoro.py são derivadas das da Casa Aurora.
- Peso: `KG` com `quantidade_unidade_diferente` N = preço de ~N kg (ex.: "Banana Prata Região
  700g" = 7.34 por 0,7 kg), dividido para gravar por kg. Frango inteiro congelado também vem como
  `KG` (ex.: 3,7 kg). Itens `UN` guardam o preço da embalagem e a quantidade vem do nome.
  Promoção em `oferta.preco_oferta` (`preco_antigo` = cheio); sem preço atacado mapeado.
- Produto, indisponível e dedupe: idênticos ao Abevê (ver docstring de scrapers/abeve.py).
"""

from typing import Optional

from database import Produto
from scrapers.casaaurora import CasaAuroraScraper

_FATOR_PARA_KG = {"kg": 1.0, "g": 0.001, "l": 1.0, "ml": 0.001}


def _preco_por_kg(produto: Produto) -> float:
    """Preço normalizado por kg/L para comparar embalagens; sem medida, o preço bruto."""
    fator = _FATOR_PARA_KG.get((produto.unidade or "").lower())
    if not fator or not produto.quantidade:
        return produto.preco
    return produto.preco / (produto.quantidade * fator)


class DelMoroScraper(CasaAuroraScraper):
    nome_fornecedor = "delmoro"

    # Categorias em que cada tarefa devolve só o produto mais barato (por kg): usado no macarrão,
    # onde a coleta quer 1 item por formato (espaguete, penne, parafuso).
    CATEGORIAS_SO_MAIS_BARATO = {"MACARRÃO"}

    NOME_LOJA = "DelMoro"
    DESCRICAO_LOJA = "loja única (filial 1 / CD 1)"
    BASE_URL = "https://www.delmorosupermercados.com.br"
    DOMINIO = "delmorosupermercados.com.br"
    ORG_ID = 287
    FILIAL_ID = 1
    CD_ID = 1

    _token: Optional[str] = None
    _ja_coletados: set = set()

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        produtos = super().extrair_produtos_da_pagina(categoria, url, palavras_chave)
        if categoria in self.CATEGORIAS_SO_MAIS_BARATO and len(produtos) > 1:
            produtos = [min(produtos, key=_preco_por_kg)]
        return produtos
