# 06 — Tarefas de coleta (`data/tarefas/*.py`, `data/produtos.py`)

## Formato de uma tarefa
```python
{
    "fornecedor": "gimba",            # chave de SCRAPERS_DISPONIVEIS
    "categoria": "Mercearia",         # nome livre (agrupa no relatório/planilha)
    "url": "https://.../categoria",   # listagem de categoria/corredor/busca
    "palavras_chave": ["arroz branco", "feijão preto"],   # opcional; None/ausente = tudo
}
```
- `palavras_chave`: substring case-insensitive no nome; sem normalização de acento → **incluir variantes com e sem acento** (`"pimentão"`, `"pimentao"`).
- Uma mesma URL pode ter várias tarefas com `categoria`/`palavras_chave` diferentes (ex.: Gimba "Azeites" x "Óleo" na mesma URL).

## Convenções de arquivo
- `data/tarefas/<fornecedor>.py` exporta `TAREFAS_<FORNECEDOR>` (lista).
- Docstring do topo: o que o site tem/não tem da lista de alimentos, achados (ex.: "não existe charque → jerked beef"), itens sem tarefa e por quê.
- Constantes privadas com `_` (`_B`/`_A` = base da URL/loja; `_FRUTAS`, `_LEGUMES`, `_VERDURAS`, `_AVES`, `_BOVINA`...) para reaproveitar listas de palavras entre tarefas. Prefixo **um** underscore (o `__FRUTAS` antigo foi corrigido).
- Base de referência do que monitorar: `data/alimentos.py::LISTA_ALIMENTOS_PADRAO` (hortifruti, carnes, grãos, massas, óleos, laticínios...). Montar `palavras_chave` a partir dela; não inventar itens fora dela sem pedido.
- Mesma rede em outra loja/região = derivar da lista existente trocando só a base da URL e o `fornecedor` (padrão de `rappi_condor.py`): `{**t, "fornecedor": "...", "url": t["url"].replace(_B_A, _B_B)}`. Ajustar palavras-chave na lista-mãe vale para todas.

## Ativar/desativar (`data/produtos.py`)
`TAREFAS_DE_COLETA` é uma lista de `*TAREFAS_X`; **comentar a linha desativa** o fornecedor (e o import correspondente
pode ficar comentado ou não). Para testar só um site, deixar só a linha dele ativa e **restaurar** o estado desejado
pelo usuário depois (não deixar tudo ativo/desativado sem avisar).

## Como descobrir a URL certa
- Navegar categoria → corredor no site e copiar a URL; preferir URL de **subcategoria** (menos ruído) e filtrar por `palavras_chave`.
- Onde não há corredor: usar a busca do site (`/s?term=...`) — traz resultados aproximados, o filtro por palavra-chave é essencial.
- Departamentos podem já conter subcategorias (Gimba) → não listar as duas (duplica).
- Confirmar no site real se o item existe antes de criar a tarefa; documentar na docstring os que não existem.
