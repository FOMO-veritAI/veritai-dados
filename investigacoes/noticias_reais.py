"""Conjunto de notícias reais de ponta a ponta: afirmações extraídas de notícias da base, analisadas pela VeritAI.

Uso, a partir de veritai-dados/, com o ambiente do repositório veritai:
    ../veritai/.venv/bin/python investigacoes/noticias_reais.py [--perfil v1]

Afirmações: as candidatas da amostra de extração (rotulos/extracao-v0/) que a pré-rotulagem marcou como
verificáveis e com um fato só; usa a versão corrigida (compreensível sozinha) quando existe. É o que o
publicador confirmaria depois do /extrair.

Análise: o pipeline da VeritAI com a base própria, sem web, com a data da notícia. A própria notícia de
origem e as cópias dela saem da busca: no FOMO, a notícia ainda não foi publicada quando é analisada.

Saídas em rotulos/noticias-reais-v0/:
- conferencia.csv: afirmação e evidências mostradas pela VeritAI, **sem o resultado dela**, para a
  conferência cega (humana ou por IA): qual deveria ser o resultado, dadas essas evidências?
- predicoes-veritai.jsonl: o resultado e as evidências com a relação atribuída (não abra antes de conferir).
"""

import argparse
import asyncio
import csv
import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "veritai"))

from veritai.base import BaseEvidencias  # noqa: E402
from veritai.config import BASE, caminho_base, perfil, versoes  # noqa: E402
from veritai.modelos import ComparadorNLI  # noqa: E402
from veritai.pipeline import analisar  # noqa: E402
from veritai.relatorio import PedidoAnalise  # noqa: E402

PASTA = RAIZ / "rotulos" / "noticias-reais-v0"
excluir: dict = {"url": None, "grupo": None}
buscar_original = BaseEvidencias.buscar


def buscar_sem_origem(self, afirmacao, ate=None):
    """Busca da base sem a notícia de origem nem suas cópias (pede o dobro de trechos para compensar)."""
    padrao = BASE["trechos_por_busca"]
    BASE["trechos_por_busca"] = 2 * padrao
    try:
        fontes = buscar_original(self, afirmacao, ate)
    finally:
        BASE["trechos_por_busca"] = padrao
    return [f for f in fontes if f.url != excluir["url"] and f.copia_de != excluir["grupo"]][:padrao]


def afirmacoes() -> list[dict]:
    with (RAIZ / "rotulos" / "extracao-v0" / "pre-rotulos-ia.csv").open(encoding="utf-8-sig") as arquivo:
        pre = list(csv.DictReader(arquivo))
    with (RAIZ / "rotulos" / "extracao-v0" / "anotacao.csv").open(encoding="utf-8-sig") as arquivo:
        origem = list(csv.DictReader(arquivo))
    itens = []
    for indice, (p, o) in enumerate(zip(pre, origem)):
        if p["afirmacao_proposta"] != o["afirmacao_proposta"]:
            raise ValueError(f"Linha {indice}: pré-rótulos e amostra desalinhados.")
        if p["verificavel (s/n)"] != "s" or p["atomica (s/n)"] != "s":
            continue
        texto = (p["afirmacao_corrigida"] or p["afirmacao_proposta"]).strip()
        if not 10 <= len(texto) <= 500:
            continue
        itens.append({"id": f"nr-{indice:03d}", "afirmacao": texto, "corrigida": bool(p["afirmacao_corrigida"]),
                      "doc_id": int(o["doc_id"]), "url_noticia": o["url"], "titulo_noticia": o["titulo"], "data": o["data"]})
    return itens


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--perfil", default="v1")
    args = parser.parse_args()
    itens = afirmacoes()
    comparador = ComparadorNLI(args.perfil)
    base = BaseEvidencias(caminho_base(), perfil(args.perfil)["embedding"], comparador.modelos.vetorizar, args.perfil)
    base.verificar_indice()
    with sqlite3.connect(f"file:{caminho_base()}?mode=ro", uri=True) as conexao:
        grupo_de = dict(conexao.execute("SELECT id, grupo_copias FROM documentos").fetchall())
    BaseEvidencias.buscar = buscar_sem_origem
    predicoes = []
    try:
        for item in itens:
            excluir.update(url=item["url_noticia"], grupo=f"base:{grupo_de[item['doc_id']]}")
            pedido = PedidoAnalise(noticia={"titulo": item["titulo_noticia"], "data": item["data"]}, afirmacoes=[item["afirmacao"]], buscar_na_web=False)
            analise = asyncio.run(analisar(pedido, comparador, base=base)).afirmacoes[0]
            predicoes.append({**item, "resultado": analise.resultado, "evidencias": [e.model_dump() for e in analise.evidencias]})
    finally:
        BaseEvidencias.buscar = buscar_original

    PASTA.mkdir(parents=True, exist_ok=True)
    (PASTA / "predicoes-veritai.jsonl").write_text(
        "".join(json.dumps({**p, "versoes": versoes(args.perfil)}, ensure_ascii=False) + "\n" for p in predicoes), encoding="utf-8"
    )
    with (PASTA / "conferencia.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["id", "data_noticia", "afirmacao", "evidencias", "rotulo (apoiada/refutada/insuficiente/conflitante)", "observacao", "anotador"])
        for p in predicoes:
            # Cada evidência uma vez, sem a relação atribuída pela VeritAI.
            vistas, linhas = set(), []
            for e in p["evidencias"]:
                if (e["fonte"], e["trecho"]) in vistas:
                    continue
                vistas.add((e["fonte"], e["trecho"]))
                linhas.append(f"[{len(linhas) + 1}] {e['fonte']} ({e['data_publicacao'] or 'sem data'}): {e['trecho']}")
            escritor.writerow([p["id"], p["data"], p["afirmacao"], "\n".join(linhas) or "(nenhuma evidência encontrada)", "", "", ""])
    # Os resultados não são impressos: a conferência é cega.
    print(f"{len(predicoes)} afirmações ({sum(p['corrigida'] for p in predicoes)} na versão corrigida)")
    print(f"Saídas em {PASTA.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
