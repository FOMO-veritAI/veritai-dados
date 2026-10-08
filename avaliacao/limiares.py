"""Estudo dos limiares de "forte" (similaridade e NLI) sobre os trechos salvos pela bateria, sem rodar modelos.

Uso, a partir de veritai-dados/:
    python avaliacao/limiares.py saida/bateria/<pasta> [--perfil v1] [--config padrao]

Protocolo: os limiares são escolhidos só no conjunto de desenvolvimento dos releases ("dev"). Critério:
maior macro-F1 sem aumentar as falsas aprovações em relação aos limiares atuais; no empate, menos falsas
refutações e, depois, a combinação mais próxima da atual. A escolha é conferida uma vez na validação
("val") e nos vizinhos com busca ("viz"). O AVERITEC-BR ("avbr") aparece só como informação: já foi usado
para ajustar regras.

O limiar de seleção de janelas (similaridade_selecao) não muda aqui: mudá-lo exigiria rodar os modelos.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "veritai" / "eval"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar  # noqa: E402
from bateria import decidir  # noqa: E402

SIMILARIDADES = [0.0, 0.43, 0.70, 0.75, 0.78, 0.80, 0.82, 0.84, 0.86]
NLIS = [round(0.50 + 0.05 * i, 2) for i in range(10)] + [0.72]


def ler(pasta: Path, conjunto: str, perfil: str, config: str) -> list[dict] | None:
    arquivo = pasta / "predicoes" / f"{conjunto}-{perfil}-{config}.jsonl"
    return [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines() if l.strip()] if arquivo.exists() else None


def medir(predicoes: list[dict], s: float, n: float) -> tuple[float, float, float]:
    rotulos = [p["rotulo"] for p in predicoes]
    preditos = [decidir(p["trechos"], s, n) for p in predicoes]
    apoiadas = [q for r, q in zip(rotulos, preditos) if r == "SUPPORTED"]
    refutacoes = sum(q == "REFUTED" for q in apoiadas) / len(apoiadas) if apoiadas else 0.0
    return avaliar.macro_f1(rotulos, preditos), avaliar.taxa_falsas_aprovacoes(rotulos, preditos) or 0.0, refutacoes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta", type=Path)
    parser.add_argument("--perfil", default="v1")
    parser.add_argument("--config", default="padrao")
    args = parser.parse_args()
    resumo = json.loads((args.pasta / "resumo.json").read_text(encoding="utf-8"))
    atual = (resumo["limiares"]["similaridade_forte"], resumo["limiares"]["nli_forte"])
    dev = ler(args.pasta, "dev", args.perfil, args.config)
    f1_atual, aprov_atual, _ = medir(dev, *atual)

    grade = []
    for s in SIMILARIDADES:
        for n in sorted(set(NLIS)):
            f1, aprov, refut = medir(dev, s, n)
            grade.append((s, n, f1, aprov, refut))
    validos = [g for g in grade if g[3] <= aprov_atual + 1e-9]
    escolhido = max(validos, key=lambda g: (round(g[2], 6), -g[4], -abs(g[0] - atual[0]) - abs(g[1] - atual[1])))

    print(f"Perfil {args.perfil}, config {args.config}. Atual: similaridade_forte {atual[0]}, nli_forte {atual[1]} "
          f"(dev: macro-F1 {f1_atual:.3f}, falsas aprovações {aprov_atual:.1%})")
    print("\nMacro-F1 no dev (linhas: similaridade_forte; colunas: nli_forte; * = falsas aprovações acima da atual)")
    print("       " + " ".join(f"{n:>6}" for n in sorted(set(NLIS))))
    for s in SIMILARIDADES:
        celulas = []
        for n in sorted(set(NLIS)):
            g = next(x for x in grade if x[0] == s and x[1] == n)
            celulas.append(f"{g[2]:.3f}{'*' if g[3] > aprov_atual + 1e-9 else ' '}")
        print(f"  {s:<4} " + " ".join(celulas))
    print(f"\nEscolhido no dev: similaridade_forte {escolhido[0]}, nli_forte {escolhido[1]} "
          f"(macro-F1 {escolhido[2]:.3f}, falsas aprovações {escolhido[3]:.1%}, falsas refutações {escolhido[4]:.1%})")

    print("\nConferência (uma vez): atual → escolhido   [macro-F1 | falsas aprovações | falsas refutações]")
    for conjunto, papel in (("dev", "ajuste"), ("val", "conferência"), ("viz", "conferência, com busca"), ("con", "sanidade"), ("avbr", "só informação")):
        predicoes = ler(args.pasta, conjunto, args.perfil, args.config)
        if not predicoes:
            continue
        a, e = medir(predicoes, *atual), medir(predicoes, escolhido[0], escolhido[1])
        print(f"  {conjunto:<4} ({papel:<22}) {a[0]:.3f} | {a[1]:5.1%} | {a[2]:5.1%}  →  {e[0]:.3f} | {e[1]:5.1%} | {e[2]:5.1%}")


if __name__ == "__main__":
    main()
