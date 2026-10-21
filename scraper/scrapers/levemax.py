"""
Scraper para o Leve Max SuperAtacado (levemaxsuperatacado.com.br).
Plataforma: VIP Commerce, a mesma do Abevê (Angular; HTML vazio, só `<vip-root>`), então
reaproveita toda a lógica de `AbeveScraper` e só troca os parâmetros da loja.

Como o site funciona (confirmado contra o site real em 19/10/2026):
- Mesma API do Abevê: https://services.vipcommerce.com.br/api-admin/v1/org/277 (277 = Leve Max),
  JWT anônimo (login `loja` + a chave pública da plataforma, igual à do Abevê),
  `DomainKey: levemaxsuperatacado.com.br` (sem "www."), `OrganizationId: 277`.
  Org e filial saem de GET /api-admin/v1/organizacoes/filiais/dominio/<dominio>.
- ATENÇÃO aos ids: a filial administrativa é 315, mas as rotas de loja usam a filial 1
  (`vipcommerce_filial_id`), CD 1 (`centro_distribuicao_padrao_id`). Com 315 a busca devolve
  404 "Não encontrado" e a árvore de categorias vem vazia.
- Loja única, sem CEP nem login para preço; `definir_cep` não faz nada.
- Busca (mesmo formato do Abevê):
  GET /filial/1/centro_distribuicao/1/loja/buscas/produtos/termo/<termo>?page=N
  -> data.produtos[], paginator{items_per_page=20, total_pages, total_items}.
  URL da tarefa: https://www.levemaxsuperatacado.com.br/busca?termo=<termo>&secoes=<ids>.
- Os ids de `classificacao_mercadologica_id` (`secoes`) NÃO são os do Abevê. Árvore do Leve Max
  (.../loja/classificacoes_mercadologicas/departamentos/arvore): 131 Fruta, 133 Legume,
  135 Verdura folha, 134 Ovo, 81/82 Aves, 85 Bovina, 86 Suína, 87 Churrasco, 89 Peixe,
  92 Arroz, 100 Feijão, 120 Manteiga, 127 Queijo, 118 Leite, 169 Leite em pó, 154 Açúcar,
  165 Fermento, 191 Óleo, 174 Azeite, 178 Condimento, 195 Tempero e caldo...
- Produto, peso, promoção ("Preço Leve Max" em oferta.preco_oferta) e dedupe: idênticos ao
  Abevê (ver docstring de scrapers/abeve.py). Item "KG" tem preço de uma unidade aproximada de
  `quantidade_unidade_diferente` kg (ex.: "Banana Maçã 600g" = 7.19 por 0,6 kg), dividido
  para gravar o preço por kg.
"""

from typing import Optional

from scrapers.abeve import AbeveScraper


class LevemaxScraper(AbeveScraper):
    nome_fornecedor = "levemax"

    NOME_LOJA = "Leve Max"
    DESCRICAO_LOJA = "loja única (filial 1 / CD 1)"
    BASE_URL = "https://www.levemaxsuperatacado.com.br"
    DOMINIO = "levemaxsuperatacado.com.br"
    ORG_ID = 277
    FILIAL_ID = 1
    CD_ID = 1

    _token: Optional[str] = None
    _ja_coletados: set = set()
