"""Carrega manifestos de saida/manifestos/ na base própria da VeritAI.

Uso (com o ambiente do repositório veritai):
    python coleta/carregar.py saida/manifestos/ibge-*.jsonl [--base caminho.sqlite3]

Usa a carga da própria VeritAI (veritai.base.importar.importar_urls): lotes de no
máximo base.max_urls_por_carga URLs, uma página por vez, com a checagem de URL
pública e o limite de tamanho do serviço. Itens com "texto" no manifesto (API do
IBGE) não são baixados de novo. Depois da carga, rode:
    python -m veritai.base indexar --perfil v0   (e --perfil v1)
"""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from veritai.base import importar
from veritai.config import BASE, caminho_base
from veritai.fontes import Fonte, ler_pagina

# Intervalo mínimo entre requisições ao mesmo domínio, em segundos (Crawl-delay do robots.txt quando existe).
INTERVALO = {"agenciabrasil.ebc.com.br": 10}
INTERVALO_PADRAO = 2


def criar_leitor(itens: dict[str, dict], sem_data: list[str]):
    ultima: dict[str, float] = {}

    async def leitor(url: str) -> Fonte:
        item = itens[url]
        dominio = urlparse(url).hostname or ""
        if item.get("texto"):
            return Fonte(url=url, titulo=item["titulo"], dominio=dominio, texto=item["texto"], origem="base_propria", data_publicacao=item.get("data"))
        espera = INTERVALO.get(dominio, INTERVALO_PADRAO) - (time.monotonic() - ultima.get(dominio, 0.0))
        if espera > 0:
            await asyncio.sleep(espera)
        ultima[dominio] = time.monotonic()
        fonte = await ler_pagina(url, origem="base_propria")
        # A data da página vale mais; a do manifesto (ex.: pubDate do RSS) só cobre a falta dela.
        fonte.data_publicacao = fonte.data_publicacao or item.get("data")
        if not fonte.data_publicacao:
            sem_data.append(url)
        return fonte

    return leitor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifestos", type=Path, nargs="+")
    parser.add_argument("--base", type=Path, default=None, help="padrão: VERITAI_BASE ou veritai/data/veritai.sqlite3")
    args = parser.parse_args()
    caminho = args.base or caminho_base()

    itens: dict[str, dict] = {}
    for manifesto in args.manifestos:
        for linha in manifesto.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                item = json.loads(linha)
                itens.setdefault(item["url"], item)
    urls = list(itens)
    tamanho = BASE["max_urls_por_carga"]
    sem_data: list[str] = []
    leitor = criar_leitor(itens, sem_data)
    total_inseridos = total_erros = 0
    print(f"Base: {caminho}; {len(urls)} URL(s) em {(len(urls) + tamanho - 1) // tamanho} lote(s).")
    for inicio in range(0, len(urls), tamanho):
        lote = urls[inicio : inicio + tamanho]
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / f"lote-{inicio // tamanho + 1}.txt"
            arquivo.write_text("\n".join(lote) + "\n", encoding="utf-8")
            resultado = importar.importar_urls(caminho, arquivo, leitor)
        total_inseridos += resultado.inseridos
        total_erros += len(resultado.erros)
        print(f"Lote {inicio // tamanho + 1}: inseridos {resultado.inseridos}, já existentes {resultado.repetidos}, erros {len(resultado.erros)}, snapshot {resultado.carga or 'sem mudança'}")
        for erro in resultado.erros:
            print(f"  Erro: {erro}", file=sys.stderr)
    if sem_data:
        print(f"{len(sem_data)} documento(s) entraram sem data de publicação.")
    print(f"Total: {total_inseridos} inserido(s), {total_erros} erro(s).")
    return 0 if not total_erros else (2 if total_inseridos else 1)


if __name__ == "__main__":
    sys.exit(main())
