"""Rastro do comparador V1 em itens de IPCA do conjunto-base-v0."""

import json
import sys

sys.path.insert(0, "eval")
from avaliar import fontes_do_item  # noqa: E402
from veritai.config import LIMIARES  # noqa: E402
from veritai.copias import agrupar  # noqa: E402
from veritai.modelos import ComparadorNLI  # noqa: E402
from veritai.regras import explicar  # noqa: E402

ids = sys.argv[2].split(",")
itens = {i["id"]: i for i in map(json.loads, open("../veritai-dados/rotulos/conjunto-base-v0.jsonl", encoding="utf-8"))}
comparador = ComparadorNLI(sys.argv[1])
print("limiares", LIMIARES)
for id_ in ids:
    item = itens[id_]
    fontes = fontes_do_item(item)
    agrupar(fontes)
    rastro: dict = {}
    avaliados = comparador.comparar(item["afirmacao"], fontes, rastro)
    print(f"\n=== {id_} [{item['rotulo']}] {item['afirmacao']}")
    for fonte in rastro["fontes"]:
        print(f"  fonte: {fonte['titulo'][:60]}  trechos={len(fonte['trechos'])}")
        for t in fonte["trechos"]:
            print(f"     trecho: {t[:160]!r}")
        for j in sorted(fonte["janelas"], key=lambda j: -(j["similaridade"] or 0))[:6]:
            nli = {k[:3]: round(v, 3) for k, v in (j["nli"] or {}).items()}
            print(f"     sim={j['similaridade']:.3f} nli={nli} rel={j['no_relatorio']} | {j['texto'][:140]!r}")
    e = explicar(avaliados)
    print("  resultado:", e["resultado"], "|", e["regra"])
    for it in e["itens"]:
        print(f"     {it['relacao']:<13} nli={it['pontuacao_nli']:.3f} sim={it['similaridade']:.3f} forte={it['forte']} | {it['trecho'][:100]!r}")
