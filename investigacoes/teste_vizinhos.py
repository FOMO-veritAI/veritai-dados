"""Roda o conjunto de vizinhos (rotulos/conjunto-vizinhos-v0.jsonl) com busca na base própria, sem web.

Uso, a partir do repositório veritai, com o .venv dele:
    python ../veritai-dados/investigacoes/teste_vizinhos.py v1 [--sem-verificador] [--contradicao-so-fora-do-tema]
        [--codigo outra/pasta/veritai] [--predicoes saida.jsonl]

--codigo roda outra versão do veritai (ex.: uma worktree de um commit anterior) para comparar.
As métricas são as do eval/avaliar.py; "recuperado" diz se o release do mês da afirmação estava
entre as evidências do relatório (falha de busca × falha de decisão).
"""

import argparse
import asyncio
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("perfil")
    parser.add_argument("--sem-verificador", action="store_true")
    parser.add_argument("--contradicao-so-fora-do-tema", action="store_true")
    parser.add_argument("--codigo", type=Path, default=Path("."))
    parser.add_argument("--arquivo", type=Path, default=RAIZ / "rotulos" / "conjunto-vizinhos-v0.jsonl")
    parser.add_argument("--predicoes", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.codigo.resolve()))
    sys.path.insert(0, str((args.codigo / "eval").resolve()))
    import avaliar
    from veritai.base import BaseEvidencias
    from veritai.config import VERIFICADOR, caminho_base, perfil
    from veritai.modelos import ComparadorNLI
    from veritai.pipeline import analisar
    from veritai.relatorio import PedidoAnalise

    if args.sem_verificador:
        VERIFICADOR["ativo"] = False
    if args.contradicao_so_fora_do_tema:
        if "contradicao_so_fora_do_tema" not in VERIFICADOR:
            sys.exit("Esta versão do código não tem a opção contradicao_so_fora_do_tema.")
        VERIFICADOR["contradicao_so_fora_do_tema"] = True

    itens = [json.loads(linha) for linha in args.arquivo.read_text(encoding="utf-8").splitlines() if linha.strip()]
    comparador = ComparadorNLI(args.perfil)
    base = BaseEvidencias(caminho_base(), perfil(args.perfil)["embedding"], comparador.modelos.vetorizar, args.perfil)
    base.verificar_indice()
    with sqlite3.connect(f"file:{caminho_base()}?mode=ro", uri=True) as conexao:
        url_do_documento = dict(conexao.execute("SELECT id, url FROM documentos").fetchall())

    # Um pedido por data (até 10 afirmações), como uma notícia com várias afirmações.
    por_data = defaultdict(list)
    for item in itens:
        por_data[item["data"]].append(item)
    resultados = {}
    for data, grupo in sorted(por_data.items()):
        for inicio in range(0, len(grupo), 10):
            lote = grupo[inicio : inicio + 10]
            pedido = PedidoAnalise(noticia={"titulo": "Conjunto de vizinhos", "data": data}, afirmacoes=[i["afirmacao"] for i in lote], buscar_na_web=False)
            relatorio = asyncio.run(analisar(pedido, comparador, base=base))
            for item, analise in zip(lote, relatorio.afirmacoes):
                urls = sorted({e.url for e in analise.evidencias})
                resultados[item["id"]] = {"predito": analise.resultado, "recuperado": url_do_documento[item["documento_base"]] in urls, "urls": urls}

    rotulos = [i["rotulo"] for i in itens]
    preditos = [resultados[i["id"]]["predito"] for i in itens]
    resultado = avaliar.metricas(rotulos, preditos)
    estado = "sem verificador" if args.sem_verificador else ("contradição só fora do tema" if args.contradicao_so_fora_do_tema else "verificador padrão")
    print(avaliar.formatar(f"{args.perfil} ({estado}, código {args.codigo})", resultado, {"carga_s": 0.0, "inferencia_s": 0.0}).split("\n", 1)[1])
    print("Acerto por tipo:")
    for tipo in sorted({i["tipo"] for i in itens}):
        dos = [i for i in itens if i["tipo"] == tipo]
        acertos = sum(resultados[i["id"]]["predito"] == i["rotulo"] for i in dos)
        recuperados = [i for i in dos if resultados[i["id"]]["recuperado"]]
        print(f"  {tipo:<24} {acertos}/{len(dos)}  preditos {dict(Counter(resultados[i['id']]['predito'] for i in dos))}"
              + (f"  release recuperado em {len(recuperados)}/{len(dos)}" if tipo != "antes_do_release" else ""))
    if args.predicoes:
        args.predicoes.write_text(
            "".join(json.dumps({"id": i["id"], "tipo": i["tipo"], "rotulo": i["rotulo"], **resultados[i["id"]]}, ensure_ascii=False) + "\n" for i in itens),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
