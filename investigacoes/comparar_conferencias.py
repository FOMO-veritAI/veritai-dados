"""Compara a conferência humana do conjunto de notícias reais com a da IA e com o resultado da VeritAI.

Uso, a partir de veritai-dados/, depois de preencher a coluna de rótulo em rotulos/noticias-reais-v0/conferencia.csv:
    python investigacoes/comparar_conferencias.py

Mostra a concordância (porcentagem e kappa de Cohen) entre os pares: humano × IA, humano × VeritAI e IA × VeritAI,
com a matriz de confusão e a lista das divergências. Tomando a conferência humana como referência, mostra também as
métricas da VeritAI (acerto, falsas aprovações, falsas refutações).
"""

import csv
import json
from collections import Counter
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1] / "rotulos" / "noticias-reais-v0"
CLASSES = {"apoiada": "SUPPORTED", "refutada": "REFUTED", "insuficiente": "NOT_ENOUGH_EVIDENCE", "conflitante": "CONFLICTING_EVIDENCE"}
CURTO = {"SUPPORTED": "S", "REFUTED": "R", "NOT_ENOUGH_EVIDENCE": "NEE", "CONFLICTING_EVIDENCE": "CE"}


def ler_csv(nome: str, coluna: str) -> dict[str, str]:
    with (PASTA / nome).open(encoding="utf-8-sig") as arquivo:
        linhas = list(csv.DictReader(arquivo))
    rotulos = {}
    for linha in linhas:
        valor = (linha.get(coluna) or "").strip().lower()
        if valor:
            if valor not in CLASSES:
                raise ValueError(f"{nome}, {linha['id']}: rótulo {valor!r} fora de {sorted(CLASSES)}.")
            rotulos[linha["id"]] = CLASSES[valor]
    return rotulos


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    observada = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    esperada = sum(ca[c] * cb[c] for c in set(a) | set(b)) / (n * n)
    return (observada - esperada) / (1 - esperada) if esperada < 1 else 1.0


def comparar(nome_a: str, a: dict, nome_b: str, b: dict, afirmacoes: dict) -> None:
    ids = sorted(set(a) & set(b))
    if not ids:
        print(f"\n{nome_a} × {nome_b}: nenhum item em comum.")
        return
    xa, xb = [a[i] for i in ids], [b[i] for i in ids]
    concordancia = sum(x == y for x, y in zip(xa, xb)) / len(ids)
    print(f"\n{nome_a} × {nome_b}: {len(ids)} itens; concordância {concordancia:.1%}; kappa {kappa(xa, xb):.2f}")
    print(f"  matriz (linha = {nome_a}, coluna = {nome_b}): " + "; ".join(f"{CURTO[x]}→{CURTO[y]} {n}" for (x, y), n in sorted(Counter(zip(xa, xb)).items())))
    for i in ids:
        if a[i] != b[i]:
            print(f"  {i}: {nome_a} {CURTO[a[i]]}, {nome_b} {CURTO[b[i]]} | {afirmacoes[i][:110]}")


def main() -> None:
    humano = ler_csv("conferencia.csv", "rotulo (apoiada/refutada/insuficiente/conflitante)")
    ia = ler_csv("conferencia-ia.csv", "rotulo")
    predicoes = [json.loads(l) for l in (PASTA / "predicoes-veritai.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    veritai = {p["id"]: p["resultado"] for p in predicoes}
    afirmacoes = {p["id"]: p["afirmacao"] for p in predicoes}
    print(f"Rótulos: humano {len(humano)}, IA {len(ia)}, VeritAI {len(veritai)}")
    for nome, rotulos in (("humano", humano), ("IA", ia), ("VeritAI", veritai)):
        print(f"  {nome}: {dict(Counter(CURTO[r] for r in rotulos.values()))}")
    comparar("humano", humano, "IA", ia, afirmacoes)
    comparar("humano", humano, "VeritAI", veritai, afirmacoes)
    comparar("IA", ia, "VeritAI", veritai, afirmacoes)
    if humano:
        ids = sorted(set(humano) & set(veritai))
        negativos = [i for i in ids if humano[i] != "SUPPORTED"]
        apoiadas = [i for i in ids if humano[i] == "SUPPORTED"]
        print("\nVeritAI com a conferência humana como referência:")
        print(f"  acerto {sum(humano[i] == veritai[i] for i in ids) / len(ids):.1%}")
        if negativos:
            print(f"  falsas aprovações {sum(veritai[i] == 'SUPPORTED' for i in negativos) / len(negativos):.1%} ({len(negativos)} itens não apoiados)")
        if apoiadas:
            print(f"  falsas refutações {sum(veritai[i] == 'REFUTED' for i in apoiadas) / len(apoiadas):.1%} ({len(apoiadas)} itens apoiados)")


if __name__ == "__main__":
    main()
