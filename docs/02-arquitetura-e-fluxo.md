# 02 — Arquitetura e fluxo

## Mapa de arquivos (`scraper/`)
```
config.py              CEP, timeouts, HEADLESS, perfil, Sheets, prints, MAX_PAGINAS_POR_CATEGORIA
database.py            dataclass Produto + SQLite (init_db, inserir_produto, listar_por_nome, filtrar_...)
scraper.py             executar_coletas(): abre Playwright, itera tarefas, instancia scrapers
main.py                CLI (argparse): coleta -> SQLite -> Sheets -> relatórios
sheets_sync.py         sincronizar_produtos(lista) [padrão, delega a planilha_fgv] / sincronizar_planilha() [histórico do banco]
planilha_fgv.py        formato da planilha FNDE Nordeste (aba Coleta, 20 colunas): vínculo produto->insumo, empresa, pesquisador; exportar_csv()
setup_sessao.py        dict SITES: abre cada site visível p/ salvar CEP/loja/login no perfil
debug_inspecionar.py   dict DOMINIO_PARA_FORNECEDOR: salva HTML renderizado + conta cards
scrapers/base.py       BaseScraper (ABC): definir_cep(cep), extrair_produtos_da_pagina(categoria,url,palavras_chave)
scrapers/__init__.py   SCRAPERS_DISPONIVEIS = {"chave": Classe}  <- registro
scrapers/<site>.py     um por site
data/produtos.py       TAREFAS_DE_COLETA: quais listas de tarefas estão ativas (comentar = desativar)
data/tarefas/<x>.py    TAREFAS_<X> = [ {fornecedor, categoria, url, palavras_chave}, ... ]
data/alimentos.py      LISTA_ALIMENTOS_PADRAO: referência do que monitorar (base p/ palavras_chave)
data/marcas.py         MARCAS_CONHECIDAS: extrair_marca() faz match por substring no nome
utils/parsers.py       parse_preco, extrair_quantidade_e_unidade, extrair_marca, calcular_preco_por_unidade
```

## Fluxo de execução
1. `main.py` → `database.init_db()` → `executar_coletas(TAREFAS_DE_COLETA, cep=config.CEP)`.
2. `scraper.py` abre **um único** contexto persistente (compartilhado por todos os sites) e uma única `page`.
3. Para cada tarefa: `SCRAPERS_DISPONIVEIS[tarefa["fornecedor"]](page)`; na **1ª tarefa de cada fornecedor**
   chama `definir_cep(cep)`; depois `extrair_produtos_da_pagina(categoria, url, palavras_chave)`.
4. Exceções são capturadas por tarefa (uma falha não derruba as demais). Scraper deve capturar as próprias
   exceções, logar e devolver o que já coletou.
5. `main.py` só insere no SQLite (**sempre INSERT**, acumula histórico) se `config.SALVAR_NO_BANCO` (padrão `False`) ou `--salvar-banco`; chama
   `sheets_sync.sincronizar_produtos(produtos)` (grava numa aba **própria** da coleta, limpa e reescrita a cada execução).
6. Relatórios no terminal (`listar_por_nome`, `--filtro`); com o banco desligado, `--filtro` filtra a coleta em memória. Coleta só para o Sheets, sem banco: `python main.py`.

## Modelo `Produto` (`database.py`) — contrato de saída de todo scraper
| Campo | Tipo | Regra |
|---|---|---|
| `fornecedor` | str | = `nome_fornecedor` do scraper (= chave em `SCRAPERS_DISPONIVEIS`) |
| `categoria` | str | vem da tarefa (nome livre) |
| `nome` | str | nome como no site |
| `marca` | str\|None | `extrair_marca(nome)` |
| `preco` | float | **obrigatório** (>0). Sem preço/indisponível => descartar o item, não gravar |
| `quantidade`, `unidade` | float\|None, str\|None | `extrair_quantidade_e_unidade(nome)`; unidades padronizadas: kg,g,L,ml,un,cx,pct,dz |
| `preco_original` | float\|None | preço "cheio" riscado (só em promoção; deve ser > `preco`) |
| `desconto` | str\|None | formato `"-34%"` |
| `preco_atacado` + `qtd_minima_atacado` | float\|None, int\|None | preço por qtd mínima (ex.: "12 un. ou + por R$ 2,99") — **distinto** de `preco_original` |
| `url_produto` | str\|None | URL absoluta da página do produto |
| `imagem_print` | str\|None | caminho do PNG; só se `config.SALVAR_PRINTS_ITENS` |
| `coletado_em` | str | automático (ISO, segundos) |

Adicionar campo novo exige mexer em `database.py` (+ migração `ALTER TABLE`) **e** `sheets_sync._CAMPOS_PRODUTO`
— evitar; só com pedido explícito.

## Sheets (planilha "Pesquisa FNDE Nordeste - Alimentos") — `planilha_fgv.py`
Exemplos dos três layouts exportados em `csv/Pesquisa FNDE Nordeste - Alimentos(Empresas|Insumos|Coleta).csv`
(CSV `;`, cp1252). O layout Centro-Oeste anterior foi substituído.
- Abas originais (Coleta, Insumos, Empresas, Pesquisadores, Leia-me, Acompanhamento) **nunca são escritas**;
  `GOOGLE_SHEETS_WORKSHEET_NAME` com esses nomes (ou vazio) é recusado. Trocar o nome a cada coleta (aba nova).
- `.env`: `GOOGLE_SHEETS_WORKSHEET_NAME` (aba da coleta), `EMPRESA_COLETA` (nome/parte na aba Empresas, uma por vez;
  ex.: `Mateus Supermercados`), `PESQUISADOR` (obrigatório se não houver aba Pesquisadores), `OBS_FRETE` (opcional).
- Empresas: `Código Empresa, Nome Empresa, CNPJ, UF Empresa` (sem coluna de busca). Insumos: `ID FGV, Categoria,
  Grupo de Insumo, Descrição, Embalagem, Observações, Busca (dropdown)`.
- Saída = 20 colunas da aba Coleta (`COLUNAS_SAIDA`), valores sem cabeçalho: Nome Empresa, CNPJ, UF Empresa, Buscar Insumo,
  Código FGV, Categoria, Grupo de Insumo, Descrição do insumo, UF Preço, Data coleta (dd/mm/aa), Pesquisador, FONTE (=url),
  PRODUTO PESQUISADO (nome; embalagem ≠ 1 kg/1 L ganha " | Unidade do item: 1 KG"/"1 l"), Preço PRODUTO (cheio ou atual),
  Desconto % (vazio), Desconto R$ (cheio/lista − final), OBS Desconto (promoção / "preço de atacado a partir de N unid.: R$ x"),
  PREÇO FINAL (atacado, se houver, senão o atual), VALOR FRETE (vazio), OBS FRETE (`OBS_FRETE` ou "retirada na loja do
  próprio estado: frete não se aplica").
- Produto -> insumo: 1º pelo ID FGV na `categoria` da tarefa (`"FRUTA ## 39"`, mesmo formato do dropdown); sem ID,
  palavras da Descrição do insumo contra o nome do produto (1ª palavra obrigatória, mais palavras em comum ganha). Sem
  insumo/empate: a linha vai com insumo em branco + aviso no log. **Nada é descartado.**
- Limite de 5 linhas por insumo (`MAX_PRECOS_POR_INSUMO`): ficam as de maior peso (empate = mais barata), mesmo produto
  (URL) repetido conta uma vez, saída ordenada por insumo e do menor para o maior preço.
- Busca no site é só pelo termo curto das tarefas; a planilha recebe a Descrição completa.
- **Conferir sem Sheets**: `python main.py --sem-sheets --exportar-csv` grava `exports/coleta_<empresa>_<data>.csv` no
  mesmo layout, lendo Insumos/Empresas de `csv/` (precisa de `EMPRESA_COLETA` e `PESQUISADOR`).
- `sincronizar_planilha()` (histórico do banco) continua com o formato antigo, mas também exige aba com nome válido.

## config.py — valores atuais relevantes
`CEP="90560-005"`, `HEADLESS=True`, `NAV_TIMEOUT_MS=45000`, `USAR_SESSAO_SALVA=True`,
`MAX_PAGINAS_POR_CATEGORIA=5` (usado por atacadao/asun/fort), `SALVAR_PRINTS_ITENS=True`.
