# 04 — Como adaptar (criar ou consertar) um scraper

Regra central: **descobrir o mecanismo real do site antes de escrever código.** Ordem de preferência
para obter os dados (do mais estável ao mais frágil): JSON embutido/API → ld+json → atributos
`data-*`/estrutura → classes CSS.

## Criar um scraper novo — passo a passo

### 1. Reconhecimento (antes de qualquer código)
Coletar, para 1 URL de categoria com produtos (e 1 com promoção, se possível):
- **Plataforma** (VTEX, Osuper, VIP, Mercafacil, Next.js, ASP.NET, XNEO...) — ver `05-fornecedores.md` para reaproveitar conhecimento.
- **Onde está a região/loja**: CEP em modal? loja na URL? conta/login (CNPJ)? preço único? (→ `07-cep-e-regiao.md`)
- **Fonte dos dados**: o HTML já traz os produtos (server-side) ou vem por JS/API? Existe `__NEXT_DATA__`, `ld+json`, chamada XHR JSON? (aba Network / `page.on("request")`).
- **Card**: seletor do card, nome, preço atual, preço riscado, badge de desconto, preço atacado, unidade ("/kg"), link, id estável.
- **Indisponível**: como aparece (sem "R$", texto "Indisponível").
- **Paginação**: tipo (tabela em `03-requisitos-dos-scrapers.md`), itens por página, onde está o total.
- **Anti-bot / login**: se houver, não automatizar; usar `setup_sessao.py` (sessão manual salva no perfil).

Como obter o HTML/JSON real:
```bash
cd scraper && python debug_inspecionar.py "<url>"   # gera logs/debug_pagina.html e logs/debug_screenshot.png
```
(precisa de linha do domínio em `DOMINIO_PARA_FORNECEDOR` no topo de `debug_inspecionar.py` para mostrar a contagem de cards; sem isso ainda salva o HTML.)
Se o site bloqueia o bot, pedir ao usuário o HTML/JSON/HAR. Para economizar tokens: **não ler o HTML inteiro** —
`grep -o`/BeautifulSoup em script para extrair só 1–2 cards e o trecho de paginação.

### 2. Criar `scrapers/<nome>.py`
Esqueleto (copiar de `gimba.py` p/ HTML server-side + paginação AJAX, `armazem.py` p/ `?page=N`,
`rappi.py` p/ JSON/API; `fort.py`/`asun.py` p/ Osuper; `atacadao.py` p/ VTEX):
```python
"""Scraper para <Site> (<dominio>). Plataforma: <x>.
Como o site funciona (confirmado contra o site real):
- região/loja: ...
- card/preço: ...
- paginação: ...
- peculiaridades: ...
"""
import logging
from typing import Optional
from bs4 import BeautifulSoup

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import parse_preco, extrair_quantidade_e_unidade, extrair_marca

logger = logging.getLogger(__name__)
BASE_URL = "https://www.<dominio>"
MAX_PAGINAS_SEGURANCA = 100


class NomeScraper(BaseScraper):
    nome_fornecedor = "nome"

    SEL_CARD_PRODUTO = "..."
    SEL_NOME_PRODUTO = "..."
    SEL_PRECO = "..."

    def definir_cep(self, cep: str) -> None:
        logger.info("<Site>: a loja vem na URL — nada a definir.")   # ou fluxo de CEP

    def _extrair_card(self, card, categoria: str) -> Optional[Produto]:
        ...  # devolve None se sem nome/preço

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        produtos, vistos = [], set()
        try:
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS)
            self.page.wait_for_selector(self.SEL_CARD_PRODUTO, timeout=15000)
            # loop de paginação com limite de segurança
            soup = BeautifulSoup(self.page.content(), "html.parser")
            for card in soup.select(self.SEL_CARD_PRODUTO):
                ...  # dedupe -> _extrair_card -> filtro palavras_chave -> append
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (<Site>)", categoria)
        return produtos
```
Se `definir_cep` precisar de CEP: copiar o fluxo de `fort.py`/`asun.py` (pular se perfil persistente já existe:
`config.USAR_SESSAO_SALVA and os.path.isdir(config.PERFIL_NAVEGADOR_DIR) and os.listdir(...)`).

### 3. Registrar (edições de 1–3 linhas cada)
| Arquivo | O que |
|---|---|
| `scrapers/__init__.py` | `from scrapers.<nome> import <Nome>Scraper` + `"<nome>": <Nome>Scraper` em `SCRAPERS_DISPONIVEIS` |
| `data/tarefas/<nome>.py` | `TAREFAS_<NOME> = [...]` (ver `06-tarefas-de-coleta.md`) |
| `data/produtos.py` | `from data.tarefas.<nome> import TAREFAS_<NOME>` + `*TAREFAS_<NOME>,` em `TAREFAS_DE_COLETA` |
| `debug_inspecionar.py` | linha em `DOMINIO_PARA_FORNECEDOR` |
| `setup_sessao.py` | linha em `SITES` **só se** o site precisa de CEP/login manual |
| `docs/05-fornecedores.md` | linha do site |

### 4. Validar
```bash
cd scraper
python main.py --sem-sheets --filtro <termo>
```
Conferir (checklist "Definição de pronto" em `03-requisitos-dos-scrapers.md`): preços plausíveis, unidade
e "por kg" corretos, sem duplicatas, promoções com `preco_original`, URLs abrem, log sem traceback.
Para testar só o novo fornecedor, deixar ativa **apenas** a linha dele em `data/produtos.py`
(as demais comentadas — é o estado normal do arquivo).

## Consertar scraper que parou (0 cards / 0 produtos)
1. Olhar `logs/debug_vazio_<categoria>.html` (gerado automaticamente) ou rodar `debug_inspecionar.py <url>`.
2. Diagnosticar: **0 cards** → `SEL_CARD_PRODUTO` mudou, ou página bloqueou/pediu CEP/login (ver screenshot), ou conteúdo carrega tarde (aumentar espera por seletor). **Cards mas 0 produtos** → seletor de nome/preço mudou, ou tudo indisponível.
3. Corrigir só as constantes `SEL_*`/a função `_extrair_card`; registrar na docstring o que mudou e a data.
4. Se a loja errada/CEP voltou a ser pedido → `python setup_sessao.py` (ver `07-cep-e-regiao.md`).
5. Reexecutar com `--sem-sheets --filtro`.

## Site fora do ramo de mercado
A arquitetura serve para qualquer grid nome+preço; mesmo processo. Sites server-side (ex.: XNEO) não precisam de
CEP (`definir_cep` vazio) e podem ter vários preços na mesma linha (PIX x parcelado) — escolher o comparável
(à vista/PIX) e documentar na docstring.

## Armadilhas já vividas (não repetir)
- Copiar seletores de site "parecido" → 0 produtos (Fort x Asun). Sempre validar com HTML real.
- Cards sem `href` (Osuper) → URL vem do `ld+json`.
- Preço por peso gravado como preço da unidade (Rappi/Armazém) → usar preço/kg.
- Listas com produtos de outras lojas (Rappi) → filtrar por `store_id`.
- Paginação cortada em silêncio por limite de requisições (Rappi) → retentativa + só parar em 204/fim real.
- Login por código no e-mail (Gimba) → impossível automatizar; sessão manual via `setup_sessao.py`.
- Departamentos que agrupam itens de outros (Gimba: cafe/snacks/natal) → dedupe por id.
