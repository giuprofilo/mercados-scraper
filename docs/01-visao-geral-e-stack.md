# 01 — Visão geral e stack

## O que é
Bot de coleta de preços de insumos alimentícios em sites de supermercados/atacados. Para cada
**tarefa** (fornecedor + categoria + URL + palavras-chave) o bot abre o site com Playwright, extrai
produtos (nome, marca, preço, quantidade/unidade, preço atacado, promoção, URL, print), grava em
SQLite (histórico) e sobrescreve uma aba do Google Sheets com a última coleta.

Uso pessoal/interno de acompanhamento de preços. Rodar ~1x/dia, sem paralelismo (evitar bloqueio).

## Stack
| Item | Detalhe |
|---|---|
| Linguagem | Python 3 (venv em `venv/`, na raiz) |
| Navegador | Playwright 1.47 **sync API**, Chromium; `launch_persistent_context` (perfil em `credentials/perfil_atacadao/`) |
| Parsing HTML | BeautifulSoup4 (`html.parser`; `lxml` instalado) sobre `page.content()` |
| Banco | SQLite (`atacado_precos.db` na raiz), módulo `sqlite3` puro, sem ORM |
| Planilha | `gspread` 6.1 + `google-auth` (service account em `credentials/google_service_account.json`) |
| Config | `python-dotenv` (`.env` na raiz: `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_SHEETS_WORKSHEET_NAME`) |
| Dependências | `requirements.txt` (6 libs, versões fixas). Não adicionar libs sem necessidade |
| Agendamento | cron / Agendador de Tarefas do Windows (manual, fora do código) |
| Testes | **não há suíte automatizada.** Validação = rodar `main.py --sem-sheets` + conferir `logs/` |

## Comandos (rodar de dentro de `scraper/`, com venv ativo)
```bash
python main.py --sem-sheets                 # coleta + SQLite, sem Sheets (usar em testes)
python main.py --sem-sheets --filtro arroz  # + relatório filtrado no terminal
python main.py --so-relatorio               # só relatório do banco, sem coletar
python main.py                              # coleta + SQLite + Sheets (produção)
python setup_sessao.py                      # abre navegador visível p/ salvar CEP/login (1x por site)
python debug_inspecionar.py "<url>"         # salva logs/debug_pagina.html + screenshot; mostra nº de cards
```
Imports são relativos à pasta `scraper/` (`import config`, `from database import ...`), então **sempre
executar de dentro de `scraper/`**.

## Pastas geradas (git-ignored)
`logs/` (debug_vazio_<categoria>.html quando uma tarefa vem vazia), `screenshots/` (print por produto),
`credentials/`, `atacado_precos.db`, `exports/*.csv`.

## Idioma
Código, docstrings, logs, commits e docs em **português (pt-BR)**. Identificadores em português
(`extrair_produtos_da_pagina`, `preco_atacado`). Manter.
