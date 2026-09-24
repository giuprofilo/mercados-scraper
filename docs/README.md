# docs/ — índice (leia só o que a tarefa precisa)

Objetivo: dar contexto exato ao Claude sem reler o código todo. Cada arquivo
é curto e autossuficiente. **Não releia `README.md` da raiz** (é manual de
instalação para humanos); o que importa para desenvolvimento está aqui.

| Tarefa | Leia |
|---|---|
| Qualquer tarefa (primeiro) | `01-visao-geral-e-stack.md` |
| Criar/adaptar um scraper novo | `04-como-adaptar-scraper.md` + `03-requisitos-dos-scrapers.md` |
| Consertar scraper que parou (0 produtos) | `04-como-adaptar-scraper.md` (seção "Consertar") + a linha do site em `05-fornecedores.md` |
| Criar/editar tarefas de coleta (`data/tarefas/*.py`) | `06-tarefas-de-coleta.md` |
| Mudar CEP / região / loja | `07-cep-e-regiao.md` |
| Mexer em banco, Sheets, main, config | `02-arquitetura-e-fluxo.md` |
| Commit, branch, PR, estilo de código | `08-convencoes.md` |

## Regras de ouro (resumo de tudo)

1. **Nunca adivinhe seletor.** Veja HTML/JSON real do site antes de escrever código. "Mesma plataforma" ≠ "mesmos seletores" (Asun x Fort).
2. Preferir **JSON/API/ld+json** do site a seletores CSS quando existir (mais estável). Classes hash (styled-components) não servem.
3. Um scraper novo toca **no máximo 5 arquivos**: `scrapers/<x>.py`, `scrapers/__init__.py`, `data/tarefas/<x>.py`, `data/produtos.py`, e opcionalmente `debug_inspecionar.py`/`setup_sessao.py`. **Nunca** mudar `database.py`, `main.py`, `sheets_sync.py`, `base.py` para acomodar um site.
4. Testar sempre com `python main.py --sem-sheets --filtro <termo>` (nunca sincronizar Sheets em teste).
5. Não commitar/abrir PR sem o usuário pedir. Nunca commitar `.env`, `credentials/`, `*.db`, `logs/`, `screenshots/`.
6. Docstring do topo do scraper registra **como o site funciona** (confirmado contra o site real) — é a memória do projeto; mantenha atualizada.
