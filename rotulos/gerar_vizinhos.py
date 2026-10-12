"""Gera o conjunto de vizinhos: afirmações sobre releases mensais do IBGE, verificadas com busca na base.

Uso (com o ambiente do repositório veritai, base no esquema 2 com período de referência):
    python rotulos/gerar_vizinhos.py [--base caminho.sqlite3] [--por-tipo 35] [--semente 0]

Mede o que o verificador deveria proteger: na base há releases da mesma série em vários meses,
e a busca traz os vizinhos junto. O rótulo vem da construção, a partir do título oficial de
cada release (valor e mês), e não de anotação:
- `valor_certo` (SUPPORTED): o valor do mês X, com a notícia datada no dia do release de X;
- `valor_do_mes_anterior` (REFUTED): o valor de X-1 atribuído a X, na mesma data;
- `antes_do_release` (NOT_ENOUGH_EVIDENCE): o valor certo de X, com a notícia datada na véspera do
  release de X, quando só há releases de outros meses;
- `ipca_x_ipca15` (REFUTED): o valor do IPCA-15 atribuído ao IPCA do mesmo mês, e vice-versa.

Os itens não têm evidências: a VeritAI busca na base (investigacoes/teste_vizinhos.py). Erros de
leitura dos títulos são possíveis; confira uma amostra antes de tirar conclusões.
"""

import argparse
import json
import random
import re
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from veritai.config import caminho_base

RAIZ = Path(__file__).resolve().parents[1]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
# Ordem importa: IPCA-15 antes de IPCA.
SERIES = [
    ("ipca15", r"\bIPCA-15\b", "O IPCA-15 de {mes} de {ano} foi de {valor}%."),
    ("ipca", r"\bIPCA\b(?!-)", "O IPCA de {mes} de {ano} foi de {valor}%."),
    ("ipp", r"Preços ao Produtor", "O Índice de Preços ao Produtor de {mes} de {ano} foi de {valor}%."),
    ("construcao", r"Construção Civil", "O Índice Nacional da Construção Civil variou {valor}% em {mes} de {ano}."),
    ("industria", r"^Produção industrial", "A produção industrial variou {valor}% em {mes} de {ano}."),
    ("servicos", r"[Vv]olume d[eo]s? [Ss]erviços", "O volume de serviços variou {valor}% em {mes} de {ano}."),
    ("varejo", r"vendas no varejo", "As vendas no varejo variaram {valor}% em {mes} de {ano}."),
    ("desocupacao", r"taxa de desocupação", "A taxa de desocupação foi de {valor}% no trimestre encerrado em {mes} de {ano}."),
]
QUEDA = re.compile(r"\b(recua|recuam|cai|caem)\b", re.IGNORECASE)


def ler_titulo(titulo: str) -> tuple[str, str] | None:
    """(série, valor como no título, com sinal) do primeiro percentual do título."""
    serie = next((nome for nome, padrao, _ in SERIES if re.search(padrao, titulo)), None)
    achado = re.search(r"([-–−]?)\s?(\d+(?:,\d+)?)\s*%", titulo)
    if not serie or not achado:
        return None
    negativo = bool(achado.group(1)) or bool(QUEDA.search(titulo[: achado.start()]))
    valor = achado.group(2)
    return serie, ("-" if negativo and valor.strip("0,") else "") + valor


def afirmacao(serie: str, periodo: str, valor: str) -> str:
    ano, mes = periodo.split("-")
    modelo = next(m for nome, _, m in SERIES if nome == serie)
    return modelo.format(mes=MESES[int(mes) - 1], ano=ano, valor=valor)


def mes_anterior(periodo: str) -> str:
    ano, mes = map(int, periodo.split("-"))
    return f"{ano - 1}-12" if mes == 1 else f"{ano}-{mes - 1:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--por-tipo", type=int, default=35)
    parser.add_argument("--semente", type=int, default=0)
    args = parser.parse_args()
    conexao = sqlite3.connect(f"file:{args.base or caminho_base()}?mode=ro", uri=True)
    linhas = conexao.execute(
        "SELECT id, titulo, data_publicacao, periodo_referencia FROM documentos WHERE dominio = 'agenciadenoticias.ibge.gov.br' "
        "AND periodo_referencia GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]' ORDER BY data_publicacao, id"
    ).fetchall()
    releases: dict[tuple[str, str], dict] = {}
    conflitos = set()
    for id_, titulo, data, periodo in linhas:
        lido = ler_titulo(titulo)
        if not lido:
            continue
        serie, valor = lido
        chave = (serie, periodo)
        if chave in releases and releases[chave]["valor"] != valor:
            conflitos.add(chave)
        # Fica o primeiro release do mês (o mais antigo).
        releases.setdefault(chave, {"id": id_, "titulo": titulo, "data": data, "valor": valor})
    for chave in conflitos:
        del releases[chave]

    por_tipo = defaultdict(list)
    for (serie, periodo), r in sorted(releases.items()):
        base = {"serie": serie, "periodo": periodo, "documento_base": r["id"], "titulo_release": r["titulo"]}
        por_tipo["valor_certo"].append({**base, "afirmacao": afirmacao(serie, periodo, r["valor"]), "rotulo": "SUPPORTED", "data": r["data"]})
        vespera = (date.fromisoformat(r["data"]) - timedelta(days=1)).isoformat()
        por_tipo["antes_do_release"].append({**base, "afirmacao": afirmacao(serie, periodo, r["valor"]), "rotulo": "NOT_ENOUGH_EVIDENCE", "data": vespera})
        anterior = releases.get((serie, mes_anterior(periodo)))
        if anterior and anterior["valor"] != r["valor"]:
            por_tipo["valor_do_mes_anterior"].append(
                {**base, "afirmacao": afirmacao(serie, periodo, anterior["valor"]), "rotulo": "REFUTED", "data": r["data"], "documento_vizinho": anterior["id"]}
            )
        if serie == "ipca" and (outro := releases.get(("ipca15", periodo))) and outro["valor"] != r["valor"]:
            data = max(r["data"], outro["data"])
            por_tipo["ipca_x_ipca15"].append({**base, "afirmacao": afirmacao("ipca", periodo, outro["valor"]), "rotulo": "REFUTED", "data": data, "documento_vizinho": outro["id"]})
            por_tipo["ipca_x_ipca15"].append(
                {**base, "serie": "ipca15", "documento_base": outro["id"], "titulo_release": outro["titulo"],
                 "afirmacao": afirmacao("ipca15", periodo, r["valor"]), "rotulo": "REFUTED", "data": data, "documento_vizinho": r["id"]}
            )

    sorteio = random.Random(args.semente)
    itens = []
    for tipo, lista in sorted(por_tipo.items()):
        escolhidos = lista if len(lista) <= args.por_tipo else sorted(sorteio.sample(lista, args.por_tipo), key=lambda i: (i["serie"], i["periodo"]))
        for item in escolhidos:
            itens.append({
                "id": f"viz-{tipo}-{item['serie']}-{item['periodo']}",
                "tipo": tipo,
                **item,
                "evento": f"ibge-{item['serie']}-{item['periodo']}",
                "fonte": "base_propria_veritai_dados",
                "justificativa": f"Gerado do título do release: {item['titulo_release']}",
                "autor": "gerado-de-titulos",
                "revisao": "conferir_amostra",
            })
    saida = RAIZ / "rotulos" / "conjunto-vizinhos-v0.jsonl"
    saida.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in itens), encoding="utf-8")
    print(f"{len(releases)} releases lidos ({len(conflitos)} meses com valores conflitantes descartados); {len(itens)} itens em {saida.relative_to(RAIZ)}")
    for tipo, lista in sorted(por_tipo.items()):
        print(f"  {tipo}: {len(lista)} possíveis, {min(len(lista), args.por_tipo)} no conjunto")


if __name__ == "__main__":
    main()
