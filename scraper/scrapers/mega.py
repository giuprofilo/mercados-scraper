"""
Scraper para o Atacadista Mega "Mega em Casa" (megaemcasa.atacadistamega.com.br), loja Mega
Mercado (retirada na Rua Joaquim Murtinho, 1811).
Plataforma: VIP Commerce, a mesma do Abevê e do Leve Max (Angular; HTML vazio, só `<vip-root>`),
então reaproveita toda a lógica de `AbeveScraper` e só troca os parâmetros da loja.

Como o site funciona (confirmado contra o site real em 19/10/2026):
- Mesma API: https://services.vipcommerce.com.br/api-admin/v1/org/224 (224 = Atacadista Mega),
  JWT anônimo (login `loja` + chave pública da plataforma, igual à das outras lojas),
  `DomainKey: megaemcasa.atacadistamega.com.br` (sem "www."; o domínio raiz
  atacadistamega.com.br não é uma loja), `OrganizationId: 224`.
  Org sai de GET /api-admin/v1/organizacoes/filiais/dominio/<dominio> (filial administrativa 258).
- ATENÇÃO aos ids: as rotas de loja usam filial 1 e o CD **27** (`centro_distribuicao_padrao_id`,
  é o que o site chama). A filial 258 dá 404. O CD 1 também responde, mas com outro catálogo
  (ex.: "arroz" tem 104 resultados no CD 1 e 137 no CD 27), por isso o CD fixo é o 27.
- Loja única, sem CEP nem login para preço; `definir_cep` não faz nada.
- Busca: GET /filial/1/centro_distribuicao/27/loja/buscas/produtos/termo/<termo>?page=N
  (20/pág). URL da tarefa: https://www.megaemcasa.atacadistamega.com.br/busca?termo=<termo>&secoes=<ids>.
- Os ids de `classificacao_mercadologica_id` (`secoes`) são próprios (e a árvore vem sem acento).
  Árvore do Mega (.../loja/classificacoes_mercadologicas/departamentos/arvore): 122 Fruta,
  124 Legume, 126 Verdura folha, 125 Ovo, 17/18 Aves, 21 Bovina, 22 Suína, 23 Churrasco,
  26 Peixe, 82 Arroz, 90 Feijão, 111 Manteiga, 118 Queijo, 109 Leite, 160 Leite em pó,
  145 Açúcar, 156 Fermento, 179 Óleo, 164 Azeite, 167 Condimento, 183 Tempero e caldo...
- Peso: hortifrúti vem como "KG" com nome "<fruta> unidade (aprox. 0.500g)" e
  `quantidade_unidade_diferente` 0.5, ou seja, o `preco` é de ~0,5 kg (ex.: "Banana Prata" 5.95
  = 11.90/kg). A lógica do Abevê divide e grava por kg. Promoção em `oferta.preco_oferta`
  ("Oferta"), sem preço atacado mapeado.
- Produto, dedupe e demais regras: idênticos ao Abevê (ver docstring de scrapers/abeve.py).
"""

from typing import Optional

from scrapers.abeve import AbeveScraper


class MegaScraper(AbeveScraper):
    nome_fornecedor = "mega"

    NOME_LOJA = "Mega"
    DESCRICAO_LOJA = "loja única (filial 1 / CD 27)"
    BASE_URL = "https://www.megaemcasa.atacadistamega.com.br"
    DOMINIO = "megaemcasa.atacadistamega.com.br"
    ORG_ID = 224
    FILIAL_ID = 1
    CD_ID = 27

    _token: Optional[str] = None
    _ja_coletados: set = set()
