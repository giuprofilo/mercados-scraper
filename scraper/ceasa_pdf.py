"""
Extrai dos PDFs de cotação da CEASA os preços das frutas, legumes e verduras
listados em data/tarefas/atacadao.py (_FRUTAS, _LEGUMES, _VERDURAS) e grava um
CSV em exports/ (e, com --sheets, na aba do .env). Cada formato mantém TODOS
os campos do seu PDF (não reduzir sem pedido: já se perdeu dado assim):
- Curitiba: categoria, palavra_chave, secao, produto, variedade, tipo,
  embalagem, situacao, min, mc_dia, max, mc_anterior, var_pct, peso_kg,
  preco_kg, procedencia.
- Porto Alegre: categoria, palavra_chave, secao, produto, und, max,
  mais_frequente, minimo, peso_kg, preco_kg.

Dois formatos (detectados pelo texto do PDF):
- CEASA-PR Curitiba ("Coleta de Preços Diário", cotacao-PR-curitiba-*.pdf):
  Produto | Tipo | Unidade Embalagem | Situação | Min | M_C Do Dia | Max | ...
  O preço (M_C = preço mais comum do dia) é por EMBALAGEM ("cx 20 kg",
  "mç 400g"); preco_kg = preco / peso da embalagem (estimativa: peso da
  caixa/saco). Seção e produto ("ABACATE") são linhas sem números em x=33; as
  variedades vêm em x=41, uma por linha de dados. Linhas de dados em x=33 cujo
  texto repete o "Tipo" são variedade do produto acima; senão são produto de
  linha único (ex.: "ABIU"). O texto em colunas (pdftotext -layout) mistura
  variedade/tipo/embalagem, por isso a leitura usa as coordenadas das palavras
  (pdftotext -bbox).
- CEASA-RS Porto Alegre ("BOLETIM INFORMATIVO DE PREÇOS", cotacao-POA-*.pdf):
  Produto | UND | MAX | MAIS FREQUENTE | MÍNIMO, uma linha por produto. O preço
  (MAIS FREQUENTE) já é por UND (KG, DZ, MOL, BDJ...): peso_kg=1 e
  preco_kg=mais_frequente só quando UND é KG e há cotação. Preço 0.00 = sem
  cotação no dia: a linha é mantida com os valores do PDF, sem preco_kg.
  Só as seções "VERDURAS E LEGUMES" e "FRUTAS" entram.
- CEASA-MT Cuiabá ("Boletim Informativo de Preços", CEASA-MT-CUIABA-*.pdf):
  Produto | Unidades | Procedência | Mínimo | Mais comum | Máximo, preço por
  EMBALAGEM ("Cx. (18 a 20Kg)", "Un. (250 a 300g)", "Dz."). Saída no formato da
  aba Coleta da planilha (planilha_fgv.py), não nos campos do PDF: empresa,
  pesquisador e insumos vêm dos CSVs em ../csv/ (cópias das abas da planilha);
  Preço PRODUTO = mais comum da embalagem, PREÇO FINAL = R$/kg (peso médio da
  faixa da embalagem; "dz." com peso por unidade = 12 x peso). Sem peso (Dz.,
  Mç., ovos) PREÇO FINAL = o próprio preço da embalagem. Observações = insumo +
  "Unidade: <embalagem>". FONTE = FONTE_MT (página do Prohort). Melancia
  ("Un. (11 a15Kg)" a R$ 2,50) é preço por kg, não por unidade. Mín/máx e
  procedência vão em OBS Desconto. Só entram produtos que casam com um insumo
  do CSV (igual ao planilha_fgv, + ALIAS_INSUMO_MT: "Batata lisa" = batata
  inglesa, "Couve" = couve manteiga); a lista do Atacadão NÃO é usada aqui.
- CEASA-DF ("COTAÇÕES DE PREÇOS NO ATACADO", CEASA-DF-*.pdf): Produtos/Variedades |
  Unidade de comercialização | Preço mínimo | Preço + comum | Preço máximo, preço
  por EMBALAGEM ("Cx- 18 a 20 kg.", "Mç- 0,3 a 0,4 kg.", "1 kg."). Mesmo formato
  de saída e mesmas regras do MT (insumos do CSV, PREÇO FINAL = R$/kg pelo peso
  médio da faixa; sem peso = preço da embalagem). FONTE = FONTE_DF. Linhas sem
  cotação (vazias ou 0,00) ficam fora. Seções: hortaliças, frutas, ovos, diversos.
- Requer o utilitário pdftotext (poppler-utils) instalado no sistema.

Uso (de dentro de scraper/):
    python ceasa_pdf.py ../CEASA/cotacao-POA-24-09.pdf            # só CSV
    python ceasa_pdf.py ../CEASA/cotacao-POA-24-09.pdf --sheets   # CSV + Sheets
    python ceasa_pdf.py ../CEASA/CEASA-MT-CUIABA-05.09.pdf        # CSV no formato Coleta
    python ceasa_pdf.py ../CEASA/CEASA-DF-05-10.pdf --sheets --aba "DF - CEASA 05-10"
    python ceasa_pdf.py <pdf> --sheets --aba "PR - CEASA 24-09"    # outra aba que a do .env

Com --sheets, a aba é a de GOOGLE_SHEETS_WORKSHEET_NAME (.env) e é SOBRESCRITA;
use uma aba própria por PDF (ex.: "PR - CEASA 24-09", "POA - CEASA 24-09"),
nunca a da coleta dos scrapers.
"""

import csv
import os
import re
import statistics
import subprocess
import sys
import unicodedata
from typing import Optional

import config
from data.tarefas.atacadao import _FRUTAS, _LEGUMES, _VERDURAS

SECOES_ALIMENTO = {
    "frutas nacionais / importadas",
    "demais frutas",
    "hortalicas frutos",
    "hortalicas tuberosas",
    "hortalicas herbaceas",
}
OUTRAS_SECOES = {
    "granjeiros",
    "graos e cereais",
    "flores de corte",
    "plantas ornamentais",
    "forracoes",
    "flores de vasos",
    "flor de vaso / mini",
    "orquidea",
    "produtos ausentes",
    "fonte",
    "legendas",
}
SITUACOES = {"estavel", "firme", "fraco", "ausente"}

# Palavras da lista do Atacadão que os PDFs escrevem de outro jeito.
SINONIMOS = {"tanjerina": ["tangerina"], "cheiro verde": ["tempero verde"]}
# Produtos que começam com uma palavra da lista mas são outro alimento.
EXCLUIR = {"alho poro", "batata yakon"}

_RE_NUM = re.compile(r"^-?\d+(?:\.\d{3})*,\d+$")
_RE_PESO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", re.IGNORECASE)
_RE_PALAVRA = re.compile(r"<word xMin=\"([\d.]+)\" yMin=\"([\d.]+)\" xMax=\"([\d.]+)\" "
                         r"yMax=\"[\d.]+\">(.*?)</word>")
_GAP_SEGMENTO = 10.0  # pt: espaço entre colunas (dentro de uma coluna é ~3 pt)


def _norm(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


def _tokens(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _norm(texto))


def _num(texto: str) -> float:
    return float(texto.replace(".", "").replace(",", "."))


def _classificar_palavras() -> list[tuple[list[str], str, str]]:
    """[(tokens da palavra-chave, palavra original, categoria)], mais longas antes."""
    itens = []
    for categoria, lista in (
        ("fruta", _FRUTAS),
        ("legume", _LEGUMES),
        ("verdura", _VERDURAS),
    ):
        for palavra in lista:
            for alvo in [palavra, *SINONIMOS.get(_norm(palavra), [])]:
                itens.append((_tokens(alvo), palavra, categoria))
    itens.sort(key=lambda i: -len(i[0]))
    return itens


def _casar(produto: str, palavras) -> Optional[tuple[str, str]]:
    """Palavra-chave cujas palavras abrem o nome do produto (ex.: "batata doce"
    casa "BATATA DOCE"; "alho" casa "ALHO NACIONAL"). Devolve (palavra, categoria)."""
    toks = _tokens(produto)
    if " ".join(toks) in EXCLUIR:
        return None
    for chave, original, categoria in palavras:
        if toks[: len(chave)] == chave:
            return original, categoria
    return None


def _peso_kg(embalagem: str) -> Optional[float]:
    """Peso do último "<n> kg|g" da embalagem ("cx c/30dz - 25kg" -> 25;
    "mç 400g" -> 0.4). None se não houver peso."""
    achados = _RE_PESO.findall(embalagem)
    if not achados:
        return None
    valor, unidade = achados[-1]
    kg = float(valor.replace(",", "."))
    return kg / 1000 if unidade.lower() == "g" else kg


def _paginas(pdf: str) -> list[list[tuple[float, float, float, str]]]:
    saida = subprocess.run(
        ["pdftotext", "-bbox", pdf, "-"], capture_output=True, text=True, check=True
    ).stdout
    paginas = []
    for bloco in saida.split("<page ")[1:]:
        palavras = [
            (float(x0), float(y), float(x1), _desescapar(t))
            for x0, y, x1, t in _RE_PALAVRA.findall(bloco)
        ]
        paginas.append(palavras)
    return paginas


def _desescapar(t: str) -> str:
    return t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def _linhas(palavras) -> list[list[tuple[float, float, float, str]]]:
    linhas: list[list] = []
    for p in sorted(palavras, key=lambda p: (round(p[1]), p[0])):
        if linhas and abs(linhas[-1][0][1] - p[1]) <= 2:
            linhas[-1].append(p)
        else:
            linhas.append([p])
    return [sorted(l) for l in linhas]


def _segmentos(palavras) -> list[list]:
    """Agrupa palavras vizinhas (mesma coluna); uma lacuna grande abre coluna nova."""
    segs: list[list] = []
    for p in palavras:
        if segs and p[0] - segs[-1][-1][2] < _GAP_SEGMENTO:
            segs[-1].append(p)
        else:
            segs.append([p])
    return segs


def _texto(seg) -> str:
    return " ".join(p[3] for p in seg)


def extrair(pdf: str) -> tuple[list[dict], str, list[str]]:
    """Devolve (registros, data da coleta, avisos). Um registro por variedade,
    de todas as seções de frutas/hortaliças (sem filtrar pela lista)."""
    registros: list[dict] = []
    avisos: list[str] = []
    data = ""
    secao = produto = ""

    for palavras in _paginas(pdf):
        linhas = _linhas(palavras)
        texto_pagina = " ".join(p[3] for p in palavras)
        m = re.search(r"Coleta:\s*(\d{2}/\d{2}/\d{4})", texto_pagina)
        if m:
            data = data or m.group(1)

        # fim do cabeçalho da página = linha "Embalagem ... Mercado ... Dia"
        y_fim_cab = next(
            (l[0][1] for l in linhas if any(p[3] == "Embalagem" for p in l)), 0
        )
        linhas = [l for l in linhas if l[0][1] > y_fim_cab + 1]

        # Ancora: linha com a "Situação do mercado"
        def situacao(l):
            return next((p for p in l if _norm(p[3]) in SITUACOES and p[0] > 200), None)

        ancoras = [l for l in linhas if situacao(l)]

        # fronteiras das colunas (pelo centro do texto), a partir do cabeçalho
        cab = {p[3]: p for l in _linhas(palavras) for p in l if p[1] <= y_fim_cab + 1}
        centro_tipo = (cab["Tipo"][0] + cab["Tipo"][2]) / 2
        centro_emb = (cab["Embalagem"][0] + cab["Embalagem"][2]) / 2
        limites = (centro_tipo - 45, (centro_tipo + centro_emb) / 2)

        # borda direita de cada coluna numérica nesta página (mediana)
        bordas: list[list[float]] = [[], [], [], [], []]
        for l in ancoras:
            nums = [p for p in l if _RE_NUM.match(p[3])]
            if len(nums) in (4, 5):
                for i, p in enumerate(nums):
                    bordas[i].append(p[2])
        ref = [statistics.median(b) if b else None for b in bordas]
        if ref[4] is None and ref[3] is not None:
            ref[4] = ref[3] + 48

        def coluna_numerica(x1):
            cand = [(abs(x1 - r), i) for i, r in enumerate(ref) if r is not None]
            return min(cand)[1] if cand else None

        for l in linhas:
            sit = situacao(l)
            if sit is None:
                # continuação de célula (ex.: embalagem em 2 linhas): sem palavras
                # na coluna do produto e colada numa linha de dados
                if l[0][0] >= 100 and any(
                    abs(l[0][1] - a[0][1]) <= 14 for a in ancoras
                ):
                    continue
                titulo = _texto(l)
                if _norm(titulo) in SECOES_ALIMENTO | OUTRAS_SECOES:
                    secao, produto = _norm(titulo), ""
                elif secao in SECOES_ALIMENTO and l[0][0] < 60:
                    produto = titulo
                continue

            if secao not in SECOES_ALIMENTO:
                continue

            dir_ = [p for p in l if p[0] > sit[2]]

            # célula em várias linhas (ex.: embalagem "sc 50 espigas -" / "13kg"):
            # linhas coladas nesta, sem palavras na coluna do produto, entram na
            # mesma linha lógica, na ordem vertical
            coladas = [
                c
                for c in linhas
                if c is not l
                and situacao(c) is None
                and c[0][0] >= 100
                and abs(c[0][1] - l[0][1]) <= 14
                and min(abs(c[0][1] - a[0][1]) for a in ancoras)
                == abs(c[0][1] - l[0][1])
            ]
            colunas = {"variedade": [], "tipo": [], "embalagem": []}
            for linha in sorted(coladas + [l], key=lambda c: c[0][1]):
                esq = [p for p in linha if p[2] <= sit[0] - 1 and p is not sit]
                for seg in _segmentos(esq):
                    centro = (seg[0][0] + seg[-1][2]) / 2
                    if centro < limites[0]:
                        colunas["variedade"].append(_texto(seg))
                    elif centro < limites[1]:
                        colunas["tipo"].append(_texto(seg))
                    else:
                        colunas["embalagem"].append(_texto(seg))
            variedade = " ".join(colunas["variedade"])
            tipo = " ".join(colunas["tipo"])
            embalagem = " ".join(colunas["embalagem"])
            x_variedade = min((p[0] for p in l if p[0] < limites[0]), default=99)

            # produto de linha única (x=33 e texto diferente do tipo)
            nome_produto = produto
            if variedade and x_variedade < 37 and _norm(variedade) != _norm(tipo):
                nome_produto, variedade = variedade, ""

            nums = [None] * 5
            for p in dir_:
                if _RE_NUM.match(p[3]):
                    i = coluna_numerica(p[2])
                    if i is not None and nums[i] is None:
                        nums[i] = _num(p[3])
            origem = " ".join(p[3] for p in dir_ if not _RE_NUM.match(p[3]))
            if sum(n is not None for n in nums[:4]) < 4 and _norm(sit[3]) != "ausente":
                avisos.append(
                    f"linha com menos de 4 preços: {nome_produto} {variedade} {tipo}"
                )

            peso = _peso_kg(embalagem)
            mc = nums[1]
            registros.append(
                {
                    "secao": secao,
                    "produto": nome_produto,
                    "variedade": variedade,
                    "tipo": tipo,
                    "embalagem": embalagem,
                    "situacao": sit[3],
                    "min": nums[0],
                    "mc_dia": mc,
                    "max": nums[2],
                    "mc_anterior": nums[3],
                    "var_pct": nums[4],
                    "procedencia": origem,
                    "peso_kg": peso,
                    "preco_kg": round(mc / peso, 2) if mc and peso else None,
                }
            )
    return registros, data, avisos


_RE_LINHA_RS = re.compile(
    r"^\s*(?P<nome>.+?)\s{2,}(?P<und>.+?)\s+R\$\s*(?P<max>[\d.,]+)"
    r"\s+R\$\s*(?P<freq>[\d.,]+)\s+R\$\s*(?P<min>[\d.,]+)\s*$"
)
SECOES_RS = {"verduras e legumes", "frutas"}


def _texto_pdf(pdf: str) -> str:
    return subprocess.run(
        ["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True
    ).stdout


def extrair_rs(texto: str) -> tuple[list[dict], str, list[str]]:
    """Formato CEASA-RS Porto Alegre. Devolve (registros, data, avisos)."""
    registros, avisos = [], []
    m = re.search(r"Data:\s*(\d{2}/\d{2}/\d{4})", texto)
    data = m.group(1) if m else ""
    secao = ""
    for linha in texto.splitlines():
        if not linha.strip() or "R$" not in linha:
            titulo = _norm(linha)
            if titulo and not re.search(r"boletim|data:|unidade:|produto|p.gina", titulo):
                secao = titulo
            continue
        m = _RE_LINHA_RS.match(linha)
        if not m:
            avisos.append(f"linha não reconhecida: {linha.strip()}")
            continue
        if secao not in SECOES_RS:
            continue
        preco = float(m.group("freq"))
        und = m.group("und")
        por_kg = und.upper() == "KG" and preco > 0
        registros.append(
            {
                "secao": secao,
                "produto": m.group("nome").strip(),
                "und": und,
                "max": float(m.group("max")),
                "mais_frequente": preco,
                "minimo": float(m.group("min")),
                "peso_kg": 1.0 if por_kg else None,
                "preco_kg": preco if por_kg else None,
            }
        )
    return registros, data, avisos


_RE_PRECO_MT = r"(\d+(?:\.\d{3})*,\d{2}|-{3,})"
_RE_LINHA_MT = re.compile(rf"^(?P<texto>.*?)\s*{_RE_PRECO_MT}\s+{_RE_PRECO_MT}\s+{_RE_PRECO_MT}\s*$")
_RE_FAIXA_PESO = re.compile(
    r"(\d+(?:,\d+)?)\s*(?:a\s*(\d+(?:,\d+)?))?\s*(kg|g)\b", re.IGNORECASE
)


def _peso_medio_kg(trecho: str) -> Optional[float]:
    """Peso médio (kg) da primeira faixa "18 a 20Kg" / "250 a 300g" / "5Kg"."""
    m = _RE_FAIXA_PESO.search(trecho)
    if not m:
        return None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", ".")) if m.group(2) else a
    kg = (a + b) / 2
    return kg / 1000 if m.group(3).lower() == "g" else kg


def _preco_mt(texto: str) -> Optional[float]:
    return None if texto.startswith("-") else _num(texto)


def extrair_mt(texto: str) -> tuple[list[dict], str, list[str]]:
    """Formato CEASA-MT Cuiabá. Devolve (registros, data, avisos).

    O pdftotext quebra 3 linhas: abacaxi graúdo (variedade com preços e o nome
    na linha de baixo) e banana nanica (procedência com preços e o nome embaixo).
    """
    registros, avisos = [], []
    m = re.search(r"PERÍODO de (\d{2}) a \d{2}\.(\d{2}\.\d{4})", texto)
    data = f"{m.group(1)}/{m.group(2).replace('.', '/')}" if m else ""
    linhas = [l for l in texto.splitlines() if l.strip()]
    for i, linha in enumerate(linhas):
        m = _RE_LINHA_MT.match(linha)
        if not m or "MÍNIMO" in linha:
            continue
        segs = [s for s in re.split(r"\s{2,}", m.group("texto").strip()) if s]
        if len(segs) == 3:
            nome, und, proc = segs
            variedade = re.match(r"(.+?)\s*(\(dz\.\))$", und)  # abacaxi médio
            if variedade:
                nome, und = f"{nome} {variedade.group(1)}", variedade.group(2)
        elif len(segs) == 1 and i + 1 < len(linhas):
            prox = [s for s in re.split(r"\s{2,}", linhas[i + 1].strip()) if s]
            if len(prox) < 2 or _RE_LINHA_MT.match(linhas[i + 1]):
                avisos.append(f"linha não reconhecida: {linha.strip()}")
                continue
            nome, und = prox[0], prox[1]
            if re.fullmatch(r"[A-Z/ ]+", segs[0]):  # banana nanica
                proc = segs[0]
            else:  # abacaxi: a variedade aparece antes do nome
                nome, proc = f"{nome} {segs[0]}", prox[2] if len(prox) > 2 else ""
        else:
            avisos.append(f"linha não reconhecida: {linha.strip()}")
            continue
        minimo, comum, maximo = (_preco_mt(g) for g in m.group(2, 3, 4))
        registros.append(
            {
                "secao": "",
                "produto": re.sub(r"\s+", " ", nome).strip(),
                "embalagem": und.strip(),
                "procedencia": proc.strip(),
                "min": minimo,
                "mais_comum": comum,
                "max": maximo,
            }
        )
    return registros, data, avisos


def preco_kg_mt(r: dict) -> tuple[Optional[float], str]:
    """(R$/kg, nota) do registro de Cuiabá; None quando a embalagem não tem peso."""
    comum = r["mais_comum"]
    if comum is None:
        return None, ""
    und = r["embalagem"]
    por_unidade = _peso_medio_kg(und)
    if por_unidade is None:  # abacaxi: peso por unidade no nome, embalagem em dz.
        por_unidade = _peso_medio_kg(r["produto"])
        if por_unidade is not None and "dz" in und.lower():
            return comum / (12 * por_unidade), "dz. = 12 un. x peso médio"
        return None, ""
    if und.lower().startswith("un") and por_unidade >= 5:
        return comum, "preço já é por kg (melancia vendida por unidade pesada)"
    return comum / por_unidade, f"peso médio da embalagem {por_unidade:g} kg"


_RE_LINHA_DF = re.compile(
    r"^(?P<texto>.+?)(?P<precos>(?:\s+\d+(?:\.\d{3})*,\d{2}){3})?\s*$"
)
_RE_FAIXA_DF = re.compile(
    r"(\d+(?:,\d+)?)\s*(?:(?:a|-)\s*(\d+(?:,\d+)?))?\s*(kg|g)\b", re.IGNORECASE
)
_CABECALHO_DF = ("produtos/variedades", "unidade de co", "mercializacao", "comum", "governo",
                 "seagri", "desenvolvimento", "centrais", "gerencia", "secao de", "cotacoes")


def _peso_medio_df(unidade: str) -> Optional[float]:
    """Peso médio (kg) da faixa da unidade ("Cx- 18 a 20 kg", "Mç- 0.4 a 0.6 kg",
    "Cxta- 4 - 6 kg", "Cx- (50dzs) 4 kg", "1 kg"); None se não houver peso."""
    texto = re.sub(r"(?<=\d)\.(?=\d)", ",", unidade.replace("–", "-"))
    m = _RE_FAIXA_DF.search(texto)
    if not m:
        return None
    a = float(m.group(1).replace(",", "."))
    b = float(m.group(2).replace(",", ".")) if m.group(2) else a
    kg = (a + b) / 2
    return kg / 1000 if m.group(3).lower() == "g" else kg


def extrair_df(texto: str) -> tuple[list[dict], str, list[str]]:
    """Formato CEASA-DF. Devolve (registros, data, avisos). Mesmos campos do MT
    (produto, embalagem, procedencia vazia, min, mais_comum, max)."""
    registros, avisos = [], []
    m = re.search(r"DATA\s*[–-]\s*(\d{2})\.(\d{2})\.(\d{4})", texto)
    data = "/".join(m.groups()) if m else ""
    secao = ""
    for linha in texto.splitlines():
        if not linha.strip() or any(c in _norm(linha) for c in _CABECALHO_DF):
            continue
        m = _RE_LINHA_DF.match(linha.strip())
        segs = [s for s in re.split(r"\s{2,}", m.group("texto").strip()) if s] if m else []
        if len(segs) == 1 and not m.group("precos"):
            secao = _norm(segs[0])
            continue
        if len(segs) != 2:
            avisos.append(f"linha não reconhecida: {linha.strip()}")
            continue
        precos = [_num(p) for p in (m.group("precos") or "").split()]
        # 0,00 = sem cotação (ex.: alho importado)
        minimo, comum, maximo = ([p or None for p in precos] + [None] * 3)[:3]
        registros.append(
            {
                "secao": secao,
                "produto": segs[0],
                "embalagem": segs[1],
                "procedencia": "",
                "min": minimo,
                "mais_comum": comum,
                "max": maximo,
            }
        )
    return registros, data, avisos


def preco_kg_df(r: dict) -> tuple[Optional[float], str]:
    """(R$/kg, nota) do registro do DF; None quando a unidade não tem peso."""
    comum = r["mais_comum"]
    peso = _peso_medio_df(r["embalagem"])
    if comum is None or peso is None:
        return None, ""
    return comum / peso, f"peso médio da embalagem {peso:g} kg"


# Nomes do boletim de Cuiabá que não repetem a descrição do insumo.
FONTE_MT = "https://www.agriculturafamiliar.mt.gov.br/prohort2"
FONTE_DF = "https://www.portal.ceasadf.com.br/informacao-mercado"
EXCLUIR_MT = {"alface americana"}  # pedido do usuário: não coletar (vale para MT e DF)

ALIAS_INSUMO_MT = {
    "batata lisa": "BATATA, INGLESA, CRUA",
    "couve": "COUVE, MANTEIGA, CRUA",
}
# Variedades do boletim do DF que o casamento por palavra confundiria com outro insumo
# (o insumo é uma variedade específica: cabotian, tahiti, formosa, palmer, fuji, branco...).
EXCLUIR_DF = EXCLUIR_MT | {
    "abobora moranga", "abobora seca ou madura", "alho porro", "cebola roxa",
    "cajamanga", "caja-manga", "limao siciliano", "mamao havaiano", "manga tommy atkins",
    "manga espada", "manga haden", "maca gala cat-1 tp-90 a 135", "maca gala (solta)",
    "maca red delicious 113 a 135", "maca granny smith", "melao orange",
    "pera d'anjou 100 a 120", "pera d\u2019anjou 100 a 120", "ovos de codorna",
    "repolho roxo", "salsao (aipo)", "tomate cereja", "tomate italiano",
}  # fmt: skip

# Nomes do boletim do DF (aliases exatos, normalizados) e prefixos de variedade.
ALIAS_INSUMO_DF = {
    "batata lisa especial/extra": "BATATA, INGLESA, CRUA",
    "batata lisa primeira/diversa": "BATATA, INGLESA, CRUA",
    "couve manteiga": "COUVE, MANTEIGA, CRUA",
    "alface lisa/crespa": "ALFACE, LISA, CRUA",
    "ovos de galinha branco extra": "OVO, DE GALINHA, INTEIRO, CRU",
    "ovos de galinha branco grande": "OVO, DE GALINHA, INTEIRO, CRU",
    "ovos de galinha branco medio": "OVO, DE GALINHA, INTEIRO, CRU",
    "ovos de galinha vermelho extra": "OVO, DE GALINHA, INTEIRO, CRU",
    "ovos de galinha vermelho grande": "OVO, DE GALINHA, INTEIRO, CRU",
}


def _ler_csv(nome: str) -> list[dict]:
    caminho = os.path.join(config.BASE_DIR, "csv", f"Pesquisa de Precos - Alimentos FNDE Centro-Oeste - {nome}.csv")
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def montar_coleta_mt(
    itens: list[dict],
    data: str,
    uf: str = "MT",
    fonte: str = "",
    rotulo: str = "CEASA-MT Cuiabá",
    alias_insumo: Optional[dict] = None,
    calcular_kg=None,
    excluir: Optional[set] = None,
) -> tuple[list[str], list[dict], list[str]]:
    """Linhas no formato da aba Coleta (ver planilha_fgv.py). Devolve (cabeçalho, linhas, avisos)."""
    import planilha_fgv

    fonte = fonte or FONTE_MT
    alias_insumo = ALIAS_INSUMO_MT if alias_insumo is None else alias_insumo
    calcular_kg = calcular_kg or preco_kg_mt
    excluir = EXCLUIR_MT if excluir is None else excluir
    insumos = [i for i in _ler_csv("Insumos") if i.get("Descrição")]
    for i in insumos:
        i["_palavras"] = planilha_fgv._palavras(i["Descrição"])
    empresas = [e for e in _ler_csv("Empresas") if e.get("Nome Empresa")]
    desejada = (config.EMPRESA_COLETA or "").strip().casefold()
    empresa = next((e for e in empresas if desejada in e["Nome Empresa"].casefold()), None)
    if empresa is None:  # o CSV pode estar desatualizado: lê a aba Empresas (só leitura)
        try:
            empresa = planilha_fgv._escolher_empresa(planilha_fgv._conectar())
        except Exception as e:
            sys.exit(f"EMPRESA_COLETA não está no CSV de Empresas e a leitura da planilha falhou: {e}")
    pesquisador = (config.PESQUISADOR or "").strip() or next(
        (list(l.values())[0].strip() for l in _ler_csv("Pesquisadores") if list(l.values())[0].strip()), ""
    )
    cabecalho = list(_ler_csv("Coleta")[0].keys())
    linhas, avisos = [], []
    for r in itens:
        if _norm(r["produto"]) in excluir:
            continue
        alias = alias_insumo.get(_norm(r["produto"]))
        insumo = (
            next((i for i in insumos if i["Descrição"] == alias), None)
            if alias
            else planilha_fgv.escolher_insumo(r["produto"], insumos)
        )
        if insumo is None:
            avisos.append(f"sem insumo na planilha, fora da coleta: {r['produto']}")
            continue
        if r["mais_comum"] is None:
            avisos.append(f"sem cotação no boletim, fora da coleta: {r['produto']}")
            continue
        kg, nota = calcular_kg(r)
        if kg is None:  # sem kg: vale o preço da embalagem (mais comum)
            kg, nota = r["mais_comum"], "preço por embalagem (sem peso em kg)"
        obs = f"{rotulo}; embalagem {r['embalagem']}; mín R$ {r['min']}; máx R$ {r['max']}"
        if r["procedencia"]:
            obs += f"; proc. {r['procedencia']}"
        obs += f"; {nota}"
        campos = {
            "Buscar Empresa": empresa["Busca (dropdown)"],
            "CNPJ": empresa["CNPJ"],
            "Nome Empresa": empresa["Nome Empresa"],
            "UF Empresa": empresa["UF Empresa"],
            "Buscar Insumo": insumo.get("Busca (dropdown)", ""),
            "Código FGV": insumo.get("Código do Insumo", ""),
            "Categoria": insumo.get("Categoria", ""),
            "Grupo de Insumo": insumo.get("Grupo de Insumo", ""),
            "Descrição do insumo": insumo.get("Descrição", ""),
            "Observações": "; ".join(
                x for x in (insumo.get("Observações", ""), f"Unidade: {r['embalagem']}") if x
            ),
            "UF Preço": uf,
            "Data coleta": data.replace("/", "-"),
            "Pesquisador": pesquisador,
            "FONTE": fonte,
            "PRODUTO PESQUISADO": f"{r['produto']} - {r['embalagem']}",
            "Preço PRODUTO": round(r["mais_comum"], 2),
            "OBS Desconto": obs,
            "PREÇO FINAL": round(kg, 2),
        }
        linhas.append({c: campos.get(c, "") for c in cabecalho})
    linhas.sort(key=lambda l: (l["Descrição do insumo"], l["PREÇO FINAL"] == "", l["PREÇO FINAL"] or 0))
    return cabecalho, linhas, avisos


def filtrar_lista_atacadao(registros: list[dict]) -> list[dict]:
    palavras = _classificar_palavras()
    saida = []
    for r in registros:
        achado = _casar(r["produto"], palavras)
        if achado:
            saida.append({**r, "palavra_chave": achado[0], "categoria": achado[1]})
    return saida


CAMPOS_CURITIBA = [
    "categoria", "palavra_chave", "secao", "produto", "variedade", "tipo",
    "embalagem", "situacao", "min", "mc_dia", "max", "mc_anterior", "var_pct",
    "peso_kg", "preco_kg", "procedencia",
]  # fmt: skip
CAMPOS_POA = [
    "categoria", "palavra_chave", "secao", "produto", "und", "max",
    "mais_frequente", "minimo", "peso_kg", "preco_kg",
]  # fmt: skip


def enviar_para_sheets(itens: list[dict], campos: list[str]) -> None:
    import sheets_sync

    if not sheets_sync._pronto_para_sincronizar():
        return
    linhas = [campos] + [["" if i.get(c) is None else i[c] for c in campos] for i in itens]
    sheets_sync._enviar_linhas(linhas)
    print(
        f"Aba '{config.GOOGLE_SHEETS_WORKSHEET_NAME}' atualizada com {len(itens)} linhas."
    )


def enviar_coleta_mt(linhas: list[dict], cabecalho: list[str]) -> None:
    """Grava na aba própria (nome do .env) como VALORES, igual ao planilha_fgv."""
    import gspread
    import planilha_fgv

    if not planilha_fgv.nome_aba_valido():
        return
    planilha = planilha_fgv._conectar()
    nome = config.GOOGLE_SHEETS_WORKSHEET_NAME.strip()
    valores = [cabecalho] + [[l[c] for c in cabecalho] for l in linhas]
    try:
        aba = planilha.worksheet(nome)
        aba.clear()
    except gspread.WorksheetNotFound:
        aba = planilha.add_worksheet(title=nome, rows=len(valores) + 50, cols=len(cabecalho))
    if aba.row_count < len(valores):
        aba.resize(rows=len(valores) + 50)
    aba.update(values=valores, range_name="A1", value_input_option="RAW")
    print(f"Aba '{nome}' atualizada com {len(linhas)} linhas.")


def main() -> None:
    argv = sys.argv[1:]
    if "--aba" in argv:  # nome da aba sem mexer no .env
        i = argv.index("--aba")
        config.GOOGLE_SHEETS_WORKSHEET_NAME = argv[i + 1]
        del argv[i : i + 2]
    args = [a for a in argv if a != "--sheets"]
    if len(args) != 1:
        sys.exit(__doc__)
    pdf = args[0]

    texto = _texto_pdf(pdf)
    if "Central de Abastecimento de Cuiabá" in texto or "CEASA/DF" in texto:
        if "CEASA/DF" in texto:
            registros, data, avisos = extrair_df(texto)
            cidade = "df"
            cabecalho, linhas, avisos_coleta = montar_coleta_mt(
                registros, data, "DF", FONTE_DF, "CEASA-DF", ALIAS_INSUMO_DF, preco_kg_df, EXCLUIR_DF
            )
        else:
            registros, data, avisos = extrair_mt(texto)
            cidade = "cuiaba"
            # a seleção é pelos Insumos (montar_coleta_mt), não pela lista do Atacadão
            cabecalho, linhas, avisos_coleta = montar_coleta_mt(registros, data)
        dia = data.replace("/", "-") or "sem-data"
        os.makedirs(os.path.join(config.BASE_DIR, "exports"), exist_ok=True)
        destino = os.path.join(config.BASE_DIR, "exports", f"ceasa_{cidade}_{dia}.csv")
        with open(destino, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cabecalho, delimiter=";")
            w.writeheader()
            w.writerows(linhas)
        print(
            f"{len(registros)} produtos no PDF; "
            f"{len(linhas)} linhas no formato Coleta -> {destino}"
        )
        for a in avisos + avisos_coleta:
            print("AVISO:", a)
        if "--sheets" in sys.argv:
            enviar_coleta_mt(linhas, cabecalho)
        return
    if "BOLETIM INFORMATIVO" in texto:
        cidade, campos = "poa", CAMPOS_POA
        registros, data, avisos = extrair_rs(texto)
    else:
        cidade, campos = "curitiba", CAMPOS_CURITIBA
        registros, data, avisos = extrair(pdf)
    itens = filtrar_lista_atacadao(registros)

    dia = data.replace("/", "-") or "sem-data"
    os.makedirs(os.path.join(config.BASE_DIR, "exports"), exist_ok=True)
    destino = os.path.join(config.BASE_DIR, "exports", f"ceasa_{cidade}_{dia}.csv")
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(itens)

    print(
        f"{len(registros)} linhas de frutas/hortaliças no PDF; "
        f"{len(itens)} na lista do Atacadão -> {destino}"
    )
    for a in avisos:
        print("AVISO:", a)

    if "--sheets" in sys.argv:
        enviar_para_sheets(itens, campos)


if __name__ == "__main__":
    main()
