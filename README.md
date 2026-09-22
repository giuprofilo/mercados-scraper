# Bot de Coleta de Preços — Atacado (Porto Alegre)

Script que visita sites de mercados atacadistas, coleta preço, nome,
marca, quantidade e um print de cada produto, guarda tudo em um banco
SQLite local (histórico) e sincroniza automaticamente com uma planilha
do Google Sheets. Feito para pesquisa de preços de insumos, mas serve
pra qualquer coleta parecida.

---

## Estrutura do projeto

```
atacado-scraper/                  <- raiz do projeto (onde fica o .git)
├── .env                          <- seus dados sensíveis (não versionado)
├── .env.example                  <- molde do .env (esse SIM vai pro git)
├── .gitignore
├── README.md
├── requirements.txt
├── atacado_precos.db             <- criado sozinho na 1ª coleta
│
├── credentials/                  <- NUNCA vai pro git
│   ├── google_service_account.json   (chave do Google Sheets)
│   └── perfil_atacadao/              (sessão salva: CEP/loja de cada site)
│
├── logs/                         <- criado sozinho quando algo dá 0 resultado
│   ├── debug_pagina.html             (do debug_inspecionar.py)
│   ├── debug_screenshot.png          (do debug_inspecionar.py)
│   └── debug_vazio_<categoria>.html  (quando uma tarefa de coleta vem vazia)
│
├── screenshots/                  <- print de cada produto coletado
│
└── scraper/                      <- todo o código
    ├── config.py                     configurações gerais (CEP, timeouts, etc.)
    ├── database.py                   SQLite: schema + funções de consulta
    ├── scraper.py                    orquestra o Playwright + os scrapers
    ├── sheets_sync.py                envia o banco pro Google Sheets
    ├── main.py                       ponto de entrada (é esse que você roda)
    ├── setup_sessao.py               roda 1x: salva CEP/loja de cada site
    ├── debug_inspecionar.py          ferramenta de debug de seletores
    │
    ├── data/
    │   ├── produtos.py               <- SUAS TAREFAS DE COLETA (o que/onde coletar)
    │   └── marcas.py                 lista de marcas conhecidas (pra identificar a marca no nome do produto)
    │
    ├── scrapers/
    │   ├── __init__.py                registro de todos os scrapers disponíveis
    │   ├── base.py                    classe base que todo scraper precisa seguir
    │   ├── atacadao.py, stock.py, asun.py, fort.py   um arquivo por site
    │
    └── utils/
        └── parsers.py                 funções de apoio: extrair preço, marca e
                                        quantidade/unidade (ex: "1kg", "500g") a
                                        partir do texto bruto do site
```

---

## 1. Instalação — Linux / macOS

```bash
# 1. Python, pip e venv
sudo apt update && sudo apt install -y python3 python3-pip python3-venv   # Ubuntu/Debian
# no macOS, use o Homebrew: brew install python3

# 2. Ambiente virtual
cd atacado-scraper
python3 -m venv venv
source venv/bin/activate          # o terminal passa a mostrar "(venv)" no início

# 3. Dependências Python
pip install --upgrade pip
pip install -r requirements.txt

# 4. Navegador do Playwright (+ libs de sistema que faltam no Linux)
playwright install --with-deps chromium
```

> Se `--with-deps` pedir senha de admin e falhar, rode
> `sudo playwright install-deps chromium` separado.

Pra rodar de novo no futuro, só reative o venv:
```bash
cd atacado-scraper/scraper && source ../venv/bin/activate
```

## 1-Windows. Instalação — Windows

O código Python já funciona em Windows sem nenhuma alteração (usa
`os.path.join` em todo lugar, não tem nada específico de Linux). O que
muda são só os comandos de terminal:

```powershell
# 1. Instale o Python (python.org/downloads) marcando a opção
#    "Add python.exe to PATH" durante a instalação.

# 2. Ambiente virtual (PowerShell)
cd atacado-scraper
python -m venv venv
venv\Scripts\Activate.ps1
# se der erro de "execução de scripts desabilitada", rode antes (1x só):
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Dependências Python
pip install --upgrade pip
pip install -r requirements.txt

# 4. Navegador do Playwright — sem "--with-deps" (essa flag só existe
#    pra instalar libs de sistema do Linux via apt; no Windows não
#    precisa)
playwright install chromium
```

Diferenças a ter em mente no resto deste README:
- Onde está escrito `python3`, use `python`.
- Onde está escrito `source venv/bin/activate`, use `venv\Scripts\Activate.ps1` (PowerShell) ou `venv\Scripts\activate.bat` (Prompt de Comando).
- A seção 10 (agendar execução diária) usa `cron`, que não existe no Windows — o equivalente é o **Agendador de Tarefas** (Task Scheduler); veja o final daquela seção.

---

## 2. Conectando com a planilha do Google Sheets

O ID da planilha fica em um arquivo **`.env`** (não vai pro git — assim
ninguém além de você consegue abrir sua planilha só de olhar o código).

### 2.1. Criando a credencial gratuita do Google

1. Acesse **console.cloud.google.com** e crie um projeto novo.
2. **APIs e Serviços → Biblioteca**: ative **Google Sheets API** e
   **Google Drive API**.
3. **APIs e Serviços → Credenciais → Criar Credenciais → Conta de
   serviço**. Dê um nome, crie.
4. Na conta de serviço criada → aba **Chaves → Adicionar chave → Criar
   nova chave → JSON**. Baixa um arquivo — renomeie pra
   `google_service_account.json` e coloque em `credentials/`.
5. Abra esse JSON, copie o valor de `"client_email"`.
6. Crie uma planilha nova (sheets.new) e **compartilhe** com esse
   e-mail, permissão de **Editor**.
7. Copie o **ID da planilha** — o trecho da URL entre `/d/` e `/edit`:
   ```
   https://docs.google.com/spreadsheets/d/1AbCDefG_ESSE_PEDACO_hIJkLmN/edit
   ```

### 2.2. Preenchendo o `.env`

Na raiz do projeto, copie o molde e preencha:
```bash
cp .env.example .env
```
Abra o `.env` e cole o ID que você copiou:
```
GOOGLE_SHEETS_SPREADSHEET_ID=1AbCDefG_ESSE_PEDACO_hIJkLmN
GOOGLE_SHEETS_WORKSHEET_NAME=Coleta
```
`GOOGLE_SHEETS_WORKSHEET_NAME` é o nome da aba dentro da planilha —
pode trocar quando quiser (ex: `Fort 17-09`), sem precisar editar código.

Se esquecer de preencher o `.env`, o `main.py` avisa isso claramente no
log em vez de dar um erro confuso do Google.

---

## 3. Configurando a sessão (CEP/loja) — 1x por site

Sites de mercado precisam saber qual CEP/loja usar pra mostrar o preço
certo (o mesmo produto custa diferente em lojas diferentes). Em vez de
automatizar isso (o que costuma disparar proteção anti-bot), configuramos
**manualmente 1 vez** e o Playwright salva a sessão (cookies +
localStorage + sessionStorage) pra reaproveitar sempre.

```bash
cd scraper
python setup_sessao.py
```

Isso abre o navegador de verdade, um site de cada vez, na lista `SITES`
que fica no **topo do arquivo `setup_sessao.py`**:

```python
SITES = {
    "stock": "https://www.stokonline.com.br/",
    "atacadao": "https://www.atacadao.com.br/",
    "asun": "https://www.asunonline.com.br/",
    "fort": "https://www.fortatacadista.com.br/",
}
```

**É aqui que você comenta/descomenta ou troca a URL** de qual site quer
(re)configurar a sessão. Em cada janela: digite o CEP, confirme que é a
loja certa (alguns sites já vêm com uma loja errada por padrão, tipo
outra cidade — CONFIRA sempre), navegue até uma categoria pra ver se
aparecem produtos com preço, e aperte ENTER no terminal pra ir pro
próximo site.

A sessão fica salva em `credentials/perfil_atacadao/` e é reaproveitada
por todos os scrapers automaticamente. Se um dia o site voltar a pedir
CEP durante a coleta normal, é só rodar esse script de novo.

---

## 4. Rodando os scrapers

```bash
cd scraper
python main.py                    # coleta tudo + salva no banco + sincroniza Sheets
python main.py --sem-sheets       # só coleta e salva no SQLite, sem tocar no Sheets
python main.py --so-relatorio     # não coleta nada, só mostra relatórios do banco atual
python main.py --filtro "arroz"   # mostra também um relatório filtrado por "arroz"
```

Use `--sem-sheets` sempre que estiver testando/ajustando alguma coisa —
só tire o `--sem-sheets` quando já tiver validado que os dados saíram
certos.

**Onde escolher qual fornecedor/categoria/URL vai ser coletado:**
`scraper/data/produtos.py`, na lista `TAREFAS_DE_COLETA`. Cada bloco é
uma tarefa:

```python
{
    "fornecedor": "fort",                # tem que bater com uma chave de scrapers/__init__.py
    "categoria": "Mercearia",            # nome livre, só pra organizar o relatório
    "url": "https://www.fortatacadista.com.br/categorias/mercearia/acucares-e-adocantes",
    "palavras_chave": ["refinado"],      # opcional: filtra só produtos cujo nome contém alguma dessas palavras
},
```

Pra desligar uma tarefa sem apagar, comente o bloco inteiro com `#`
(o arquivo já tem vários exemplos assim). Pra rodar só um fornecedor,
comente todos os blocos dos outros.

---

## 5. Ligando/desligando o print de cada produto

Em `scraper/config.py`:
```python
SALVAR_PRINTS_ITENS = True     # True liga, False desliga
PRINTS_DIR = os.path.join(BASE_DIR, "screenshots")   # onde os prints são salvos
```
Com `False`, a coleta fica mais rápida (não precisa rolar até cada card
e tirar print), mas você perde a conferência visual de cada produto.

---

## 6. Como fazer o debug pra achar os seletores (e mandar pra uma IA)

Sites de e-commerce mudam o HTML com frequência, e cada plataforma usa
nomes de classe diferentes — então o primeiro passo ao adicionar (ou
consertar) um scraper NUNCA é adivinhar, é olhar o HTML de verdade.

```bash
cd scraper
python debug_inspecionar.py "https://www.fortatacadista.com.br/categorias/mercearia/acucares-e-adocantes"
```

O script:
1. Reconhece o site pelo domínio da URL (usando o dicionário
   `DOMINIO_PARA_FORNECEDOR` no topo do próprio arquivo — adicione uma
   linha ali quando cadastrar um fornecedor novo) e mostra no terminal
   quantos cards o `SEL_CARD_PRODUTO` daquele scraper encontrou.
2. Salva `logs/debug_pagina.html` (o HTML **renderizado de verdade**,
   depois do JavaScript carregar os produtos) e `logs/debug_screenshot.png`.

**Se o problema não ficar óbvio olhando você mesmo**, é só anexar o
`logs/debug_pagina.html` (e o screenshot, se ajudar) numa conversa com
uma IA (Claude, por exemplo) e pedir pra ela achar os seletores certos
de nome/preço/desconto — foi assim que Asun e Fort foram mapeados. Duas
dicas práticas que fizeram diferença nesse processo:
- **Mande o HTML de uma categoria que tenha produto em oferta ativa** se
  o que você quer confirmar é desconto/preço riscado — uma categoria sem
  nenhuma promoção não mostra essa parte do HTML.
- **"Mesma plataforma" não garante "mesmos seletores"**: Asun e Fort
  rodam na mesma plataforma (Osuper), mas usam nomes de classe
  diferentes entre si. Sempre confirme com HTML real, mesmo copiando de
  um scraper parecido.

Depois de ajustar, teste rápido com `python main.py --sem-sheets --filtro <algo>`
antes de rodar a coleta inteira.

---

## 7. Fornecedores já mapeados (resumo)

| Fornecedor | Plataforma | Observações |
|---|---|---|
| `atacadao` | VTEX | paginação por `?page=N` ou botão "Mostrar mais" |
| `stock` | VIP | scroll infinito |
| `asun` | Osuper | card = `.item-product-wrapper`; preço riscado = `.text-full-price`; sem venda por atacado tradicional (apesar do rodapé dizer isso — é texto padrão da plataforma, não confie nele) |
| `fort` | Osuper (mesma do Asun, HTML de card diferente) | card = `.products-list-body a`; preço riscado = `.line-through` (classe genérica, não a customizada do Asun); atacarejo de verdade — espera-se `preco_atacado` preenchido com frequência |

Em ambos Asun e Fort, os cards não têm `href` (a navegação é via
JavaScript), então a URL de cada produto é lida de um bloco
`<script type="application/ld+json">` (schema `ItemList`) que o próprio
site injeta na página — ver `_mapear_urls_por_ordem()` nesses dois
arquivos.

---

## 8. Adaptando para um novo site de mercado

1. Crie `scraper/scrapers/<nome>.py`, com uma classe `<Nome>Scraper(BaseScraper)`.
2. Defina `nome_fornecedor = "<nome>"`.
3. Implemente `definir_cep()` (siga o padrão de `fort.py`/`asun.py`).
4. Implemente `extrair_produtos_da_pagina()` com os seletores certos —
   descubra-os com a seção 6 acima antes de escrever qualquer código.
5. Registre em `scraper/scrapers/__init__.py`:
   ```python
   from scrapers.<nome> import <Nome>Scraper
   SCRAPERS_DISPONIVEIS = {
       ...,
       "<nome>": <Nome>Scraper,
   }
   ```
6. Adicione o domínio em `DOMINIO_PARA_FORNECEDOR`, no topo de
   `debug_inspecionar.py`.
7. Adicione tarefas em `scraper/data/produtos.py` com
   `"fornecedor": "<nome>"`.
8. Adicione o site em `SITES`, no topo de `setup_sessao.py`, e rode-o
   pra salvar a sessão.

Nenhum outro arquivo (`database.py`, `main.py`, `sheets_sync.py`) precisa
mudar — essa é a parte modular do projeto.

---

## 9. Adaptando para um site que NÃO é de mercado

A arquitetura não tem nada específico de supermercado — qualquer site
com um grid de produtos (nome + preço) serve. Como exemplo concreto,
olhei a **Galiotto Equipamentos** (galiottoequipamentos.com.br, loja de
equipamentos de cozinha industrial) pra já deixar uma referência real:

- É uma loja da plataforma **XNEO**, bem diferente do Osuper: o HTML já
  vem **pronto no servidor** (não depende de JavaScript rodar pra
  mostrar os produtos), os links dos produtos são `<a href="...">`
  normais, e o preço aparece em mais de um formato na mesma linha
  ("R$ 1.920,60 no PIX" **e** "R$ 1.980,00 em 6x de R$330,00") — então
  o `_extrair_precos()` de um scraper pra esse site precisaria decidir
  qual desses valores é o "preço" comparável (provavelmente o do PIX, à
  vista, que é o mais parecido com os outros scrapers).
- Não tem conceito de escolher CEP/loja (preço único pro site inteiro),
  então `definir_cep()` pode ser praticamente vazio — só navegar até a
  URL da categoria já basta.
- Cada categoria (ex: `/fogao-industrial`, `/acougue`) já é uma página
  de listagem direta, sem o nível intermediário de "subcategoria" que o
  Asun/Fort têm.

O processo pra mapear esse (ou qualquer outro site fora do ramo
alimentício) é o mesmo da seção 6: abra uma categoria de verdade no
navegador, rode (ou adapte) o `debug_inspecionar.py` nela, veja o HTML
real, e escreva os seletores a partir disso — nunca aproveite os
seletores do Asun/Fort/Atacadão sem confirmar, mesmo que o site "pareça"
parecido.

---

## 10. Rodando sozinho todo dia

**Linux/macOS (cron):**
```bash
crontab -e
```
```
0 8 * * * cd /caminho/para/atacado-scraper/scraper && /caminho/para/atacado-scraper/venv/bin/python main.py >> ../logs/coleta.log 2>&1
```

**Windows (Agendador de Tarefas):**
1. Abra o **Agendador de Tarefas** → Criar Tarefa Básica.
2. Gatilho: Diariamente, no horário desejado.
3. Ação: Iniciar um programa →
   - Programa/script: `C:\caminho\para\atacado-scraper\venv\Scripts\python.exe`
   - Argumentos: `main.py`
   - Iniciar em: `C:\caminho\para\atacado-scraper\scraper`

---

## 11. Perguntas frequentes / decisões de projeto

**A planilha depende do banco SQLite?**
Não mais. `main.py` chama `sheets_sync.sincronizar_produtos(produtos)`,
que manda pra planilha os produtos direto da memória — a mesma lista
que acabou de ser coletada — sem ler o banco. O banco continua sendo
gravado normalmente (é o histórico local, usado pelos relatórios do
terminal e pelo `--filtro`), mas ele deixou de ser um passo obrigatório
pra planilha ficar atualizada. Se um dia você quiser mandar o
**histórico inteiro** do banco pra planilha (não só a última coleta),
a função antiga continua disponível: `python sheets_sync.py` chama
`sincronizar_planilha()`.

**As imagens (prints) aparecem de verdade na planilha?**
Não — a coluna `imagem_print` mostra o **caminho do arquivo** no seu
computador (texto), não uma miniatura visível. Isso vale tanto pro
`sincronizar_produtos()` quanto pro `sincronizar_planilha()` — não é
uma limitação do banco, é que o Google Sheets só consegue *exibir*
imagens que estejam hospedadas em algum lugar acessível pela internet
(ex: Google Drive com link público + fórmula `=IMAGE(url)`). Dá pra
implementar isso subindo cada print pro Drive antes de montar a
planilha, mas é uma etapa a mais — avise se quiser essa função.

**Cada execução do `main.py` apaga os dados antigos?**
No **banco**, não — cada execução **insere** linhas novas (nunca
sobrescreve), então o SQLite acumula histórico de preço ao longo do
tempo. Na **planilha**, sim — ela é sobrescrita a cada sincronização
com os dados da coleta que acabou de rodar (não acumula histórico lá).

**Uso responsável:** rode a coleta com um intervalo razoável (ex: 1x/dia)
e evite abrir muitas abas em paralelo — isso reduz o risco de bloqueio e
é mais educado com a infraestrutura dos sites. Este projeto é pensado
para uso pessoal/interno de acompanhamento de preços.

---

## 12. Troubleshooting rápido

| Sintoma | Causa provável | Solução |
|---|---|---|
| `Executable doesn't exist` (Playwright) | navegador não instalado | `playwright install chromium` (Windows) ou `playwright install --with-deps chromium` (Linux) |
| `GOOGLE_SHEETS_SPREADSHEET_ID não definido` | `.env` não criado/preenchido | seção 2.2 |
| 0 cards encontrados | `SEL_CARD_PRODUTO` desatualizado | seção 6 |
| Cards encontrados, mas 0 produtos extraídos | `SEL_NOME_PRODUTO`/preço não batem | seção 6 — o próprio bot salva `logs/debug_vazio_<categoria>.html` automaticamente nesse caso |
| `FileNotFoundError` na credencial do Google | JSON não está em `credentials/` | seção 2.1 |
| `gspread.exceptions.SpreadsheetNotFound` | ID errado no `.env`, ou planilha não compartilhada com o e-mail da conta de serviço | seção 2 |
| Loja errada / cidade errada | sessão não configurada pra esse site, ou site caiu numa loja padrão por geolocalização | rode `setup_sessao.py` e confirme manualmente a loja certa |
| CEP "não fica salvo" entre execuções | — | já resolvido: o projeto usa `launch_persistent_context` (perfil completo, salva sessionStorage também) |