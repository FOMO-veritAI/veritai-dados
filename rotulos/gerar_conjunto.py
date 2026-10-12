"""Gera o conjunto rotulado (formato do eval/avaliar.py da VeritAI) a partir de documentos da base própria.

Uso (com o ambiente do repositório veritai):
    python rotulos/gerar_conjunto.py [--base caminho.sqlite3]

As evidências são lidas da base (texto, URL e data reais); as afirmações e os rótulos
estão em ITENS abaixo. Saída: rotulos/conjunto-base-v0.jsonl.

Estado: pré-rotulagem feita por IA (autor "claude-pre"), pendente de revisão humana
dupla. Não use para escolher limiares nem como teste antes dessa revisão.
"""

import argparse
import json
import sqlite3
from pathlib import Path

from veritai.config import caminho_base

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "rotulos" / "conjunto-base-v0.jsonl"

S, R, N = "SUPPORTED", "REFUTED", "NOT_ENOUGH_EVIDENCE"

# (id, evento, evidências [(documento, posições dos trechos ou None para o primeiro)], afirmação, rótulo, tipo, justificativa)
ITENS = [
    # IBGE: produção industrial de agosto de 2026 (documento 1); 12 e 25 são outros meses do mesmo indicador.
    ("pim-ago-1", "ibge-pim-2026-08", [(1, None)], "Em agosto de 2026, a produção industrial brasileira caiu 0,6% em relação a julho.", S, "parafrase", "O release informa recuo de 0,6% frente a julho."),
    ("pim-ago-2", "ibge-pim-2026-08", [(1, None)], "Em agosto de 2026, a produção industrial brasileira caiu 1,6% em relação a julho.", R, "numero_alterado", "O recuo foi de 0,6%, não de 1,6%."),
    ("pim-ago-3", "ibge-pim-2026-08", [(1, None)], "Em agosto de 2026, a produção industrial brasileira cresceu 0,6% em relação a julho.", R, "direcao_invertida", "A produção recuou, não cresceu."),
    ("pim-ago-4", "ibge-pim-2026-08", [(1, None)], "Na comparação com agosto de 2025, a indústria brasileira teve queda de 1,2% em agosto de 2026.", S, "parafrase", "O release informa queda de 1,2% frente a agosto de 2025."),
    ("pim-ago-5", "ibge-pim-2026-08", [(1, None), (12, None), (25, None)], "Em agosto de 2026, a produção industrial brasileira caiu 0,6% em relação a julho.", S, "armadilha_temporal", "O release de agosto confirma; os de julho e junho tratam de outros meses e não contradizem."),
    ("pim-ago-6", "ibge-pim-2026-08", [(1, None)], "A produção industrial de Pernambuco cresceu em agosto de 2026.", N, "sem_evidencia", "O release nacional não traz resultado por estado."),
    # IBGE: PNAD Contínua, trimestre encerrado em agosto (3); 37 e 51 são outros trimestres.
    ("pnad-ago-1", "ibge-pnad-2026-08", [(3, None)], "A taxa de desocupação no Brasil ficou em 5,3% no trimestre de junho a agosto de 2026.", S, "parafrase", "O release informa 5,3% no trimestre de junho a agosto."),
    ("pnad-ago-2", "ibge-pnad-2026-08", [(3, None)], "A taxa de desocupação no Brasil ficou em 6,3% no trimestre de junho a agosto de 2026.", R, "numero_alterado", "A taxa foi de 5,3%."),
    ("pnad-ago-3", "ibge-pnad-2026-08", [(3, None)], "A taxa de subutilização foi de 13,1% no trimestre encerrado em agosto de 2026.", S, "parafrase", "O título do release informa 13,1%."),
    ("pnad-ago-4", "ibge-pnad-2026-08", [(3, None), (37, None), (51, None)], "A taxa de desocupação no Brasil ficou em 5,3% no trimestre de junho a agosto de 2026.", S, "armadilha_temporal", "O release de agosto confirma; os de maio e abril tratam de outros trimestres."),
    ("pnad-ago-5", "ibge-pnad-2026-08", [(3, None)], "A taxa de desocupação no trimestre encerrado em maio de 2026 foi de 5,3%.", R, "periodo_trocado", "O release informa 5,6% no trimestre encerrado em maio; 5,3% é o de agosto."),
    ("pnad-ago-6", "ibge-pnad-2026-08", [(3, None)], "A taxa de desocupação entre jovens de 18 a 24 anos foi de 12% no trimestre encerrado em agosto de 2026.", N, "sem_evidencia", "O trecho não traz desocupação por faixa etária."),
    # IBGE: IPCA de agosto (8) e IPCA-15 de agosto (16).
    ("ipca-ago-1", "ibge-ipca-2026-08", [(8, None)], "O IPCA de agosto de 2026 foi de -0,32%, o que indica deflação no mês.", S, "parafrase", "O release informa IPCA de -0,32% em agosto."),
    ("ipca-ago-2", "ibge-ipca-2026-08", [(8, None)], "O IPCA de agosto de 2026 foi de 0,32%.", R, "numero_alterado", "O índice foi negativo (-0,32%), não positivo."),
    ("ipca-ago-3", "ibge-ipca-2026-08", [(8, None)], "O IPCA de julho de 2026 foi de -0,32%.", R, "periodo_trocado", "O release informa 0,07% em julho; -0,32% é agosto."),
    ("ipca-ago-4", "ibge-ipca-2026-08", [(8, None)], "Nos 12 meses encerrados em agosto de 2026, o IPCA acumulou 4,22%.", S, "parafrase", "O release informa 4,22% em 12 meses."),
    ("ipca-ago-5", "ibge-ipca-2026-08", [(8, None), (16, None)], "O IPCA de agosto de 2026 foi de -0,40%.", R, "ipca_x_ipca15", "-0,40% é o IPCA-15 de agosto; o IPCA foi de -0,32%."),
    ("ipca-ago-6", "ibge-ipca-2026-08", [(8, None), (16, None)], "O IPCA-15 de agosto de 2026 foi de -0,40%.", S, "ipca_x_ipca15", "O release do IPCA-15 confirma -0,40%."),
    ("ipca-ago-7", "ibge-ipca-2026-08", [(8, None)], "Em agosto de 2026, Porto Alegre teve a menor inflação entre as capitais pesquisadas.", N, "sem_evidencia", "O trecho não traz resultados por região metropolitana."),
    # IBGE: IPCA-15 de setembro (4).
    ("ipca15-set-1", "ibge-ipca15-2026-09", [(4, None)], "O IPCA-15 de setembro de 2026 foi de 0,70%.", S, "parafrase", "O release informa 0,70%."),
    ("ipca15-set-2", "ibge-ipca15-2026-09", [(4, None)], "O IPCA-15 de setembro de 2026 foi de 0,07%.", R, "numero_alterado", "O índice foi de 0,70%; troca de casa decimal."),
    # IBGE: PIB do 2º trimestre (13); 49 é o 1º trimestre.
    ("pib-2t-1", "ibge-pib-2026-t2", [(13, None)], "O PIB brasileiro cresceu 0,5% no segundo trimestre de 2026 em relação ao primeiro trimestre.", S, "parafrase", "O release informa 0,5%."),
    ("pib-2t-2", "ibge-pib-2026-t2", [(13, None)], "O PIB brasileiro cresceu 1,1% no segundo trimestre de 2026 em relação ao primeiro trimestre.", R, "periodo_trocado", "1,1% foi o crescimento do 1º trimestre; o 2º foi 0,5%."),
    ("pib-2t-3", "ibge-pib-2026-t2", [(13, None), (49, None)], "O PIB brasileiro cresceu 0,5% no segundo trimestre de 2026 em relação ao primeiro trimestre.", S, "armadilha_temporal", "O release do 2º trimestre confirma; o do 1º trata de outro período."),
    ("pib-2t-4", "ibge-pib-2026-t2", [(13, None)], "A agropecuária cresceu 2,8% no segundo trimestre de 2026.", S, "parafrase", "O release destaca a agropecuária com 2,8%."),
    ("pib-2t-5", "ibge-pib-2026-t2", [(13, None)], "O PIB do Nordeste cresceu 2% no segundo trimestre de 2026.", N, "sem_evidencia", "O release nacional não traz PIB regional."),
    # IBGE: safra (7).
    ("safra-ago-1", "ibge-lspa-2026-08", [(7, None)], "O IBGE estima uma safra de 352,9 milhões de toneladas de grãos para 2026.", S, "parafrase", "Estimativa de agosto: 352,9 milhões de toneladas."),
    ("safra-ago-2", "ibge-lspa-2026-08", [(7, None)], "O IBGE estima uma safra de 382,9 milhões de toneladas de grãos para 2026.", R, "numero_alterado", "A estimativa é de 352,9 milhões."),
    ("safra-ago-3", "ibge-lspa-2026-08", [(7, None)], "A safra de grãos de 2026 deve ser 2,0% maior que a de 2025, segundo o IBGE.", S, "parafrase", "O release informa alta de 2,0% sobre 2025."),
    # IBGE: varejo de julho (5).
    ("varejo-jul-1", "ibge-pmc-2026-07", [(5, None)], "As vendas no comércio varejista caíram 0,8% em julho de 2026 em relação a junho.", S, "parafrase", "O release informa queda de 0,8%."),
    ("varejo-jul-2", "ibge-pmc-2026-07", [(5, None)], "As vendas no comércio varejista subiram 0,8% em julho de 2026 em relação a junho.", R, "direcao_invertida", "As vendas caíram."),
    # IBGE: abate no 1º trimestre (39).
    ("abate-1t-1", "ibge-abate-2026-t1", [(39, None)], "No primeiro trimestre de 2026, foram abatidas 10,29 milhões de cabeças de bovinos, o maior resultado para um primeiro trimestre desde 1997.", S, "parafrase", "O release informa recorde da série iniciada em 1997."),
    ("abate-1t-2", "ibge-abate-2026-t1", [(39, None)], "O abate de bovinos no primeiro trimestre de 2026 foi o menor para um primeiro trimestre desde 1997.", R, "direcao_invertida", "Foi o maior resultado da série, não o menor."),
    # Agência Gov via MEC: Enamed (316).
    ("enamed-1", "mec-enamed-2026", [(316, [0, 1])], "O Enamed 2026 reuniu mais de 152 mil inscritos.", S, "parafrase", "O texto informa 152.966 inscritos."),
    ("enamed-2", "mec-enamed-2026", [(316, [0, 1])], "O Enamed 2026 teve cerca de 14 mil inscritos.", R, "entidade_trocada", "14.417 é o número de participantes do Revalida; o Enamed tem 152.966."),
    ("enamed-3", "mec-enamed-2026", [(316, [0, 1])], "A primeira etapa do Revalida 2026/2 tem 152.966 participantes.", R, "entidade_trocada", "152.966 são os inscritos do Enamed; o Revalida tem 14.417."),
    # Agência Gov via IBGE: deflação de agosto (326).
    ("deflacao-1", "ibge-ipca-2026-08", [(326, [0, 1])], "Em agosto de 2026, a energia elétrica residencial caiu 7,63% por causa do Bônus de Itaipu.", S, "parafrase", "O texto atribui a queda de 7,63% ao Bônus de Itaipu."),
    ("deflacao-2", "ibge-ipca-2026-08", [(326, [0, 1])], "Em agosto de 2026, estava em vigor a bandeira tarifária vermelha na conta de luz.", R, "entidade_trocada", "O texto informa bandeira amarela."),
    # Agência Gov via Conab: cesta básica (327) e safra 2025/26 (309).
    ("cesta-1", "conab-cesta-2026-08", [(327, [0, 1])], "O custo da cesta básica caiu em 25 das 27 capitais em agosto de 2026.", S, "parafrase", "Pesquisa Conab/Dieese: queda em 25 das 27 capitais."),
    ("cesta-2", "conab-cesta-2026-08", [(327, [0, 1])], "O custo da cesta básica subiu em 25 das 27 capitais em agosto de 2026.", R, "direcao_invertida", "O custo caiu."),
    ("cesta-3", "conab-cesta-2026-08", [(327, [0, 1])], "Em agosto de 2026, o preço do tomate em Campo Grande caiu 27,09%.", S, "parafrase", "O texto lista Campo Grande com -27,09% no tomate."),
    ("conab-safra-1", "conab-safra-2025-26", [(309, [0, 1])], "A Conab estima uma produção recorde de 361,7 milhões de toneladas de grãos na safra 2025/26.", S, "parafrase", "12º levantamento da Conab: 361,7 milhões de toneladas."),
    ("conab-safra-2", "conab-safra-2025-26", [(309, [0, 1])], "A área plantada no país caiu 1,7% na safra 2025/26 em relação à anterior.", R, "direcao_invertida", "A área cresceu 1,7%."),
    # Agência Gov via Ministério da Saúde: pneumo 20 (307).
    ("pneumo-1", "saude-pneumo20-2026", [(307, [0, 1])], "O SUS passou a oferecer a vacina pneumocócica 20-valente para pessoas com 85 anos ou mais.", S, "parafrase", "O texto informa a oferta para 85 anos ou mais."),
    ("pneumo-2", "saude-pneumo20-2026", [(307, [0, 1])], "O SUS passou a oferecer a vacina pneumocócica 20-valente para pessoas com 60 anos ou mais.", R, "numero_alterado", "O público é de 85 anos ou mais."),
    ("pneumo-3", "saude-pneumo20-2026", [(307, [0, 1])], "A vacina pneumocócica 20-valente tem eficácia de 90% contra pneumonia.", N, "sem_evidencia", "O texto não informa eficácia."),
    # INEP: Pisa 2025 (412).
    ("pisa-1", "inep-pisa-2025", [(412, [0, 1])], "No Pisa 2025, o Brasil fez 377 pontos em Matemática.", S, "parafrase", "O texto informa 377 pontos em Matemática."),
    ("pisa-2", "inep-pisa-2025", [(412, [0, 1])], "No Pisa 2025, o Brasil fez 408 pontos em Matemática.", R, "entidade_trocada", "408 é a nota de Leitura; Matemática foi 377."),
    ("pisa-3", "inep-pisa-2025", [(412, [0, 1])], "Entre 2006 e 2025, a diferença entre o Brasil e a média da OCDE em Leitura caiu de 102 para 58 pontos.", S, "parafrase", "O texto informa a redução de 102 para 58 pontos."),
    # INEP: Encceja (404).
    ("encceja-1", "inep-encceja-2026", [(404, [0, 1])], "A reaplicação do Encceja 2026 começou em 6 de outubro.", S, "parafrase", "O texto informa início em 6 de outubro."),
    ("encceja-2", "inep-encceja-2026", [(404, [0, 1])], "O Encceja 2026 teve mais de 1 milhão de inscritos.", N, "sem_evidencia", "O texto não informa o número de inscritos."),
    # Agência Brasil: balança comercial (501).
    ("balanca-1", "mdic-balanca-2026-09", [(501, [0, 1])], "A balança comercial brasileira teve superávit de US$ 7,74 bilhões em setembro de 2026.", S, "parafrase", "O texto informa US$ 7,74 bilhões."),
    ("balanca-2", "mdic-balanca-2026-09", [(501, [0, 1])], "O superávit de setembro de 2026 foi o maior da história para meses de setembro.", R, "numero_alterado", "Foi o segundo melhor; o maior foi em setembro de 2023."),
    ("balanca-3", "mdic-balanca-2026-09", [(501, [0, 1])], "As exportações de café cresceram em setembro de 2026.", N, "sem_evidencia", "O trecho cita petróleo, combustíveis, soja e cobre, não café."),
    # Agência Brasil: câmbio (500), emplacamentos (505), Focus (506), bets (499), eleição (534).
    ("dolar-1", "mercado-2026-10-06", [(500, [0, 1])], "Em 6 de outubro de 2026, o dólar fechou a R$ 4,975, menor cotação de fechamento desde 12 de maio.", S, "parafrase", "O texto informa R$ 4,975 e o menor fechamento desde 12 de maio."),
    ("dolar-2", "mercado-2026-10-06", [(500, [0, 1])], "Em 6 de outubro de 2026, o dólar subiu 0,55% e fechou a R$ 4,975.", R, "direcao_invertida", "O dólar caiu 0,55%."),
    ("fenabrave-1", "fenabrave-2026-09", [(505, [0, 1])], "Os emplacamentos de veículos passaram de 500 mil unidades em setembro de 2026, recorde para o mês.", S, "parafrase", "O texto informa 509.686 unidades, recorde para setembro."),
    ("fenabrave-2", "fenabrave-2026-09", [(505, [0, 1])], "Os emplacamentos de veículos caíram 8,32% em setembro de 2026 em relação a setembro de 2025.", R, "direcao_invertida", "Houve alta de 8,32%."),
    ("focus-1", "bc-focus-2026-10-05", [(506, [0, 1])], "O Boletim Focus elevou a projeção de inflação de 2026 para 5,01%.", S, "parafrase", "Projeção subiu de 4,99% para 5,01%."),
    ("focus-2", "bc-focus-2026-10-05", [(506, [0, 1])], "O Boletim Focus projeta a Selic em 12% ao ano no fim de 2026.", R, "periodo_trocado", "Para 2026 a projeção é 13,5%; 12% é para 2027."),
    ("bets-1", "fazenda-bets-2026-10", [(499, [0, 1])], "O governo pediu o bloqueio de mais de 13 mil sites ilegais de apostas desde 25 de setembro de 2026.", S, "parafrase", "O texto informa 13.241 sites."),
    ("bets-2", "fazenda-bets-2026-10", [(499, [0, 1])], "O governo pediu o bloqueio de cerca de 1.300 sites ilegais de apostas desde 25 de setembro de 2026.", R, "numero_alterado", "Foram 13.241 sites."),
    ("erundina-1", "eleicao-alesp-2026", [(534, [0, 1])], "Luiza Erundina foi eleita deputada estadual em São Paulo aos 91 anos.", S, "parafrase", "O texto informa a eleição para a Alesp aos 91 anos."),
    ("erundina-2", "eleicao-alesp-2026", [(534, [0, 1])], "Luiza Erundina foi a candidata mais votada para a Assembleia Legislativa de São Paulo em 2026.", R, "numero_alterado", "Ela ficou na 13ª posição."),
    ("erundina-3", "eleicao-alesp-2026", [(534, [0, 1])], "Luiza Erundina pretende disputar a presidência da Assembleia Legislativa de São Paulo.", N, "sem_evidencia", "O texto não trata disso."),
]


def evidencias(conexao: sqlite3.Connection, referencias) -> list[dict]:
    resultado = []
    for documento, posicoes in referencias:
        doc = conexao.execute("SELECT url, titulo, data_publicacao FROM documentos WHERE id = ?", (documento,)).fetchone()
        if doc is None:
            raise ValueError(f"Documento {documento} não está na base; a base mudou desde a geração.")
        posicoes = posicoes or [0]
        trechos = conexao.execute(
            f"SELECT texto FROM trechos WHERE documento = ? AND posicao IN ({','.join('?' * len(posicoes))}) ORDER BY posicao", (documento, *posicoes)
        ).fetchall()
        # Trechos consecutivos se sobrepõem; juntos formam o texto contínuo do documento.
        resultado.append({"texto": " ".join(t[0] for t in trechos), "fonte": doc[1], "data": doc[2], "url": doc[0], "documento_base": documento})
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", type=Path, default=None)
    args = parser.parse_args()
    conexao = sqlite3.connect(f"file:{args.base or caminho_base()}?mode=ro", uri=True)
    linhas = []
    for id_, evento, referencias, afirmacao, rotulo, tipo, justificativa in ITENS:
        evid = evidencias(conexao, referencias)
        linhas.append({
            "id": id_, "par": evento, "afirmacao": afirmacao, "evidencias": evid, "rotulo": rotulo,
            "evento": evento, "data": evid[0]["data"], "fonte": "base_propria_veritai_dados", "justificativa": justificativa,
            "tipo": tipo, "autor": "claude-pre", "revisao": "pendente_humano",
        })
    SAIDA.write_text("".join(json.dumps(linha, ensure_ascii=False) + "\n" for linha in linhas), encoding="utf-8")
    print(f"{len(linhas)} itens em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
