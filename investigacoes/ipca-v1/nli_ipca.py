"""Pares controlados para isolar por que o NLI da V1 dá "neutro" nos itens de IPCA."""

import sys

from veritai.modelos import ModelosHF

m = ModelosHF(sys.argv[1] if len(sys.argv) > 1 else "v1")

PREMISSA_API = ("IPCA-15 é de 0,70% em setembro. O Índice Nacional de Preços ao Consumidor Amplo 15 (IPCA-15) foi de 0,70% em setembro, "
                "ficando 1,10 ponto percentual (p.p.) acima da taxa de agosto (-0,40%). O IPCA-E, que se constitui no IPCA-15 acumulado "
                "trimestralmente, ficou em 0,36%, abaixo da taxa")
FRASE = "O Índice Nacional de Preços ao Consumidor Amplo 15 (IPCA-15) foi de 0,70% em setembro, ficando 1,10 ponto percentual (p.p.) acima da taxa de agosto (-0,40%)."
casos = [
    ("A. janela atual (sem ano, com fragmento cortado)", PREMISSA_API, "O IPCA-15 de setembro de 2026 foi de 0,70%."),
    ("B. mesma janela, hipótese sem o ano", PREMISSA_API, "O IPCA-15 de setembro foi de 0,70%."),
    ("C. sem o fragmento cortado no fim", PREMISSA_API.rsplit(" O IPCA-E", 1)[0], "O IPCA-15 de setembro de 2026 foi de 0,70%."),
    ("D. uma frase só, sem ano", FRASE, "O IPCA-15 de setembro de 2026 foi de 0,70%."),
    ("E. uma frase só, hipótese sem ano", FRASE, "O IPCA-15 de setembro foi de 0,70%."),
    ("F. janela com ano no texto", PREMISSA_API.replace("em setembro,", "em setembro de 2026,"), "O IPCA-15 de setembro de 2026 foi de 0,70%."),
    ("G. janela com data de publicação na frente", "Publicado em 25/09/2026. " + PREMISSA_API, "O IPCA-15 de setembro de 2026 foi de 0,70%."),
    ("H. contraste: valor errado, sem ano", FRASE, "O IPCA-15 de setembro foi de 0,07%."),
    ("I. contraste: valor errado, com ano no texto", FRASE.replace("em setembro,", "em setembro de 2026,"), "O IPCA-15 de setembro de 2026 foi de 0,07%."),
    ("J. IPCA agosto, frase com ano", "O IPCA de agosto de 2026 foi de -0,32%, 0,39 ponto percentual (p.p.) abaixo do 0,07% registrado em julho.", "O IPCA de agosto de 2026 foi de -0,32%."),
    ("K. IPCA agosto, frase sem ano", "O IPCA de agosto foi de -0,32%, 0,39 ponto percentual (p.p.) abaixo do 0,07% registrado em julho.", "O IPCA de agosto de 2026 foi de -0,32%."),
]
saida = m.classificar([(p, h) for _, p, h in casos])
for (nome, _, h), probs in zip(casos, saida):
    print(f"{nome:<48} ent={probs['entailment']:.3f} neu={probs['neutral']:.3f} con={probs['contradiction']:.3f}   H: {h}")
