"""Teste de ponta a ponta: a VeritAI analisando afirmações só com a base própria (sem web).

Uso, a partir do repositório veritai (ou da worktree), com o .venv dele:
    python ../veritai-dados/investigacoes/teste_base.py v1 [--sem-verificador]

Não é medição: são 8 afirmações escritas a partir de documentos da base (07/10/2026).
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from veritai.base import BaseEvidencias  # noqa: E402
from veritai.config import VERIFICADOR, caminho_base, perfil  # noqa: E402
from veritai.modelos import ComparadorNLI  # noqa: E402
from veritai.pipeline import analisar  # noqa: E402
from veritai.relatorio import PedidoAnalise  # noqa: E402

CASOS = [
    ("A produção industrial brasileira recuou 0,6% em agosto de 2026 em relação a julho.", "SUPPORTED"),
    ("A produção industrial brasileira cresceu 0,6% em agosto de 2026 em relação a julho.", "REFUTED"),
    ("O governo incluiu 82 empregadores na lista suja do trabalho escravo.", "SUPPORTED"),
    ("O governo incluiu 182 empregadores na lista suja do trabalho escravo.", "REFUTED"),
    ("As provas do Enem 2026 serão aplicadas nos dias 8 e 15 de novembro.", "SUPPORTED"),
    ("As provas do Enem 2026 serão aplicadas nos dias 1 e 8 de dezembro.", "REFUTED"),
    ("O IPCA-15 de março de 2026 foi de 0,44%.", "SUPPORTED"),
    ("A seleção brasileira venceu a Copa do Mundo de 2026.", "NOT_ENOUGH_EVIDENCE"),
]


async def main(nome: str) -> None:
    comparador = ComparadorNLI(nome)
    base = BaseEvidencias(caminho_base(), perfil(nome)["embedding"], comparador.modelos.vetorizar, nome)
    base.verificar_indice()
    pedido = PedidoAnalise(noticia={"titulo": "Teste da base própria", "data": "2026-10-07"}, afirmacoes=[a for a, _ in CASOS], buscar_na_web=False)
    inicio = time.perf_counter()
    relatorio = await analisar(pedido, comparador, base=base)
    estado = "com" if VERIFICADOR["ativo"] else "sem"
    acertos = sum(item.resultado == esperado for (_, esperado), item in zip(CASOS, relatorio.afirmacoes))
    print(f"== Perfil {nome}, {estado} verificador ({time.perf_counter() - inicio:.0f} s): {acertos}/{len(CASOS)}")
    for (afirmacao, esperado), item in zip(CASOS, relatorio.afirmacoes):
        marca = "OK  " if item.resultado == esperado else "ERRO"
        print(f"{marca} esperado {esperado:<20} obtido {item.resultado:<20} {afirmacao[:75]}")


if __name__ == "__main__":
    if "--sem-verificador" in sys.argv:
        VERIFICADOR["ativo"] = False
    asyncio.run(main(sys.argv[1]))
