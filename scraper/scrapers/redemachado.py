"""
Scraper para a Rede Machado (redemachado.com.br, "Machado Supermercados", MT).
Plataforma: Agile (e-commerce PHP, HTML renderizado no servidor; `agile_token`, `components/*.php`).
Não é o Machadão Atacadista (machadao.com.br, Osuper): são sites e plataformas diferentes.

Como o site funciona (confirmado contra o site real em 21/10/2026):
- Preço público, sem login e sem CEP/loja (loja única; `definir_cep` não faz nada). O site
  responde 403 ao Chromium headless; com Chrome real em janela (config.NAVEGADOR_CANAL =
  "chrome", HEADLESS = False) abre normal.
- Sem aceitar o banner de cookies (botão "Aceitar" na home, cookie `agile_cookie_consent`) as
  páginas de busca/categoria vêm com o layout da home e 0 produtos. O scraper aceita uma vez
  (o perfil persistente guarda o cookie).
- URLs: busca `/busca?s=<termo>` (substring: "arroz" traz também "Arrozina") e categorias
  `/horti-fruti/frutas`, `/acougue/carne-bovina`, `/c/<id>/<slug>`. Paginação `?page=N`
  (também na busca), 24 produtos por página; fim = menos de 24 itens ou sem link "Próxima
  página". Busca sem resultado devolve 0 linhas.
- A listagem tem duas visões no HTML (grade e tabela); usa-se a tabela: uma `tr.cart-table__row`
  por produto, com `a[data-nome]` (data-nome, data-preco, data-marca, href), a legenda
  `.product-card__rating-legend` ("Embalagem: ...") e `.product-card__prices`. A 1ª linha da
  tabela é o cabeçalho (sem `.product-card__prices`).
- Preço: `.product-card__new-price` ("R$ 6,99" ou "Por: R$ 6,49" em promoção, igual ao
  `data-preco`); promoção traz também `.product-card__old-price` ("De: R$ 7,99" = cheio).
  `data-marca` NÃO é marca (vem "DIVERSOS MERCEARIA SALGADA"), então a marca sai do nome.
- Embalagem: "Embalagem: KG" = vendido por peso, preço já é por kg (grava 1 kg); "Embalagem:
  1X1 500GR" / "1X1 1LT" / "1X1 24UN" = preço da embalagem com esse conteúdo (o prefixo foi 1X1
  em todos os 548 itens vistos; usa-se o tamanho). Formato fora disso (ex.: "1X1 200/5GR") cai
  no parser genérico do nome. Sem preço atacado.
- Limite de ritmo: com requisições seguidas demais (dezenas por minuto) o site passa a devolver
  a home em vez da listagem, sem a mensagem de busca vazia ("Não foram encontrados produtos com
  os termos da busca"); a sessão volta ao normal depois de alguns minutos parada. Por isso há
  pausa mínima entre páginas (PAUSA_MINIMA_ENTRE_PAGINAS_MS) e, na falha, espera crescente +
  reinício da sessão do site (apaga os cookies do site, um a um com o domínio exato, e aceita os
  cookies de novo; `clear_cookies(domain=...)` compara o domínio inteiro, então "redemachado.com.br"
  não apaga os cookies de "www.redemachado.com.br"). O cookie `aws-waf-token` é preservado:
  apagá-lo descarta o desafio de verificação humana já resolvido e o WAF pede de novo.
- Às vezes o WAF mostra um desafio de verificação humana no lugar da página (sem o campo de
  busca do site). O scraper não tenta resolver: avisa no log e espera até 5 min para a pessoa
  resolver na janela do navegador (por isso a coleta completa deve rodar com alguém por perto
  na 1ª vez; o token resolvido fica no perfil).
- Checkpoint: cada tarefa concluída (inclusive busca realmente vazia) é gravada em
  logs/cache_redemachado_<AAAA-MM-DD>.json. Na 1ª tarefa que falhar de vez a coleta é pausada: as
  demais tarefas da execução são puladas na hora (log "PENDENTE") em vez de insistir contra o
  limite do site. Reexecutar `main.py` retoma do que falta (as concluídas saem do checkpoint, sem
  abrir o site). Só quando nenhuma ficar PENDENTE vale enviar à planilha. O checkpoint é do dia:
  no dia seguinte a coleta recomeça do zero. Apague o arquivo para forçar recoleta.
- Dedupe por `data-id-produto` dentro da tarefa e entre as tarefas da execução (o scraper.py
  cria uma instância por tarefa, então o controle fica na classe).
"""

import json
import logging
import os
import re
import time
from dataclasses import asdict
from datetime import date
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup

import config as config
from database import Produto
from scrapers.base import BaseScraper
from utils.parsers import extrair_quantidade_e_unidade, extrair_marca, parse_preco

logger = logging.getLogger(__name__)

BASE_URL = "https://www.redemachado.com.br"
ITENS_POR_PAGINA = 24
MAX_PAGINAS_SEGURANCA = 30
ESPERA_LINHAS_MS = 15_000
TENTATIVAS_POR_PAGINA = 3
PAUSA_ENTRE_TENTATIVAS_MS = 30_000  # x nº da tentativa
PAUSA_MINIMA_ENTRE_PAGINAS_MS = 4_000
ESPERA_DESAFIO_MS = 300_000
TEXTO_BUSCA_VAZIA = "Não foram encontrados produtos"

_REGEX_EMBALAGEM = re.compile(
    r"^Embalagem:\s*\d+X\d+\s+(?P<qtd>\d+[.,]?\d*)\s*(?P<unid>KG|GR|G|ML|LT|L|UN)\s*$",
    re.IGNORECASE,
)
_UNIDADES = {"kg": "kg", "gr": "g", "g": "g", "ml": "ml", "lt": "L", "l": "L", "un": "un"}


class RedeMachadoScraper(BaseScraper):
    nome_fornecedor = "redemachado"

    SEL_LINHA = "tr.cart-table__row"
    SEL_LINK = "a[data-nome]"
    SEL_PRECOS = ".product-card__prices"
    SEL_PRECO_ATUAL = ".product-card__new-price"
    SEL_PRECO_ANTIGO = ".product-card__old-price"
    SEL_EMBALAGEM = ".product-card__rating-legend"

    # Em nível de classe: o dedupe e o ritmo valem para a execução inteira (uma instância por tarefa).
    _ja_coletados: set = set()  # data-id-produto já devolvido nesta execução
    _ultima_navegacao: float = 0.0
    _interrompida: bool = False  # uma tarefa falhou de vez: pula as demais desta execução
    _checkpoint: Optional[dict] = None  # {chave da tarefa: {"produtos": [...], "ids": [...]}}

    @staticmethod
    def _url_pagina(url: str, pagina: int) -> str:
        partes = urlsplit(url)
        query = [(k, v) for k, v in parse_qsl(partes.query) if k != "page"]
        if pagina > 1:
            query.append(("page", str(pagina)))
        return urlunsplit(partes._replace(query=urlencode(query)))

    @staticmethod
    def _quantidade(embalagem: str, nome: str) -> tuple[Optional[float], Optional[str]]:
        if re.match(r"^Embalagem:\s*KG\s*$", embalagem, re.IGNORECASE):
            return 1.0, "kg"  # vendido por peso: preço já é por kg
        m = _REGEX_EMBALAGEM.match(embalagem)
        if m:
            return float(m.group("qtd").replace(",", ".")), _UNIDADES[m.group("unid").lower()]
        return extrair_quantidade_e_unidade(nome)

    def _extrair_linha(self, linha, categoria: str) -> Optional[tuple[str, Produto]]:
        link = linha.select_one(self.SEL_LINK)
        el_preco = linha.select_one(self.SEL_PRECO_ATUAL)
        if not link or not el_preco:
            return None
        nome = (link.get("data-nome") or "").strip()
        preco = parse_preco(el_preco.get_text(" ", strip=True))
        if not nome or not preco or preco <= 0:
            return None

        preco_original = desconto = None
        el_antigo = linha.select_one(self.SEL_PRECO_ANTIGO)
        antigo = parse_preco(el_antigo.get_text(" ", strip=True)) if el_antigo else None
        if antigo and antigo > preco:
            preco_original = antigo
            desconto = f"-{round((1 - preco / antigo) * 100)}%"

        el_emb = linha.select_one(self.SEL_EMBALAGEM)
        embalagem = el_emb.get_text(" ", strip=True) if el_emb else ""
        quantidade, unidade = self._quantidade(embalagem, nome)

        return link.get("data-id-produto") or link.get("href"), Produto(
            fornecedor=self.nome_fornecedor,
            categoria=categoria,
            nome=nome,
            marca=extrair_marca(nome),
            preco=preco,
            quantidade=quantidade,
            unidade=unidade,
            preco_original=preco_original,
            desconto=desconto,
            url_produto=link.get("href"),
        )

    def _salvar_debug_pagina_vazia(self, categoria: str) -> None:
        logs_dir = os.path.join(config.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        nome = re.sub(r"[^\w-]", "_", categoria)
        caminho = os.path.join(logs_dir, f"debug_vazio_{nome}.html")
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.page.content())
        logger.error("0 produtos em '%s' (Rede Machado). HTML salvo em %s", categoria, caminho)

    def _garantir_consentimento_de_cookies(self, forcar: bool = False) -> None:
        cookies = self.page.context.cookies(BASE_URL)
        if not forcar and any(c["name"] == "agile_cookie_consent" for c in cookies):
            return
        self.page.goto(BASE_URL, timeout=config.NAV_TIMEOUT_MS, wait_until="domcontentloaded")
        try:
            self.page.get_by_text("Aceitar", exact=True).click(timeout=8000)
            self.page.wait_for_timeout(1500)
            logger.info("Rede Machado: cookies aceitos (necessário para listar produtos).")
        except Exception:
            logger.warning("Rede Machado: banner de cookies não encontrado/clicável.")

    def _esperar_listagem(self, timeout_ms: int) -> str:
        """Espera as linhas de produto ou a mensagem de busca vazia: "ok" ou "vazio"."""
        self.page.wait_for_function(
            """([sel, texto]) => document.querySelector(sel)
                || document.body.innerText.includes(texto)""",
            arg=[f"{self.SEL_LINHA} {self.SEL_PRECOS}", TEXTO_BUSCA_VAZIA],
            timeout=timeout_ms,
        )
        return "ok" if self.page.query_selector(f"{self.SEL_LINHA} {self.SEL_PRECOS}") else "vazio"

    def _reiniciar_sessao_do_site(self) -> None:
        """Apaga os cookies do domínio, menos o do WAF, e aceita os cookies de novo."""
        contexto = self.page.context
        for c in contexto.cookies(BASE_URL):
            if not c["name"].startswith("aws-waf"):
                contexto.clear_cookies(name=c["name"], domain=c["domain"])
        self._garantir_consentimento_de_cookies(forcar=True)

    def _respeitar_ritmo(self) -> None:
        cls = type(self)
        faltam_ms = PAUSA_MINIMA_ENTRE_PAGINAS_MS - (time.monotonic() - cls._ultima_navegacao) * 1000
        if faltam_ms > 0:
            self.page.wait_for_timeout(faltam_ms)
        cls._ultima_navegacao = time.monotonic()

    def _carregar_pagina(self, url: str) -> str:
        """Abre `url` e devolve "ok" (há produtos), "vazio" (busca sem resultado) ou "falha"."""
        for tentativa in range(1, TENTATIVAS_POR_PAGINA + 1):
            self._respeitar_ritmo()
            self.page.goto(url, timeout=config.NAV_TIMEOUT_MS, wait_until="domcontentloaded")
            try:
                return self._esperar_listagem(ESPERA_LINHAS_MS)
            except Exception:
                if not self.page.query_selector("input.search__input"):
                    logger.warning(
                        "Rede Machado: desafio de verificação humana? Resolva na janela do "
                        "navegador (aguardando até %d min): %s",
                        ESPERA_DESAFIO_MS // 60_000,
                        url,
                    )
                    try:
                        return self._esperar_listagem(ESPERA_DESAFIO_MS)
                    except Exception:
                        pass
                logger.warning(
                    "Rede Machado: página sem listagem (tentativa %d/%d): %s",
                    tentativa,
                    TENTATIVAS_POR_PAGINA,
                    url,
                )
                self.page.wait_for_timeout(PAUSA_ENTRE_TENTATIVAS_MS * tentativa)
                self._reiniciar_sessao_do_site()
        return "falha"

    @staticmethod
    def _arquivo_checkpoint() -> str:
        return os.path.join(config.BASE_DIR, "logs", f"cache_redemachado_{date.today()}.json")

    @classmethod
    def _tarefas_concluidas(cls) -> dict:
        if cls._checkpoint is None:
            try:
                with open(cls._arquivo_checkpoint(), encoding="utf-8") as f:
                    cls._checkpoint = json.load(f)
            except (OSError, ValueError):
                cls._checkpoint = {}
        return cls._checkpoint

    @classmethod
    def _gravar_checkpoint(cls, chave: str, produtos: list[Produto], ids: list[str]) -> None:
        cls._tarefas_concluidas()[chave] = {"produtos": [asdict(p) for p in produtos], "ids": ids}
        caminho = cls._arquivo_checkpoint()
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(cls._checkpoint, f, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)

    def definir_cep(self, cep: str) -> None:
        logger.info("Rede Machado: loja única, sem CEP — nada a definir.")

    def extrair_produtos_da_pagina(
        self, categoria: str, url: str, palavras_chave: Optional[list[str]] = None
    ) -> list[Produto]:
        cls = type(self)
        chave = f"{categoria}|{url}|{sorted(palavras_chave or [])}"
        concluida = cls._tarefas_concluidas().get(chave)
        if concluida:
            cls._ja_coletados.update(concluida["ids"])
            logger.info(
                "Categoria '%s' -> %s (Rede Machado): %d produtos do checkpoint.",
                categoria,
                url,
                len(concluida["produtos"]),
            )
            return [Produto(**d) for d in concluida["produtos"]]
        if cls._interrompida:
            logger.warning("PENDENTE (coleta pausada pelo limite do site): '%s' -> %s", categoria, url)
            return []

        logger.info("Coletando categoria '%s' -> %s (Rede Machado)", categoria, url)
        produtos: list[Produto] = []
        ids_coletados: list[str] = []
        vistos: set = set()
        sem_preco = fora_do_filtro = 0
        falhou = False
        e_busca = "/busca" in url

        try:
            self._garantir_consentimento_de_cookies()
            for pagina in range(1, MAX_PAGINAS_SEGURANCA + 1):
                situacao = self._carregar_pagina(self._url_pagina(url, pagina))
                if situacao == "falha":
                    logger.error("Rede Machado: '%s' sem listagem após retentativas.", url)
                    falhou = True
                    break
                if situacao == "vazio":
                    break

                soup = BeautifulSoup(self.page.content(), "html.parser")
                linhas = [l for l in soup.select(self.SEL_LINHA) if l.select_one(self.SEL_PRECOS)]
                novos = 0
                for linha in linhas:
                    resultado = self._extrair_linha(linha, categoria)
                    if resultado is None:
                        sem_preco += 1
                        continue
                    id_produto, produto = resultado
                    if id_produto in vistos or id_produto in cls._ja_coletados:
                        continue
                    vistos.add(id_produto)
                    novos += 1
                    if palavras_chave and not any(
                        pk.lower() in produto.nome.lower() for pk in palavras_chave
                    ):
                        fora_do_filtro += 1
                        continue
                    cls._ja_coletados.add(id_produto)
                    ids_coletados.append(id_produto)
                    produtos.append(produto)

                if len(linhas) < ITENS_POR_PAGINA or not soup.find("a", string=re.compile("Próxima")):
                    break
                if novos == 0:
                    break  # página repetida
        except Exception:
            logger.exception("Erro ao processar categoria '%s' (Rede Machado)", categoria)
            falhou = True

        logger.info(
            "Categoria '%s' (Rede Machado): %d extraídos, %d sem preço, %d fora do filtro.",
            categoria,
            len(produtos),
            sem_preco,
            fora_do_filtro,
        )
        if falhou:
            cls._interrompida = True
            logger.error("PENDENTE (limite do site): '%s' -> %s. Coleta pausada.", categoria, url)
        else:
            try:
                cls._gravar_checkpoint(chave, produtos, ids_coletados)
            except Exception:
                logger.exception("Falha ao gravar o checkpoint (Rede Machado)")
        if not produtos and (falhou or not e_busca):
            try:
                self._salvar_debug_pagina_vazia(categoria)
            except Exception:
                logger.exception("Falha ao salvar HTML de debug (Rede Machado)")
        return produtos
