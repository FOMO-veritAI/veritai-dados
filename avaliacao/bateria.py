"""Bateria de avaliação da VeritAI: perfis × configurações do verificador × conjuntos, num comando só.

Uso, a partir de veritai-dados/, com o ambiente do repositório veritai:
    ../veritai/.venv/bin/python avaliacao/bateria.py [--perfis v1 v0] [--configs padrao sem alternativa]
        [--conjuntos dev val con avbr aven viz] [--nome rotulo]

Conjuntos:
- dev, val: releases (rotulos/conjunto-base-v0, conjunto-validacao-v0), conferidos por um anotador;
- con: contraste (veritai/eval/contraste.jsonl), só sanidade;
- avbr, aven: AVeriTeC dev em português (AVERITEC-BR) e em inglês, gerados por averitec/converter.py
  em saida/averitec/ (fora do git); pulados se não existirem;
- viz: vizinhos, com busca na base própria (VERITAI_BASE).
Configurações: padrao (config.json), sem (verificador desligado), alternativa
(contradicao_so_fora_do_tema).

Saída em saida/bateria/<data>-<commit>[-nome]/ (fora do git):
- predicoes/<conjunto>-<perfil>-<config>.jsonl: predição e trechos de cada item (relação, similaridade,
  nota do NLI e grupo da fonte), para estudar limiares sem rodar os modelos de novo (avaliacao/limiares.py);
- resumo.json e resumo.md, com o commit e as versões.

Métricas: macro-F1 (IC95 por bootstrap), falsas aprovações (SUPPORTED quando o rótulo é outro), falsas
refutações (REFUTED quando o rótulo é SUPPORTED), taxa de NEE predita, itens frágeis (a decisão muda se
um dos limiares de "forte" se mover 0,02 para cima ou para baixo) e, nos vizinhos, recall da busca
(o release do mês da afirmação está entre as evidências do relatório).
"""

import argparse
import asyncio
import json
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERITAI = RAIZ.parent / "veritai"
sys.path.insert(0, str(VERITAI))
sys.path.insert(0, str(VERITAI / "eval"))

import avaliar  # noqa: E402
from veritai.config import LIMIARES, VERIFICADOR, caminho_base, perfil, versoes  # noqa: E402
from veritai.modelos import ComparadorNLI  # noqa: E402
from veritai.regras import agregar, grupo  # noqa: E402

CONJUNTOS = {
    "dev": RAIZ / "rotulos" / "conjunto-base-v0.jsonl",
    "val": RAIZ / "rotulos" / "conjunto-validacao-v0.jsonl",
    "con": VERITAI / "eval" / "contraste.jsonl",
    "avbr": RAIZ / "saida" / "averitec" / "dev-pt.jsonl",
    "aven": RAIZ / "saida" / "averitec" / "dev.jsonl",
    "viz": RAIZ / "rotulos" / "conjunto-vizinhos-v0.jsonl",
    # Teste intocado: treino do AVeriTeC, nunca usado para ajustar regras ou limiares. Rode uma vez, com a config final.
    "avbr_teste": RAIZ / "saida" / "averitec" / "train-pt.jsonl",
    "aven_teste": RAIZ / "saida" / "averitec" / "train.jsonl",
}
CONFIGS = {
    "padrao": {},
    "sem": {"ativo": False},
    "alternativa": {"contradicao_so_fora_do_tema": True},
}
CLASSES = avaliar.CLASSES


def decidir(trechos: list[dict], similaridade_forte: float, nli_forte: float) -> str:
    """As regras de veritai/regras.py sobre trechos salvos, com limiares à escolha."""
    fortes = [t for t in trechos if t["similaridade"] >= similaridade_forte and t["pontuacao"] >= nli_forte]
    a_favor = {t["grupo"] for t in fortes if t["relacao"] == "entailment"}
    contra = {t["grupo"] for t in fortes if t["relacao"] == "contradiction"}
    if a_favor and contra:
        return "CONFLICTING_EVIDENCE"
    if contra:
        return "REFUTED"
    if a_favor:
        return "SUPPORTED"
    return "NOT_ENOUGH_EVIDENCE"


def fragil(trechos: list[dict], predito: str, passo: float = 0.02) -> bool:
    s, n = LIMIARES["similaridade_forte"], LIMIARES["nli_forte"]
    return any(decidir(trechos, s + ds, n + dn) != predito for ds, dn in ((passo, 0), (-passo, 0), (0, passo), (0, -passo)))


def salvar_trechos(itens) -> list[dict]:
    return [
        {"grupo": grupo(t), "relacao": t.relacao, "similaridade": round(t.similaridade, 5), "pontuacao": round(t.pontuacao_nli, 5)}
        for t in itens
    ]


def rodar_conjunto_com_evidencias(comparador, itens: list[dict]) -> list[dict]:
    saida = []
    for item in itens:
        trechos = comparador.comparar(item["afirmacao"], avaliar.fontes_do_item(item))
        saida.append({"id": item.get("id"), "rotulo": item["rotulo"], "predito": agregar(trechos).resultado, "trechos": salvar_trechos(trechos)})
    return saida


def rodar_vizinhos(comparador, itens: list[dict], nome_perfil: str) -> list[dict]:
    from veritai.base import BaseEvidencias
    from veritai.pipeline import analisar
    from veritai.relatorio import PedidoAnalise

    base = BaseEvidencias(caminho_base(), perfil(nome_perfil)["embedding"], comparador.modelos.vetorizar, nome_perfil)
    base.verificar_indice()
    with sqlite3.connect(f"file:{caminho_base()}?mode=ro", uri=True) as conexao:
        url_do_documento = dict(conexao.execute("SELECT id, url FROM documentos").fetchall())
    capturados: dict[str, list] = {}
    original = comparador.comparar

    def comparar(afirmacao, fontes, rastro=None):
        resultado = original(afirmacao, fontes, rastro)
        capturados[afirmacao] = resultado
        return resultado

    comparador.comparar = comparar
    saida = []
    try:
        for item in itens:
            pedido = PedidoAnalise(noticia={"titulo": "Conjunto de vizinhos", "data": item["data"]}, afirmacoes=[item["afirmacao"]], buscar_na_web=False)
            analise = asyncio.run(analisar(pedido, comparador, base=base)).afirmacoes[0]
            urls = {e.url for e in analise.evidencias}
            saida.append({
                "id": item["id"], "tipo": item["tipo"], "rotulo": item["rotulo"], "predito": analise.resultado,
                "trechos": salvar_trechos(capturados[item["afirmacao"]]), "recuperado": url_do_documento[item["documento_base"]] in urls,
            })
    finally:
        comparador.comparar = original
    return saida


def metricas(predicoes: list[dict]) -> dict:
    rotulos, preditos = [p["rotulo"] for p in predicoes], [p["predito"] for p in predicoes]
    base = avaliar.metricas(rotulos, preditos)
    apoiadas = [p for p in predicoes if p["rotulo"] == "SUPPORTED"]
    resultado = {
        "n": len(predicoes),
        "macro_f1": base["macro_f1"],
        "macro_f1_ic95": base["macro_f1_ic95"],
        "falsas_aprovacoes": base["taxa_falsas_aprovacoes"],
        "falsas_refutacoes": sum(p["predito"] == "REFUTED" for p in apoiadas) / len(apoiadas) if apoiadas else None,
        "taxa_nee": sum(p == "NOT_ENOUGH_EVIDENCE" for p in preditos) / len(preditos),
        "frageis": sum(fragil(p["trechos"], p["predito"]) for p in predicoes),
        "f1_por_classe": base["f1_por_classe"],
    }
    if all("recuperado" in p for p in predicoes):
        com_release = [p for p in predicoes if p.get("tipo") != "antes_do_release"]
        resultado["recall_busca"] = sum(p["recuperado"] for p in com_release) / len(com_release) if com_release else None
    return resultado


def commit_atual() -> str:
    try:
        hash_ = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout.strip()
        # Só as pastas que a bateria usa: código, conjuntos e conversores.
        pastas = [str(VERITAI), *(str(RAIZ / p) for p in ("avaliacao", "rotulos", "averitec", "investigacoes"))]
        sujo = subprocess.run(["git", "status", "--porcelain", "--", *pastas], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
        return hash_ + ("-modificado" if sujo else "")
    except (OSError, subprocess.CalledProcessError):
        return "sem-git"


def formatar(valor, porcento=False) -> str:
    if valor is None:
        return "—"
    return f"{100 * valor:.1f}%" if porcento else f"{valor:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--perfis", nargs="+", default=["v1", "v0"])
    parser.add_argument("--configs", nargs="+", default=["padrao", "sem", "alternativa"], choices=list(CONFIGS))
    parser.add_argument("--conjuntos", nargs="+", default=[c for c in CONJUNTOS if not c.endswith("_teste")], choices=list(CONJUNTOS))
    parser.add_argument("--nome", default="")
    args = parser.parse_args()

    commit = commit_atual()
    pasta = RAIZ / "saida" / "bateria" / f"{datetime.now():%Y%m%dT%H%M}-{commit}{'-' + args.nome if args.nome else ''}"
    (pasta / "predicoes").mkdir(parents=True, exist_ok=True)
    original = dict(VERIFICADOR)
    resumo = {"commit": commit, "data": datetime.now().isoformat(timespec="seconds"), "limiares": dict(LIMIARES), "versoes": {}, "resultados": []}
    for nome_perfil in args.perfis:
        comparador = ComparadorNLI(nome_perfil)
        resumo["versoes"][nome_perfil] = versoes(nome_perfil)
        for nome_config in args.configs:
            VERIFICADOR.clear()
            VERIFICADOR.update({**original, **CONFIGS[nome_config]})
            for nome_conjunto in args.conjuntos:
                caminho = CONJUNTOS[nome_conjunto]
                if not caminho.exists():
                    print(f"pulado: {nome_conjunto} ({caminho} não existe)")
                    continue
                inicio = time.perf_counter()
                if nome_conjunto == "viz":
                    itens = [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]
                    predicoes = rodar_vizinhos(comparador, itens, nome_perfil)
                else:
                    predicoes = rodar_conjunto_com_evidencias(comparador, avaliar.carregar(caminho))
                # As regras salvas reproduzem a decisão do serviço; se não, a bateria está desatualizada.
                divergentes = [p["id"] for p in predicoes if decidir(p["trechos"], LIMIARES["similaridade_forte"], LIMIARES["nli_forte"]) != p["predito"]]
                if divergentes:
                    raise RuntimeError(f"decidir() diverge de regras.agregar em {divergentes[:5]}: atualize a bateria.")
                arquivo = pasta / "predicoes" / f"{nome_conjunto}-{nome_perfil}-{nome_config}.jsonl"
                arquivo.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in predicoes), encoding="utf-8")
                m = metricas(predicoes)
                resumo["resultados"].append({"conjunto": nome_conjunto, "perfil": nome_perfil, "config": nome_config, "segundos": round(time.perf_counter() - inicio, 1), **m})
                print(f"{nome_conjunto:<4} {nome_perfil} {nome_config:<11} macro-F1 {formatar(m['macro_f1'])}  aprov. {formatar(m['falsas_aprovacoes'], True)}"
                      f"  refut. {formatar(m['falsas_refutacoes'], True)}  NEE {formatar(m['taxa_nee'], True)}  frágeis {m['frageis']}"
                      + (f"  recall busca {formatar(m['recall_busca'], True)}" if "recall_busca" in m else ""), flush=True)
    VERIFICADOR.clear()
    VERIFICADOR.update(original)

    (pasta / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    linhas = [f"# Bateria {resumo['data']} (commit {commit})", "", f"Limiares: {resumo['limiares']}", "",
              "| Conjunto | Perfil | Config | n | Macro-F1 (IC95) | Falsas aprov. | Falsas refut. | NEE | Frágeis | Recall busca |", "|---" * 10 + "|"]
    for r in resumo["resultados"]:
        ic = r["macro_f1_ic95"]
        linhas.append(
            f"| {r['conjunto']} | {r['perfil']} | {r['config']} | {r['n']} | {formatar(r['macro_f1'])} [{formatar(ic[0]) if ic else '—'}; {formatar(ic[1]) if ic else '—'}]"
            f" | {formatar(r['falsas_aprovacoes'], True)} | {formatar(r['falsas_refutacoes'], True)} | {formatar(r['taxa_nee'], True)} | {r['frageis']}"
            f" | {formatar(r.get('recall_busca'), True)} |"
        )
    (pasta / "resumo.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"\nResultados em {pasta.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
