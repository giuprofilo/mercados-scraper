# 03 — Requisitos de todo scraper (checklist obrigatório)

## Contrato
- [ ] Classe `<Nome>Scraper(BaseScraper)` em `scrapers/<nome>.py`, com `nome_fornecedor = "<nome>"` (minúsculo, sem espaço, igual à chave do registro).
- [ ] Implementa `definir_cep(self, cep: str) -> None` (pode só logar "nada a definir" — ver `07-cep-e-regiao.md`).
- [ ] Implementa `extrair_produtos_da_pagina(self, categoria, url, palavras_chave=None) -> list[Produto]`.
- [ ] **Nunca levanta exceção para fora**: `try/except Exception: logger.exception(...)` em volta da tarefa; retorna o que já coletou.
- [ ] Usa `self.page` (Playwright sync). **Não** criar browser/contexto próprio. **Não** abrir abas paralelas.
- [ ] Usa `config.NAV_TIMEOUT_MS` em `page.goto`.
- [ ] Logging via `logger = logging.getLogger(__name__)`, em pt-BR. Nunca `print`.

## Qualidade dos dados
- [ ] `preco` sempre float > 0; item sem preço/indisponível é **descartado** (contar e logar quantos).
- [ ] Preço parseado só com `utils.parsers.parse_preco` ("R$ 1.234,56" → 1234.56). Não reimplementar.
- [ ] `quantidade/unidade` via `extrair_quantidade_e_unidade(nome)`; `marca` via `extrair_marca(nome)`.
- [ ] **Item vendido por peso**: gravar o preço **por kg** com `quantidade=1, unidade="kg"` (ver Rappi `balance_price`, Armazém "/kg"). Nunca gravar preço de "bandeja aproximada" como se fosse por kg.
- [ ] Promoção: `preco_original` (cheio, riscado) só se > `preco`; `desconto = f"-{round((1 - preco/preco_original)*100)}%"`. Senão ambos `None`.
- [ ] Atacado ("a partir de N un. por R$ X"): `preco_atacado` + `qtd_minima_atacado`. Não confundir com preço riscado.
- [ ] Ignorar preços que não são o de prateleira (ex.: "preço no PIX" do Gimba, parcelado).
- [ ] `url_produto` absoluta (prefixar `BASE_URL` se relativa).
- [ ] **Dedupe** por id estável do site (PID/product_id/slug) — categorias/departamentos repetem produtos.
- [ ] Só incluir produtos da **loja/região da tarefa** (Rappi completa listas com produtos de outras lojas: filtrar por `store_id`).

## palavras_chave (filtro)
- Se `palavras_chave` vier, mantém só produtos cujo nome contém **alguma** palavra: `pk.lower() in nome.lower()` (substring, case-insensitive).
- **Nenhum scraper normaliza acentos** (só compara `.lower()`). Por isso as listas de tarefas trazem variantes com e sem acento (`"limão"`, `"limao"`). Ao criar tarefas, incluir as duas. (Alternativa futura: normalizar com `unicodedata` no filtro; não fazer sem pedido.)
- Filtrar **depois** de extrair e **antes** de tirar print (não gastar tempo com item descartado).

## Paginação / carregamento (escolher conforme o site; documentar na docstring)
| Padrão | Exemplo | Como |
|---|---|---|
| `?page=N` na URL | Atacadão, Armazém | montar URL com `urlsplit/parse_qsl/urlencode`; parar quando vazio/repetido; usar total "N resultados" |
| Botão "Mostrar/Ver mais" | Asun, Fort, Rappi | clicar até sumir, limitado por `config.MAX_PAGINAS_POR_CATEGORIA` ou `MAX_PAGINAS_SEGURANCA` |
| Scroll infinito | Stock | rolar até a contagem de cards parar de crescer |
| AJAX que troca grid | Gimba | chamar função JS do site e `wait_for_function` até o 1º nome mudar |
| API JSON | Rappi | capturar a request no 1º clique e repetir mudando `offset` até 204 |
- Sempre um **limite de segurança** de páginas/iterações (constante `MAX_PAGINAS_SEGURANCA`).
- Sempre ter condição de parada por "sem novos itens".

## Seletores
- Definir como constantes de classe `SEL_*` no topo da classe (fácil de achar/consertar).
- Preferir: dados estruturados (`__NEXT_DATA__`, `ld+json`, API) > `data-testid`/`data-cy` > estrutura estável (`href^="/produto/"`, `title`, texto "R$") > classes CSS. **Nunca** classes hash geradas (`sc-aaf59d57-1`).
- Cards sem `href` (Osuper: Asun/Fort): ler URLs do `<script type="application/ld+json">` (ItemList) e casar por ordem (`_mapear_urls_por_ordem`).

## Screenshots
- Só se `getattr(config, "SALVAR_PRINTS_ITENS", False)`. Salvar em `config.PRINTS_DIR` como `<fornecedor>_<id>_<nome_seguro>.png`; falha de print **não** pode descartar o produto (logar warning, `imagem_print=None`).

## Falha "vazia"
- Se cards encontrados mas 0 produtos extraídos (ou 0 cards), salvar `logs/debug_vazio_<categoria>.html` (padrão dos scrapers existentes) e logar erro.

## Docstring do módulo (obrigatória)
Topo do arquivo, bloco "Como o site funciona (confirmado contra o site real)": plataforma, onde vem a loja/região, formato do card/preço, paginação, peculiaridades (peso, atacado, login, dedupe). Atualizar quando descobrir algo novo.

## Definição de pronto
1. `python main.py --sem-sheets --filtro <termo>` retorna itens coerentes (preço plausível, unidade certa, sem duplicata, URL abre).
2. Nenhum traceback no log; contagem "N extraídos, M sem preço" logada.
3. Registrado em `scrapers/__init__.py`, tarefas em `data/tarefas/<x>.py`, ligado em `data/produtos.py`.
4. Linha do site adicionada em `docs/05-fornecedores.md`.
