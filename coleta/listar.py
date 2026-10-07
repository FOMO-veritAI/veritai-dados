"""Monta manifestos (JSONL) com os documentos de cada fonte da lista curada.

Uso (com o ambiente do repositório veritai):
    python coleta/listar.py ibge --quantidade 300
    python coleta/listar.py agencia-brasil
    python coleta/listar.py agencia-gov --quantidade 100
    python coleta/listar.py inep --quantidade 100

Cada linha do manifesto tem url, fonte, titulo e data (AAAA-MM-DD ou null); a API do
IBGE já traz o texto, que vai em "texto". Os manifestos ficam em saida/manifestos/,
fora do git. As fontes, licenças e restrições estão em fontes/fontes.md.
"""

import argparse
import gzip
import json
import re
import time
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import httpx

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "saida" / "manifestos"
CABECALHOS = {"User-Agent": "VeritAI/0.1 (local research prototype)"}

EDITORIAS_AGENCIA_BRASIL = ["economia", "saude", "educacao", "politica", "geral", "direitos-humanos", "justica", "internacional", "meio-ambiente"]


def obter(cliente: httpx.Client, url: str, espera: float) -> httpx.Response:
    # Uma requisição por vez, com intervalo fixo: respeita o Crawl-delay de cada site.
    time.sleep(espera)
    resposta = cliente.get(url)
    resposta.raise_for_status()
    return resposta


def ibge(cliente: httpx.Client, quantidade: int) -> list[dict]:
    """Releases da API pública de notícias do IBGE (a página da agência bloqueia acesso automatizado)."""
    itens, pagina = [], 1
    while len(itens) < quantidade:
        url = f"https://servicodados.ibge.gov.br/api/v3/noticias/?tipo=release&qtd=100&page={pagina}"
        dados = obter(cliente, url, 1).json()
        for item in dados["items"]:
            introducao = re.sub(r"\s*\.\.\.$", "", item["introducao"].strip())
            itens.append({
                "url": item["link"].replace("http://", "https://", 1),
                "fonte": "IBGE - Agência de Notícias (API de notícias)",
                "titulo": item["titulo"].strip(),
                "data": datetime.strptime(item["data_publicacao"], "%d/%m/%Y %H:%M:%S").date().isoformat(),
                "texto": f"{item['titulo'].strip()}. {introducao}",
            })
        if not dados.get("nextPage") or pagina >= dados["totalPages"]:
            break
        pagina += 1
    return itens[:quantidade]


def agencia_brasil(cliente: httpx.Client, quantidade: int) -> list[dict]:
    """Últimas matérias de cada editoria pelos feeds RSS (o robots.txt pede 10 s entre requisições)."""
    itens: dict[str, dict] = {}
    for editoria in EDITORIAS_AGENCIA_BRASIL:
        raiz = ElementTree.fromstring(obter(cliente, f"https://agenciabrasil.ebc.com.br/rss/{editoria}/feed.xml", 10).content)
        for item in raiz.findall("./channel/item"):
            url = (item.findtext("link") or "").strip()
            if "/noticia/" not in url or url in itens:
                continue
            data = item.findtext("pubDate")
            itens[url] = {
                "url": url,
                "fonte": "Agência Brasil (EBC)",
                "titulo": (item.findtext("title") or "").strip(),
                "data": parsedate_to_datetime(data).date().isoformat() if data else None,
            }
    return list(itens.values())[:quantidade]


def agencia_gov(cliente: httpx.Client, quantidade: int) -> list[dict]:
    """Notícias mais recentes do sitemap (o robots.txt proíbe URLs com "?", então nada de busca)."""
    xml = gzip.decompress(obter(cliente, "https://agenciagov.ebc.com.br/sitemap.xml.gz", 1).content)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    entradas = []
    for url in ElementTree.fromstring(xml).findall("s:url", ns):
        loc = url.findtext("s:loc", namespaces=ns) or ""
        # Só páginas de notícia; imagens e anexos do mesmo caminho têm extensão.
        if re.search(r"/noticias/\d{6}/[^/.]+$", loc):
            entradas.append((url.findtext("s:lastmod", namespaces=ns) or "", loc))
    entradas.sort(reverse=True)
    # A data de publicação vem da própria página (DC.date.valid_range); lastmod é data de alteração.
    return [{"url": loc, "fonte": "Agência Gov (EBC)", "titulo": "", "data": None} for _, loc in entradas[:quantidade]]


def inep(cliente: httpx.Client, quantidade: int) -> list[dict]:
    """Notícias listadas nas páginas de categoria do INEP (gov.br não publica sitemap para o INEP)."""
    base = "https://www.gov.br/inep/pt-br/centrais-de-conteudo/noticias"
    indice = obter(cliente, base, 2).text
    categorias = list(dict.fromkeys(re.findall(rf'href="({re.escape(base)}/[a-z0-9-]+)/?"', indice)))
    urls: list[str] = []
    for categoria in categorias:
        html = obter(cliente, categoria, 2).text
        for link in re.findall(rf'href="({re.escape(categoria)}/[a-z0-9-]+)"', html):
            if link not in urls:
                urls.append(link)
    # Distribui a cota entre as categorias, para não ficar só com a primeira.
    por_categoria: dict[str, list[str]] = {}
    for url in urls:
        por_categoria.setdefault(url.rsplit("/", 1)[0], []).append(url)
    escolhidas: list[str] = []
    while len(escolhidas) < quantidade and any(por_categoria.values()):
        for lista in por_categoria.values():
            if lista and len(escolhidas) < quantidade:
                escolhidas.append(lista.pop(0))
    return [{"url": url, "fonte": "INEP (gov.br)", "titulo": "", "data": None} for url in escolhidas]


FONTES = {"ibge": ibge, "agencia-brasil": agencia_brasil, "agencia-gov": agencia_gov, "inep": inep}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fonte", choices=FONTES)
    parser.add_argument("--quantidade", type=int, default=100)
    args = parser.parse_args()
    with httpx.Client(timeout=30, headers=CABECALHOS, follow_redirects=False) as cliente:
        itens = FONTES[args.fonte](cliente, args.quantidade)
    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / f"{args.fonte}-{datetime.now():%Y%m%dT%H%M%S}.jsonl"
    destino.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in itens), encoding="utf-8")
    dominios = sorted({urlparse(item["url"]).hostname for item in itens})
    print(f"{len(itens)} documento(s) de {', '.join(dominios)} em {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
