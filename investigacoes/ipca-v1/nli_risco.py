from veritai.modelos import ModelosHF
m = ModelosHF("v1")
P = "O Índice Nacional de Preços ao Consumidor Amplo (IPCA) de dezembro foi de 0,52%, acima do 0,39% de novembro."
casos = [
    ("publicação 10/01/2026, H dez/2025 (certo)", "Publicado em 10/01/2026. " + P, "O IPCA de dezembro de 2025 foi de 0,52%."),
    ("publicação 10/01/2026, H dez/2026 (errado)", "Publicado em 10/01/2026. " + P, "O IPCA de dezembro de 2026 foi de 0,52%."),
    ("sem data, H dez/2025", P, "O IPCA de dezembro de 2025 foi de 0,52%."),
    ("publicação 11/09/2026, H ago/2026 (certo)", "Publicado em 11/09/2026. O IPCA de agosto foi de -0,32%.", "O IPCA de agosto de 2026 foi de -0,32%."),
    ("publicação 11/09/2026, H ago/2025 (errado)", "Publicado em 11/09/2026. O IPCA de agosto foi de -0,32%.", "O IPCA de agosto de 2025 foi de -0,32%."),
]
for (n, p, h), r in zip(casos, m.classificar([(p, h) for _, p, h in casos])):
    print(f"{n:<45} ent={r['entailment']:.3f} neu={r['neutral']:.3f} con={r['contradiction']:.3f}")
