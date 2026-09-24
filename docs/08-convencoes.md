# 08 — Convenções (Git, código, segurança)

## Git (padrão observado no histórico)
- Uma branch por site/feature: `feature/<site>` (ex.: `feature/gimba`, `feature/armazemdamaria`, `feature/rappi`), PR para `main` (`Merge pull request #N from giuprofilo/feature/...`).
- Commits em português, Conventional Commits com escopo: `feat(scraper): adiciona scraper do armazemdamaria`, `feat(scraper): ajusta itens de coleta do atacadao`. Usar `fix(scraper):` para conserto, `docs:` para documentação, `refactor(...)`.
- **Só commitar / abrir PR / dar push quando o usuário pedir.** Nunca `--force`, nunca commitar em `main`.
- Nunca versionar: `.env`, `credentials/`, `*.db`, `logs/`, `screenshots/`, `venv/`, `exports/*.csv` (já no `.gitignore`).
- Antes de commitar: `git status` e conferir que só entram arquivos do escopo (mudanças alheias, como renomear `__FRUTAS`, vão em commit separado ou avisar).

## Estilo de código
- Formatação estilo **black** (aspas duplas, 88 col.). Type hints modernos (`Optional[...]`, `list[str]`).
- Comentários só para o **porquê** não óbvio; a explicação de como o site funciona vai na docstring do módulo.
- Constantes `SEL_*` na classe; constantes de módulo em MAIÚSCULAS (`BASE_URL`, `ITENS_POR_PAGINA`, `MAX_PAGINAS_SEGURANCA`); helpers privados `_nome`.
- Reaproveitar `utils/parsers.py`; não duplicar parsing de preço/quantidade/marca.
- Manter mudanças mínimas e localizadas: não refatorar scrapers vizinhos ao criar um novo.
- Adicionar marcas novas em `data/marcas.py` (`MARCAS_CONHECIDAS`, match por substring — cuidado com marcas curtas que geram falso positivo).

## Segurança / boas maneiras
- Segredos só em `.env`/`credentials/`; nunca imprimir ou commitar (nem o ID da planilha).
- Coleta educada: ~1x/dia, uma aba, sem paralelismo, limites de página, pausas curtas (`wait_for_timeout`) quando o site limitar requisições.
- Testes sempre com `--sem-sheets` (a planilha é sobrescrita inteira a cada sync).

## Economia de tokens ao trabalhar neste repo
- Ler `docs/README.md` e só os arquivos indicados; **não** ler o `README.md` raiz, `venv/`, `logs/`, `screenshots/`, `*.db`.
- Ler só a docstring (`sed -n 1,50p`) do scraper do site em questão, e um scraper "modelo" da mesma plataforma, não todos.
- HTML de debug é grande: extrair com `grep`/script apenas 1–2 cards + trecho de paginação; não fazer `Read` do arquivo inteiro.
- Listas de tarefas são longas e repetitivas: editar por `Edit` localizado, sem reler o arquivo todo.
- Não há testes automatizados: validar rodando `main.py --sem-sheets` com um único fornecedor ativo e `--filtro`.
