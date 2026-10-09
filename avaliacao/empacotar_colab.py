"""Monta veritai-colab.zip: tudo o que o notebook de avaliação precisa para rodar no Google Colab.

Uso, a partir de veritai-dados/:
    python avaliacao/empacotar_colab.py [--saida caminho.zip]

O pacote leva o código da VeritAI (sem .venv), os scripts e rótulos de veritai-dados, os resultados da
última bateria completa e do teste intocado (fora do git) e a base própria já migrada (veritai/data,
também fora do git). Não leva .env, o AVeriTeC convertido nem outras saídas. No Colab, a primeira célula
do notebook pede o upload deste arquivo.
"""

import argparse
import zipfile
from pathlib import Path

DADOS = Path(__file__).resolve().parents[1]
RAIZ = DADOS.parent
IGNORAR_PASTAS = {".venv", ".git", "__pycache__", ".pytest_cache", "veritai.egg-info", "revisao", "saida", "data", "demo"}
IGNORAR_ARQUIVOS = {".env", ".DS_Store"}


def arquivos(pasta: Path):
    for caminho in sorted(pasta.rglob("*")):
        relativo = caminho.relative_to(RAIZ)
        if caminho.is_file() and not IGNORAR_PASTAS & set(relativo.parts[:-1]) and caminho.name not in IGNORAR_ARQUIVOS:
            yield caminho


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--saida", type=Path, default=DADOS / "avaliacao" / "veritai-colab.zip")
    args = parser.parse_args()
    lista = list(arquivos(RAIZ / "veritai")) + list(arquivos(DADOS))
    # Fora do git, mas necessários: a base migrada e os resultados mais recentes de cada bateria.
    lista.append(RAIZ / "veritai" / "data" / "veritai.sqlite3")
    for sufixo in ("completa", "intocado"):
        pastas = sorted((DADOS / "saida" / "bateria").glob(f"*-{sufixo}"))
        if pastas:
            lista += [c for c in pastas[-1].rglob("*") if c.is_file() and c.name not in IGNORAR_ARQUIVOS]
    if not (RAIZ / "veritai" / "data" / "veritai.sqlite3").exists():
        raise SystemExit("Base própria não encontrada em veritai/data/veritai.sqlite3.")
    args.saida.unlink(missing_ok=True)
    with zipfile.ZipFile(args.saida, "w", zipfile.ZIP_DEFLATED) as pacote:
        for caminho in lista:
            if caminho != args.saida:
                pacote.write(caminho, caminho.relative_to(RAIZ))
    print(f"{len(lista)} arquivos, {args.saida.stat().st_size / 1e6:.1f} MB em {args.saida}")


if __name__ == "__main__":
    main()
