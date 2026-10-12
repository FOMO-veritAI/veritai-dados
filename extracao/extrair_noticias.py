"""Roda a extração por regras (veritai/extracao.py) nas notícias da base própria e prepara a anotação.

Uso (com o ambiente do repositório veritai):
    python extracao/extrair_noticias.py [--base caminho.sqlite3] [--amostra 30] [--semente 0]

Notícias: Agência Brasil, Agência Gov e gov.br (INEP) da base. Os textos da base são páginas
inteiras achatadas; para aproximar o corpo que o publicador enviaria ao FOMO, o cabeçalho de
cada portal (editoria, autor, "Publicado em", crédito de foto, "Versão em áudio") é cortado aqui,
por regras deste script. É uma aproximação: sobras de página ainda aparecem.

Saídas:
- saida/extracao/candidatas.csv: todas as candidatas, para consulta (fora do git);
- rotulos/extracao-v0/anotacao.csv: candidatas de uma amostra de notícias, com colunas para anotar;
- rotulos/extracao-v0/faltantes.csv: uma linha por notícia da amostra, para listar o que o extrator perdeu.
O guia de anotação está em rotulos/extracao-v0/README.md.
"""

import argparse
import csv
import random
import re
import sqlite3
from collections import Counter
from pathlib import Path

from veritai.config import caminho_base
from veritai.extracao import extrair

RAIZ = Path(__file__).resolve().parents[1]
DOMINIOS = ("agenciabrasil.ebc.com.br", "agenciagov.ebc.com.br", "www.gov.br")
# Último marcador de cabeçalho nos primeiros caracteres: o corpo começa depois dele.
FIM_DO_CABECALHO = re.compile(
    r"Versão em áudio|\d{2}/\d{2}/\d{4}\s*[-–]?\s*\d{2}[:h]\d{2}|Atualizado em \d{2}/\d{2}/\d{4} \d{2}h\d{2}|Colaboradores: [^.]*?\b(?:Inep|MEC)\b"
)
CREDITO = re.compile(
    r"^\s*(?:Divulgação\s+|Foto:\s*[\wÀ-ÿ .]+/[\wÀ-ÿ]+\s+|(?:©\s*)?[\wÀ-ÿ .]+/(?:arquivo|[A-ZÀ-Ý][\wÀ-ÿ ]+?)(?=\s+[A-ZÀ-Ý])\s*)"
)
SUFIXO_DO_TITULO = re.compile(r"\s+(?:[|—–-]\s+.*)$")


def corpo(texto: str) -> str:
    marcadores = [m for m in FIM_DO_CABECALHO.finditer(texto[:1200])]
    inicio = marcadores[-1].end() if marcadores else 0
    return CREDITO.sub("", texto[inicio:]).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=None)
    parser.add_argument("--amostra", type=int, default=30)
    parser.add_argument("--semente", type=int, default=0)
    args = parser.parse_args()
    conexao = sqlite3.connect(f"file:{args.base or caminho_base()}?mode=ro", uri=True)
    marcadores = ",".join("?" * len(DOMINIOS))
    documentos = conexao.execute(
        f"SELECT id, dominio, titulo, url, data_publicacao, texto FROM documentos WHERE dominio IN ({marcadores}) ORDER BY id", DOMINIOS
    ).fetchall()

    linhas, por_noticia, sinais, alertas = [], Counter(), Counter(), Counter()
    for id_, dominio, titulo, url, data, texto in documentos:
        titulo = SUFIXO_DO_TITULO.sub("", titulo)
        for c in extrair(titulo, corpo(texto), data):
            linhas.append({
                "doc_id": id_, "dominio": dominio, "titulo": titulo, "url": url, "data": data, "posicao": c.posicao, "pontuacao": c.pontuacao,
                "afirmacao_proposta": c.texto, "trecho_origem": c.trecho_origem, "sinais": "; ".join(c.sinais),
                "alertas": "; ".join(c.alertas), "atribuicao": c.atribuicao or "",
            })
            por_noticia[id_] += 1
            sinais.update(c.sinais)
            alertas.update(c.alertas)

    saida = RAIZ / "saida" / "extracao" / "candidatas.csv"
    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)

    contagens = [por_noticia.get(d[0], 0) for d in documentos]
    print(f"{len(documentos)} notícias; {len(linhas)} candidatas em {saida.relative_to(RAIZ)}")
    print(f"Candidatas por notícia: {Counter(contagens).most_common()}")
    print("Sinais:", dict(sinais.most_common()))
    print("Alertas:", {k: f"{v} ({v / len(linhas):.0%})" for k, v in alertas.most_common()})

    sorteio = random.Random(args.semente)
    escolhidas = sorted(sorteio.sample([d[0] for d in documentos], args.amostra))
    pasta = RAIZ / "rotulos" / "extracao-v0"
    pasta.mkdir(parents=True, exist_ok=True)
    campos_anotacao = ["verificavel (s/n)", "atomica (s/n)", "compreensivel_sozinha (s/n)", "afirmacao_corrigida", "anotador", "observacao"]
    with (pasta / "anotacao.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=[*linhas[0], *campos_anotacao])
        escritor.writeheader()
        escritor.writerows({**l, **dict.fromkeys(campos_anotacao, "")} for l in linhas if l["doc_id"] in escolhidas)
    with (pasta / "faltantes.csv").open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["doc_id", "titulo", "url", "data", "candidatas_propostas", "afirmacoes_faltantes (uma por linha na célula)", "anotador"])
        for d in documentos:
            if d[0] in escolhidas:
                escritor.writerow([d[0], SUFIXO_DO_TITULO.sub("", d[2]), d[3], d[4], por_noticia.get(d[0], 0), "", ""])
    print(f"Amostra para anotação: {len(escolhidas)} notícias, {sum(l['doc_id'] in escolhidas for l in linhas)} candidatas em {pasta.relative_to(RAIZ)}/")


if __name__ == "__main__":
    main()
