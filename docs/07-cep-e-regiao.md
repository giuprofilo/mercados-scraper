# 07 — CEP, região e loja

**Requisito do usuário: a região NÃO é fixa; o CEP deve poder ser definido sempre que necessário.**

## Como o CEP entra hoje
- Valor único em `scraper/config.py`: `CEP = "90560-005"` (Porto Alegre — apenas o valor padrão atual).
- `main.py` passa `cep=config.CEP` → `executar_coletas(...)` → `scraper.definir_cep(cep)` **uma vez por fornecedor por execução** (antes da 1ª tarefa dele).
- Para mudar de região: editar `config.CEP` **e** refazer a sessão dos sites que usam CEP (abaixo). Se for adicionado suporte a CLI/`.env` (ex.: `--cep` / `CEP=` no `.env`, lido em `config.py` com `os.environ.get("CEP", "90560-005")`), documentar aqui. *(Ainda não existe — implementar só se o usuário pedir.)*

## Três modelos de região (cada scraper declara qual usa na docstring e em `definir_cep`)
| Modelo | Sites | `definir_cep` | Para mudar a região |
|---|---|---|---|
| **CEP em modal** (sessão salva no perfil) | atacadao, stock, asun, fort | preenche CEP/escolhe loja; **pula** se `credentials/perfil_atacadao/` já tem conteúdo | apagar/refazer perfil: `python setup_sessao.py` e configurar o CEP novo manualmente (ou apagar `credentials/perfil_atacadao/`) |
| **Loja na URL** | armazem (`/loja-N`), rappi/rappi_condor (`/lojas/<id>-<tipo>`) | só loga "nada a definir"; **ignora o CEP** | trocar a base da URL nas tarefas (`_B`) pelo id da loja da nova região; **o `config.CEP` não tem efeito** |
| **Conta/sem região** | gimba (preço por conta CNPJ, login manual), sites de preço único | confere sessão/login ou vazio | relogar via `setup_sessao.py` |

## Regras ao criar/alterar
- Sempre descobrir **qual modelo** o site usa antes de escrever `definir_cep` (procurar no site: pede CEP? a URL muda com a loja? exige login?).
- Não automatizar CEP em site com anti-bot: configurar 1x manualmente (`setup_sessao.py`) e reaproveitar o perfil persistente (cookies + localStorage + sessionStorage). Login com código por e-mail não é automatizável.
- **Conferir a loja escolhida** (sites às vezes caem numa loja padrão de outra cidade por geolocalização) — logar o nome da loja/cidade detectada quando o site mostrar.
- Ao trocar de região, os dados no SQLite continuam misturados (a tabela não tem coluna de região/CEP). Se o usuário precisar separar coletas por região, isso exige decisão de schema (`database.py` + `sheets_sync._CAMPOS_PRODUTO`) — **perguntar antes**. Enquanto isso, registrar a região na `categoria` da tarefa ou na aba do Sheets (`GOOGLE_SHEETS_WORKSHEET_NAME`, ex.: `Coleta Curitiba`).
- Lojas conhecidas: Armazém `/loja-1` = Curitiba/PR (sem loja em POA); Rappi Assaí Água Verde = `900637167-assaiatacadista-nc`, Condor = `900685906-condor-supermer-alpormayor-nc` (ambas Curitiba/PR; CEP de referência usado no levantamento: 80730-420). Para outra cidade: descobrir os ids das lojas da região no site.
