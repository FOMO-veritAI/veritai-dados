"""Agregador treinado: regressão logística que decide a classe a partir dos trechos avaliados, no lugar das regras.

Uso, a partir de veritai-dados/, com o ambiente do repositório veritai (precisa de scikit-learn):
    ../veritai/.venv/bin/python avaliacao/agregador.py saida/bateria/<pasta> [--perfil v1] [--config padrao]

Pergunta: um agregador aprendido supera as regras explícitas (veritai/regras.py)? Nenhuma LLM decide: o
agregador só combina as notas que o embedding e o NLI já produziram (depois do verificador, na config
"padrao"; sem ele, na "sem").

Dados: os trechos salvos pela bateria. Treino em dev (releases, 65) + viz (vizinhos com busca, 140), com
validação cruzada agrupada por evento (itens do mesmo release ficam do mesmo lado). Teste, uma vez, em val
(43). Contraste e AVERITEC-BR aparecem só como informação. CONFLICTING_EVIDENCE não aparece no treino, então
o agregador nunca a prevê; isso é limite dos dados, não escolha.

Saída: saida/modelos/agregador-<perfil>-<config>.pkl (o modelo, com scikit-learn) e .json (atributos, dados de
treino, métricas e versões).
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "veritai" / "eval"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import avaliar  # noqa: E402
from bateria import CONJUNTOS, decidir  # noqa: E402

ATRIBUTOS = [
    "maior_apoio", "maior_contradicao", "maior_neutro",
    "fontes_apoio_050", "fontes_apoio_072", "fontes_contradicao_050", "fontes_contradicao_072",
    "maior_similaridade", "similaridade_media", "trechos", "fontes", "sem_trechos",
]


def atributos(trechos: list[dict]) -> list[float]:
    def maior(relacao):
        return max((t["pontuacao"] for t in trechos if t["relacao"] == relacao), default=0.0)

    def fontes(relacao, minimo):
        return float(len({t["grupo"] for t in trechos if t["relacao"] == relacao and t["pontuacao"] >= minimo}))

    similaridades = [t["similaridade"] for t in trechos]
    return [
        maior("entailment"), maior("contradiction"), maior("neutral"),
        fontes("entailment", 0.50), fontes("entailment", 0.72), fontes("contradiction", 0.50), fontes("contradiction", 0.72),
        max(similaridades, default=0.0), float(numpy.mean(similaridades)) if similaridades else 0.0,
        float(len(trechos)), float(len({t["grupo"] for t in trechos})), float(not trechos),
    ]


def ler(pasta: Path, conjunto: str, perfil: str, config: str) -> list[dict] | None:
    arquivo = pasta / "predicoes" / f"{conjunto}-{perfil}-{config}.jsonl"
    if not arquivo.exists():
        return None
    predicoes = [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Evento de cada item, para agrupar a validação cruzada.
    origem = CONJUNTOS[conjunto]
    eventos = {}
    for linha in origem.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            item = json.loads(linha)
            eventos[item.get("id")] = item.get("evento", item.get("id"))
    for p in predicoes:
        p["evento"] = eventos.get(p["id"], p["id"])
    return predicoes


def medidas(rotulos: list[str], preditos: list[str]) -> dict:
    """macro_f1 é o do avaliar.py (classes dos rótulos ou das predições): prever uma classe ausente dos rótulos
    acrescenta um F1 zero à média. macro_f1_classes_dos_rotulos usa só as classes dos rótulos e é a comparação justa."""
    apoiadas = [q for r, q in zip(rotulos, preditos) if r == "SUPPORTED"]
    return {
        "acerto": round(sum(r == q for r, q in zip(rotulos, preditos)) / len(rotulos), 3),
        "macro_f1_classes_dos_rotulos": round(float(f1_score(rotulos, preditos, labels=sorted(set(rotulos)), average="macro", zero_division=0)), 3),
        "macro_f1": round(avaliar.macro_f1(rotulos, preditos), 3),
        "falsas_aprovacoes": round(avaliar.taxa_falsas_aprovacoes(rotulos, preditos) or 0.0, 3),
        "falsas_refutacoes": round(sum(q == "REFUTED" for q in apoiadas) / len(apoiadas), 3) if apoiadas else None,
    }


def novo_modelo():
    return make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pasta", type=Path)
    parser.add_argument("--perfil", default="v1")
    parser.add_argument("--config", default="padrao")
    args = parser.parse_args()
    resumo = json.loads((args.pasta / "resumo.json").read_text(encoding="utf-8"))
    limiares = (resumo["limiares"]["similaridade_forte"], resumo["limiares"]["nli_forte"])

    treino = ler(args.pasta, "dev", args.perfil, args.config) + ler(args.pasta, "viz", args.perfil, args.config)
    X = numpy.array([atributos(p["trechos"]) for p in treino])
    y = numpy.array([p["rotulo"] for p in treino])
    grupos = numpy.array([p["evento"] for p in treino])

    # Validação cruzada agrupada por evento: predição fora da dobra para cada item do treino.
    fora = numpy.empty(len(y), dtype=object)
    for indices_treino, indices_teste in GroupKFold(n_splits=5).split(X, y, grupos):
        modelo = novo_modelo().fit(X[indices_treino], y[indices_treino])
        fora[indices_teste] = modelo.predict(X[indices_teste])
    regras_treino = [decidir(p["trechos"], *limiares) for p in treino]

    relatorio = {
        "perfil": args.perfil, "config": args.config, "bateria": str(args.pasta.name), "commit_bateria": resumo["commit"],
        "atributos": ATRIBUTOS, "treino": {"conjuntos": ["dev", "viz"], "n": len(y), "classes": {c: int((y == c).sum()) for c in sorted(set(y))}},
        "validacao_cruzada": {"agregador": medidas(list(y), list(fora)), "regras": medidas(list(y), regras_treino)},
        "teste": {}, "scikit_learn": sklearn.__version__,
    }
    final = novo_modelo().fit(X, y)
    for conjunto in ("val", "con", "avbr"):
        predicoes = ler(args.pasta, conjunto, args.perfil, args.config)
        if not predicoes:
            continue
        rotulos = [p["rotulo"] for p in predicoes]
        aprendido = list(final.predict(numpy.array([atributos(p["trechos"]) for p in predicoes])))
        relatorio["teste"][conjunto] = {"n": len(rotulos), "agregador": medidas(rotulos, aprendido), "regras": medidas(rotulos, [decidir(p["trechos"], *limiares) for p in predicoes])}
    regressao = final[-1]
    relatorio["coeficientes"] = {
        classe: dict(zip(ATRIBUTOS, (round(float(c), 3) for c in coeficientes))) for classe, coeficientes in zip(regressao.classes_, regressao.coef_)
    }

    pasta = RAIZ / "saida" / "modelos"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"agregador-{args.perfil}-{args.config}"
    with (pasta / f"{nome}.pkl").open("wb") as arquivo:
        pickle.dump({"modelo": final, "atributos": ATRIBUTOS, "funcao_de_atributos": "avaliacao/agregador.py::atributos"}, arquivo)
    (pasta / f"{nome}.json").write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Agregador {nome}: treino {relatorio['treino']}")
    print(f"Validação cruzada (5 dobras por evento): agregador {relatorio['validacao_cruzada']['agregador']} | regras {relatorio['validacao_cruzada']['regras']}")
    for conjunto, r in relatorio["teste"].items():
        print(f"{conjunto:<4} (n={r['n']}): agregador {r['agregador']} | regras {r['regras']}")
    print("Maiores pesos por classe:")
    for classe, pesos in relatorio["coeficientes"].items():
        principais = sorted(pesos.items(), key=lambda kv: -abs(kv[1]))[:4]
        print(f"  {classe}: " + ", ".join(f"{k} {v:+.2f}" for k, v in principais))
    print(f"Modelo em {(pasta / (nome + '.pkl')).relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
