"""Testa a regra do período de referência nos itens de IPCA e nos casos de risco (V1)."""

import json
import re
import sys
from datetime import date

sys.path.insert(0, "eval")
from avaliar import fontes_do_item  # noqa: E402
from veritai.copias import agrupar  # noqa: E402
from veritai.modelos import ComparadorNLI, ModelosHF  # noqa: E402
from veritai.regras import agregar  # noqa: E402

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def referencia(titulo: str, publicado: str) -> str | None:
    """Mês citado no título, no ano mais recente em que ele não é posterior à publicação."""
    achado = re.search(r"\b(" + "|".join(MESES) + r")\b", titulo.lower())
    if not achado:
        return None
    pub = date.fromisoformat(publicado)
    mes = MESES.index(achado.group(1)) + 1
    ano = pub.year if mes <= pub.month else pub.year - 1
    return f"{MESES[mes - 1]} de {ano}"


# 1. Casos de risco no NLI, com a linha de referência no lugar da data de publicação.
m = ModelosHF("v1")
P = "O Índice Nacional de Preços ao Consumidor Amplo (IPCA) de dezembro foi de 0,52%, acima do 0,39% de novembro."
ref = referencia("IPCA de dezembro fica em 0,52%", "2026-01-10")
casos = [
    (f"ref {ref}, H dez/2025 (certo)", f"Período de referência: {ref}. " + P, "O IPCA de dezembro de 2025 foi de 0,52%."),
    (f"ref {ref}, H dez/2026 (errado)", f"Período de referência: {ref}. " + P, "O IPCA de dezembro de 2026 foi de 0,52%."),
]
for (n, p, h), r in zip(casos, m.classificar([(p, h) for _, p, h in casos])):
    print(f"{n:<42} ent={r['entailment']:.3f} neu={r['neutral']:.3f} con={r['contradiction']:.3f}")

# 2. Itens de IPCA do conjunto, com e sem a linha de referência nas evidências do IBGE sem ano.
itens = [json.loads(l) for l in open("../veritai-dados/rotulos/conjunto-base-v0.jsonl", encoding="utf-8")]
comparador = ComparadorNLI("v1", m)
for item in itens:
    if not item["id"].startswith(("ipca-", "ipca15-")):
        continue
    resultados = []
    for com_ref in (False, True):
        copia = json.loads(json.dumps(item))
        for ev in copia["evidencias"]:
            r = referencia(ev["fonte"], ev["data"])
            if com_ref and r and not re.search(r"\b20\d{2}\b", ev["texto"]):
                ev["texto"] = f"Período de referência: {r}. " + ev["texto"]
        fontes = fontes_do_item(copia)
        agrupar(fontes)
        resultados.append(agregar(comparador.comparar(copia["afirmacao"], fontes)).resultado)
    print(f"{item['id']:<14} rótulo {item['rotulo']:<20} sem ref {resultados[0]:<20} com ref {resultados[1]}")
