"""Quebra as predições de eval/avaliar.py no AVeriTeC por classe, tipo de alegação e estratégia.

Uso: python averitec/analisar.py saida/averitec/dev.jsonl predicoes.jsonl [outras_predicoes.jsonl ...]

Mostra onde a VeritAI erra; não é medição de desempenho (veja converter.py).
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

CLASSES = ["SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE", "CONFLICTING_EVIDENCE"]
CURTO = {"SUPPORTED": "S", "REFUTED": "R", "NOT_ENOUGH_EVIDENCE": "NEE", "CONFLICTING_EVIDENCE": "CE"}


def ler(caminho: str) -> dict[str, dict]:
    return {d["id"]: d for d in map(json.loads, Path(caminho).read_text(encoding="utf-8").splitlines()) if d}


def quebra(itens: dict, preditos: dict, chave: str, minimo: int = 15) -> list[str]:
    grupos = defaultdict(list)
    for i, item in itens.items():
        for valor in item[chave]:
            grupos[valor].append((item["rotulo"], preditos[i]["predito"]))
    linhas = []
    for valor, pares in sorted(grupos.items(), key=lambda g: -len(g[1])):
        if len(pares) < minimo:
            continue
        acerto = sum(r == p for r, p in pares) / len(pares)
        aprov = [p for r, p in pares if r != "SUPPORTED"]
        fa = sum(p == "SUPPORTED" for p in aprov) / len(aprov) if aprov else float("nan")
        dist = Counter(CURTO[p] for _, p in pares)
        linhas.append(f"  {valor[:38]:<38} n={len(pares):>3}  acerto {acerto:.2f}  falsas aprov. {fa:.2f}  preditos {dict(dist)}")
    return linhas


def main() -> None:
    itens = ler(sys.argv[1])
    for caminho in sys.argv[2:]:
        preditos = ler(caminho)
        print(f"== {Path(caminho).stem}")
        print("  Distribuição das predições:", dict(Counter(CURTO[p["predito"]] for p in preditos.values())))
        for classe in CLASSES:
            dessa = [i for i in itens if itens[i]["rotulo"] == classe]
            print(f"  {classe:<22} n={len(dessa):>3}  recall {sum(preditos[i]['predito'] == classe for i in dessa) / len(dessa):.2f}"
                  f"  preditos {dict(Counter(CURTO[preditos[i]['predito']] for i in dessa))}")
        print(" Por tipo de alegação:")
        print("\n".join(quebra(itens, preditos, "tipos")))
        print(" Por estratégia de checagem:")
        print("\n".join(quebra(itens, preditos, "estrategias")))


if __name__ == "__main__":
    main()
