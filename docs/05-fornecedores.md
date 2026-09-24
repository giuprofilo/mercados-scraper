# 05 — Fornecedores já mapeados

Fonte da verdade detalhada = docstring no topo de `scraper/scrapers/<x>.py` (ler só a do site em questão).
Chave = valor de `"fornecedor"` nas tarefas e em `SCRAPERS_DISPONIVEIS`.

| Chave | Site | Plataforma | Região / loja | Fonte dos dados | Paginação | Atacado/promo | Notas |
|---|---|---|---|---|---|---|---|
| `atacadao` | atacadao.com.br | VTEX | CEP/loja em modal (pulado se perfil persistente existe) | HTML, `data-testid` (`store-product-card-content`, `product-link`) | `?page=N` ou "Mostrar mais" (até `MAX_PAGINAS_POR_CATEGORIA`) | `preco_atacado`+`qtd_minima` | tarefas: `data/tarefas/atacadao.py` |
| `stock` | stokonline.com.br | VIP | CEP em modal (idem perfil) | HTML, `.vip-card-produto`, `data-cy` | scroll infinito | — | tarefas ativas por último; `atacado` não mapeado |
| `asun` | levemaisonline.com.br | Osuper | CEP/loja (`text=Loja de`) | HTML `.item-product-wrapper`; nome no `alt` da img; URLs via `ld+json` | botão "mostrar mais" | preço riscado `.text-full-price` + badge; **não** é atacarejo (rodapé mente) | cards sem `href` |
| `fort` | fortatacadista.com.br | Osuper (HTML diferente do Asun!) | CEP/loja (`text=Você está na loja`) | HTML `.products-list-body a`; riscado `.line-through`; URLs via `ld+json` | botão "mostrar mais" | atacarejo real: `preco_atacado` frequente | seletores do Asun **não** valem |
| `gimba` | gimba.com.br | ASP.NET próprio (server-side) | sem CEP; preço depende da **conta CNPJ** (login manual por e-mail+código) | HTML `.CardProduto`, `h2.ChamaItem`, `.CardPrecoDE/POR/LeveMais` | AJAX `PaginaLista(n)`, 60/pág, total em `.TotalItens` | "N un. ou + por R$ X" → atacado; `.CardDescontoPreco` (PIX 3%) ignorado | dedupe por `PID`; só não perecíveis; `definir_cep` só confere login |
| `armazem` | armazemdamaria.com.br | Mercafacil (Next.js + styled-components; classes hash!) | loja na URL: `/loja-1` = Curitiba/PR (há Campinas/SP; sem POA) | HTML por estrutura: `href` `/produto/`, `title`, texto "R$" | `?page=N`, 30/pág, total "N resultados" | "-14%" + preço riscado; itens por peso mostram "/kg" (preço é por kg) | não usar classes `sc-*` |
| `rappi` | rappi.com.br/lojas/900637167-assaiatacadista-nc | Next.js + API web-gateway | loja na URL (Assaí Água Verde, Curitiba/PR); sem CEP | **JSON** (`__NEXT_DATA__` 24 iniciais + POST `dynamic/context/content/`, offset 6,12,18…, 204 = fim) | replay da request do "Ver mais" | `real_price`+`discount`; peso (`sale_type` WB/WP/WW) → `balance_price` por kg, qtd 1 kg | filtrar `store_id` da loja; dedupe `product_id`; retentativa em erro |
| `rappi_condor` | rappi.com.br/lojas/900685906-condor-supermer-alpormayor-nc | idem `rappi` | Condor, Curitiba/PR | idem | idem | idem | subclasse: só muda `nome_fornecedor`/`nome_loja`; tarefas derivadas de `TAREFAS_RAPPI` trocando a loja na URL |

## Estado atual do repositório (24/09/2026, branch `feature/rappi`, não commitado)
- `rappi`/`rappi_condor` + tarefas novas, edições em `armazem`/`atacadao` tarefas e `__init__.py` ainda **sem commit**.
- `data/produtos.py`: só `TAREFAS_RAPPI_CONDOR` ativa; demais comentadas (estado de trabalho, não é bug).
- `debug_inspecionar.py` (`DOMINIO_PARA_FORNECEDOR`) só tem `fort` ativo; `setup_sessao.py` (`SITES`) só `atacadao` ativo. Descomentar/adicionar o que for usar.
- Rappi/Armazém/Gimba **não** estão em `setup_sessao.py` (Gimba está comentado; precisa de login manual).

## Plataformas — o que reaproveitar
- **Osuper** (Asun, Fort): mesma plataforma, componentes diferentes; cards sem href → `ld+json`; modal de loja.
- **VTEX** (Atacadão): `data-testid` estáveis.
- **Next.js** (Rappi, Armazém): procurar `__NEXT_DATA__` e XHR JSON antes de olhar o HTML.
- **HTML server-side** (Gimba, XNEO): `requests`-like simples serviria, mas manter Playwright por padronização/sessão.
