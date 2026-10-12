"""Aplica o mapeamento de vereditos (mapeamento/vereditos.csv) às checagens da base própria.

Uso (com o ambiente do repositório veritai):
    python mapeamento/aplicar.py [--base caminho.sqlite3]

Só lê a base: o esquema da VeritAI guarda apenas o veredito original. Gera
saida/checagens-mapeadas.csv para a revisão manual e lista os vereditos sem
mapeamento, que precisam entrar no CSV antes da próxima rodada.
"""

import argparse
import csv
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from veritai.config import caminho_base

RAIZ = Path(__file__).resolve().parents[1]


def normalizar(veredito: str) -> str:
    """Minúsculas, sem acentos e sem pontuação; o que vem depois de ":" (explicação da agência) é descartado."""
    texto = veredito.split(":", 1)[0]
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", texto)).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=None)
    args = parser.parse_args()
    with (RAIZ / "mapeamento" / "vereditos.csv").open(encoding="utf-8") as arquivo:
        mapa = {linha["veredito_normalizado"]: linha for linha in csv.DictReader(arquivo)}

    conexao = sqlite3.connect(f"file:{args.base or caminho_base()}?mode=ro", uri=True)
    linhas = conexao.execute("SELECT id, agencia, data, url, alegacao, veredito_original FROM checagens ORDER BY id").fetchall()
    saida = RAIZ / "saida" / "checagens-mapeadas.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    classes, sem_mapa = Counter(), Counter()
    with saida.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["id", "agencia", "data", "veredito_original", "classe_proposta", "revisar", "classe_revisada", "alegacao", "url"])
        for id_, agencia, data, url, alegacao, veredito in linhas:
            regra = mapa.get(normalizar(veredito))
            if regra is None:
                sem_mapa[veredito] += 1
            classe = regra["classe"] if regra else ""
            classes[classe or "(sem mapeamento)"] += 1
            escritor.writerow([id_, agencia, data or "", veredito, classe, regra["revisar"] if regra else "sim", "", alegacao, url])
    print(f"{len(linhas)} checagem(ns) em {saida.relative_to(RAIZ)}")
    for classe, total in classes.most_common():
        print(f"  {classe}: {total}")
    for veredito, total in sem_mapa.most_common():
        print(f"  sem mapeamento: {veredito!r} ({total})")


if __name__ == "__main__":
    main()
