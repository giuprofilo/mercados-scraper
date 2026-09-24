# atacado-scraper

Bot Python (Playwright sync + BeautifulSoup + SQLite + Google Sheets) que coleta preços de insumos em sites
de mercados. Código em `scraper/` (rodar sempre de dentro dessa pasta, com `venv/` ativo). Idioma: pt-BR.

**Antes de qualquer tarefa leia `docs/README.md`** (índice) e apenas os arquivos de `docs/` indicados para a tarefa.
Não leia o `README.md` da raiz (manual de instalação), nem `logs/`, `screenshots/`, `venv/`, `*.db`.

Regras essenciais:
- Nunca adivinhar seletores: usar HTML/JSON real (`python debug_inspecionar.py "<url>"` ou pedir ao usuário). "Mesma plataforma" ≠ mesmos seletores.
- Novo scraper = `scrapers/<x>.py` (herda `BaseScraper`) + registro em `scrapers/__init__.py` + `data/tarefas/<x>.py` + `data/produtos.py`. Não alterar `database.py`/`main.py`/`sheets_sync.py`/`base.py` por causa de um site. Passo a passo e checklist: `docs/04` e `docs/03`.
- O CEP/região é variável (usuário define quando precisar); alguns sites usam a loja na URL e ignoram CEP: `docs/07-cep-e-regiao.md`.
- Testar com `python main.py --sem-sheets --filtro <termo>`; nunca sincronizar o Sheets em teste.
- Não commitar, dar push nem abrir PR sem o usuário pedir. Branch `feature/<site>`, commits `feat(scraper): ...` em português. Nunca versionar `.env`, `credentials/`, `*.db`.
