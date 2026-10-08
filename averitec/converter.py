"""Converte o desenvolvimento do AVeriTeC para o formato de eval/avaliar.py (teste de estresse).

Uso (com o ambiente do repositório veritai):
    python averitec/converter.py caminho/dev.json [--com-unanswerable] [--sem-site-da-checagem] [--traducao dev_pt.json]

O AVeriTeC (Schlichtkrull et al., 2023) está sob CC BY-NC 4.0: só uso não comercial,
com atribuição, e os dados não vão para o git (a saída fica em saida/averitec/).

Decisões (com base na EDA da FOP, relatório seção 4):
- evidência = uma por resposta, com o texto "pergunta + resposta"; nas booleanas entra também a
  explicação ("No" sozinho não diz nada);
- fonte = domínio original da URL (quase todas passam pelo web.archive.org, que senão contaria
  como uma fonte só); respostas tiradas dos metadados da alegação ou sem URL contam como uma
  fonte por item;
- a justificativa (`justification`) nunca vira evidência: ela verbaliza o veredito;
- respostas Unanswerable ("No answer could be found.") ficam de fora por padrão, porque são um
  atalho para NEE que não existe em produção; --com-unanswerable as mantém;
- --sem-site-da-checagem tira as respostas vindas do mesmo site do artigo de checagem;
- --traducao usa o texto do AVERITEC-BR (Delucis et al., 2025; licença não declarada, derivada do
  AVeriTeC), alinhado por posição com o original. Ficam de fora as alegações com alguma resposta
  truncada pela tradução (original com mais de um parágrafo e tradução com menos da metade do
  tamanho), o defeito medido na EDA (seção 4.5). Os erros de magnitude da tradução ("80.63 lakh"
  → "80,63 mil") continuam lá e podem aparecer como "número sem correspondente".

Não é medição de desempenho da VeritAI: alegações de 2020, centradas nos EUA, em inglês e com
evidência-ouro escolhida por anotadores. As regras do verificador são para português.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parents[1]
SHA256_DEV = "499793726b4a5406780928a3d9dedc48d6dd53de778f22437d129cacdb08e300"  # revisão 2ca9dee do HF chenxwh/AVeriTeC
ROTULOS = {
    "Supported": "SUPPORTED",
    "Refuted": "REFUTED",
    "Not Enough Evidence": "NOT_ENOUGH_EVIDENCE",
    "Conflicting Evidence/Cherrypicking": "CONFLICTING_EVIDENCE",
}


def url_original(url: str) -> str:
    """Tira o prefixo do web.archive.org: https://web.archive.org/web/2020.../https://site/x → https://site/x."""
    achado = re.match(r"https?://web\.archive\.org/web/[^/]+/(.*)", url or "")
    return achado.group(1) if achado else (url or "")


def dominio(url: str) -> str:
    return (urlparse(url_original(url)).hostname or "").removeprefix("www.")


def texto_da_resposta(pergunta: str, resposta: dict) -> str:
    pergunta = pergunta.strip()
    if not pergunta.endswith("?"):
        pergunta += "?"
    texto = f"{pergunta} {resposta['answer'].strip()}"
    if resposta.get("boolean_explanation"):
        texto = f"{texto.rstrip('.')}. {resposta['boolean_explanation'].strip()}"
    return texto


def paragrafos(texto: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", texto or "") if p.strip()]


def truncada(original: dict, traduzida: dict) -> bool:
    """Alguma resposta (ou explicação booleana) com original de vários parágrafos e tradução com menos da metade."""
    for q_en, q_pt in zip(original["questions"], traduzida["questions"]):
        for a_en, a_pt in zip(q_en["answers"], q_pt["answers"]):
            for campo in ("answer", "boolean_explanation"):
                en, pt = a_en.get(campo) or "", a_pt.get(campo) or ""
                if len(paragrafos(en)) > 1 and len(pt) < 0.5 * len(en):
                    return True
    return False


def traduzir(alegacoes: list[dict], traducao: list[dict], contagem: Counter) -> list[tuple[int, dict]]:
    """Troca o texto pelo da tradução, alinhado por posição, e tira as alegações truncadas."""
    if len(traducao) != len(alegacoes):
        raise ValueError(f"Tradução com {len(traducao)} alegações; o original tem {len(alegacoes)}.")
    resultado = []
    for indice, (en, pt) in enumerate(zip(alegacoes, traducao)):
        if (en["label"], en.get("claim_date"), len(en["questions"])) != (pt["label"], pt.get("claim_date"), len(pt["questions"])):
            raise ValueError(f"Alegação {indice} desalinhada entre original e tradução.")
        if truncada(en, pt):
            contagem["alegações truncadas pela tradução, fora"] += 1
            continue
        resultado.append((indice, pt))
    return resultado


def converter(alegacoes: list[tuple[int, dict]], com_unanswerable: bool, sem_site_da_checagem: bool) -> tuple[list[dict], Counter]:
    itens, contagem = [], Counter()
    for indice, alegacao in alegacoes:
        data = datetime.strptime(alegacao["claim_date"], "%d-%m-%Y").date().isoformat() if alegacao.get("claim_date") else ""
        site_da_checagem = dominio(alegacao.get("fact_checking_article") or "")
        evidencias = []
        for pergunta in alegacao["questions"]:
            for resposta in pergunta["answers"]:
                contagem["respostas"] += 1
                # O tipo não é traduzido; o texto fixo vira "Nenhuma resposta pôde ser encontrada." no AVERITEC-BR.
                if resposta["answer_type"] == "Unanswerable" and not com_unanswerable:
                    contagem["unanswerable descartadas"] += 1
                    continue
                url = url_original(resposta.get("source_url") or "")
                if sem_site_da_checagem and site_da_checagem and dominio(url) == site_da_checagem:
                    contagem["do site da checagem descartadas"] += 1
                    continue
                if urlparse(url).hostname:
                    evidencia = {"texto": texto_da_resposta(pergunta["question"], resposta), "fonte": dominio(url), "data": None, "url": url}
                else:
                    # "Metadata" ou sem URL: uma fonte por item, identificada pelo nome.
                    nome = "metadados da alegação" if url == "Metadata" else "sem URL"
                    evidencia = {"texto": texto_da_resposta(pergunta["question"], resposta), "fonte": nome, "data": None}
                evidencias.append(evidencia)
        contagem["itens sem evidência"] += not evidencias
        itens.append({
            "id": f"averitec-dev-{indice:03d}",
            "afirmacao": alegacao["claim"],
            "evidencias": evidencias,
            "rotulo": ROTULOS[alegacao["label"]],
            "evento": f"averitec-dev-{indice:03d}",
            "data": data,
            "fonte": "AVeriTeC dev (CC BY-NC 4.0)",
            # Só para leitura humana; avaliar.py não usa este campo como entrada.
            "justificativa": alegacao.get("justification") or "",
            "tipos": alegacao.get("claim_types") or [],
            "estrategias": alegacao.get("fact_checking_strategies") or [],
        })
    return itens, contagem


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("entrada", type=Path, help="dev.json do AVeriTeC")
    parser.add_argument("--com-unanswerable", action="store_true")
    parser.add_argument("--sem-site-da-checagem", action="store_true")
    parser.add_argument("--traducao", type=Path, help="dev.json do AVERITEC-BR (texto em português)")
    args = parser.parse_args()
    bruto = args.entrada.read_bytes()
    sha = hashlib.sha256(bruto).hexdigest()
    if sha != SHA256_DEV:
        print(f"Aviso: SHA-256 {sha} difere da revisão conferida na EDA ({SHA256_DEV}).")
    alegacoes, previa = list(enumerate(json.loads(bruto))), Counter()
    if args.traducao:
        alegacoes = traduzir([a for _, a in alegacoes], json.loads(args.traducao.read_text(encoding="utf-8")), previa)
    itens, contagem = converter(alegacoes, args.com_unanswerable, args.sem_site_da_checagem)
    contagem.update(previa)
    for item in itens:
        if args.traducao:
            item["fonte"] = "AVERITEC-BR dev (tradução do AVeriTeC, CC BY-NC 4.0)"
    sufixo = ("-pt" if args.traducao else "") + ("-com-unanswerable" if args.com_unanswerable else "") + ("-sem-site-da-checagem" if args.sem_site_da_checagem else "")
    saida = RAIZ / "saida" / "averitec" / f"dev{sufixo}.jsonl"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in itens), encoding="utf-8")
    print(f"{len(itens)} itens em {saida.relative_to(RAIZ)}; {dict(contagem)}")
    print("Rótulos:", dict(Counter(item["rotulo"] for item in itens)))


if __name__ == "__main__":
    main()
