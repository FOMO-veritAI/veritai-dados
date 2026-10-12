"""Gera o conjunto de validação (conjunto-validacao-v0.jsonl) a partir de documentos da base própria.

Escrito em 07/10/2026, antes da implementação do verificador da VeritAI, com documentos
que não foram usados no diagnóstico (conjunto-base-v0). Serve para medir o verificador
fora dos casos que o motivaram. Mesmo autor (pré-rotulagem por IA), então não é cego:
pendente de revisão humana como o conjunto-base-v0.

Uso (com o ambiente do repositório veritai):
    python rotulos/gerar_validacao.py [--base caminho.sqlite3]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerar_conjunto import N, R, RAIZ, S, evidencias  # noqa: E402

from veritai.config import caminho_base  # noqa: E402

SAIDA = RAIZ / "rotulos" / "conjunto-validacao-v0.jsonl"

ITENS = [
    # Virada de ano: releases de janeiro sobre dezembro do ano anterior.
    ("v-ipca-dez-1", "ibge-ipca-2025-12", [(109, None)], "O IPCA de dezembro de 2025 foi de 0,33%.", S, "virada_de_ano", "Release de 09/01/2026: IPCA de dezembro (2025) de 0,33%."),
    ("v-ipca-dez-2", "ibge-ipca-2025-12", [(109, None)], "O IPCA de dezembro de 2026 foi de 0,33%.", N, "virada_de_ano", "A evidência trata de dezembro de 2025; não diz nada sobre dezembro de 2026."),
    ("v-ipca-dez-3", "ibge-ipca-2025-12", [(109, None)], "O IPCA de dezembro de 2025 foi de 0,52%.", R, "periodo_trocado", "0,52% foi dezembro de 2024; dezembro de 2025 foi 0,33%."),
    ("v-ipca15-jan-1", "ibge-ipca15-2026-01", [(102, None)], "O IPCA-15 de janeiro de 2026 foi de 0,20%.", S, "sem_ano_no_texto", "Release de 27/01/2026: IPCA-15 de janeiro de 0,20%."),
    ("v-ipca15-jan-2", "ibge-ipca15-2026-01", [(102, None)], "O IPCA-15 de dezembro de 2025 foi de 0,20%.", R, "virada_de_ano", "O IPCA-15 de dezembro foi 0,25%; 0,20% é janeiro."),
    ("v-ipca-fev-1", "ibge-ipca-2026-02", [(81, None)], "O IPCA de fevereiro de 2026 foi de 0,70%.", S, "sem_ano_no_texto", "Release informa 0,70% em fevereiro."),
    ("v-ipca-fev-2", "ibge-ipca-2026-02", [(81, None)], "O IPCA de fevereiro de 2026 foi de 0,37%.", R, "unidade_trocada", "0,37 é a diferença em pontos percentuais; o IPCA foi 0,70%."),
    ("v-ipca15-mar-1", "ibge-ipca15-2026-03", [(74, None)], "O IPCA-15 de março de 2026 foi de 0,44%.", S, "sem_ano_no_texto", "Release informa IPCA-15 de 0,44% em março."),
    ("v-ipca15-mar-2", "ibge-ipca15-2026-03", [(74, None), (69, None)], "O IPCA de março de 2026 foi de 0,44%.", R, "ipca_x_ipca15", "0,44% é o IPCA-15; o IPCA de março foi 0,88%."),
    ("v-ipca15-mar-3", "ibge-ipca15-2026-03", [(74, None), (69, None)], "O IPCA-15 de março de 2026 foi de 0,44%.", S, "ipca_x_ipca15", "O release do IPCA-15 confirma; o do IPCA trata de outro índice."),
    # Sinal negativo.
    ("v-ipp-out-1", "ibge-ipp-2025-10", [(120, None)], "Os preços ao produtor (IPP) variaram -0,48% em outubro de 2025.", S, "sinal", "Release informa -0,48%."),
    ("v-ipp-out-2", "ibge-ipp-2025-10", [(120, None)], "Os preços ao produtor (IPP) subiram 0,48% em outubro de 2025.", R, "sinal", "A variação foi negativa (-0,48%)."),
    ("v-ipp-fev-1", "ibge-ipp-2026-02", [(72, None)], "Em fevereiro de 2026, os preços ao produtor caíram 0,25% frente a janeiro.", S, "sinal", "Release informa -0,25%; \"caíram 0,25%\" é o mesmo fato."),
    ("v-serv-nov-1", "ibge-pms-2025-11", [(107, None)], "O volume de serviços variou -0,1% em novembro de 2025.", S, "sinal", "Release informa -0,1%."),
    ("v-serv-nov-2", "ibge-pms-2025-11", [(107, None)], "O volume de serviços cresceu 0,1% em novembro de 2025.", R, "sinal", "O volume variou -0,1%."),
    # Séries temporais e períodos.
    ("v-pim-dez-1", "ibge-pim-2025-12", [(99, None)], "Em dezembro de 2025, a produção industrial recuou 1,2% frente a novembro.", S, "parafrase", "Release informa recuo de 1,2%."),
    ("v-pim-dez-2", "ibge-pim-2025-12", [(99, None), (83, None), (110, None)], "Em dezembro de 2025, a produção industrial recuou 1,2% frente a novembro.", S, "armadilha_temporal", "Os releases de janeiro e novembro tratam de outros meses."),
    ("v-pim-jan-1", "ibge-pim-2026-01", [(83, None)], "Em janeiro de 2026, a produção industrial avançou 1,8% frente a dezembro.", S, "parafrase", "Release informa alta de 1,8%."),
    ("v-pim-jan-2", "ibge-pim-2026-01", [(83, None)], "Em janeiro de 2026, a produção industrial avançou 1,2% frente a dezembro.", R, "numero_alterado", "A alta foi de 1,8%."),
    ("v-pnad-ano-1", "ibge-pnad-2025-anual", [(101, None)], "A taxa anual de desocupação de 2025 foi de 5,6%, a menor da série iniciada em 2012.", S, "parafrase", "Release informa 5,6%, menor da série."),
    ("v-pnad-ano-2", "ibge-pnad-2025-anual", [(101, None)], "A taxa anual de desocupação de 2024 foi de 5,6%.", R, "periodo_trocado", "A de 2024 foi 6,6%; 5,6% é 2025."),
    ("v-pnad-ano-3", "ibge-pnad-2025-anual", [(101, None), (100, None)], "A taxa de desocupação no trimestre encerrado em dezembro de 2025 foi de 5,1%.", S, "armadilha_temporal", "O release trimestral confirma 5,1%; o anual (5,6%) trata de outro recorte."),
    ("v-pib-2025-1", "ibge-pib-2025-anual", [(86, None)], "O PIB brasileiro cresceu 2,3% em 2025.", S, "parafrase", "Release informa 2,3%."),
    ("v-pib-2025-2", "ibge-pib-2025-anual", [(86, None)], "A agropecuária cresceu 1,4% em 2025.", R, "entidade_trocada", "1,4% foi a Indústria; a Agropecuária cresceu 11,7%."),
    ("v-pib-2025-3", "ibge-pib-2025-anual", [(86, None), (121, None)], "O PIB brasileiro cresceu 0,1% em 2025.", R, "periodo_trocado", "0,1% foi o 3º trimestre; no ano o PIB cresceu 2,3%."),
    ("v-safra-dez-1", "ibge-lspa-2025-12", [(105, None)], "Em dezembro de 2025, o IBGE estimou a safra de 2026 em 339,8 milhões de toneladas.", S, "parafrase", "Título informa 339,8 milhões de toneladas para 2026."),
    ("v-safra-dez-2", "ibge-lspa-2025-12", [(105, None)], "A safra de 2025 foi estimada pelo IBGE em 339,8 milhões de toneladas.", R, "periodo_trocado", "A estimativa para 2025 é 346,1 milhões; 339,8 é 2026."),
    ("v-abate-2025-1", "ibge-abate-2025-anual", [(76, None)], "Em 2025, foram abatidas 42,94 milhões de cabeças de bovinos, um recorde.", S, "parafrase", "Release informa 42,94 milhões, novo recorde."),
    ("v-abate-2025-2", "ibge-abate-2025-anual", [(76, None)], "O abate de bovinos em 2025 caiu 8,2% em relação a 2024.", R, "direcao_invertida", "O abate aumentou 8,2%."),
    # Entidade ausente: a evidência fala de outro recorte.
    ("v-varejo-mg", "ibge-pmc-2025-10", [(115, None)], "As vendas no varejo de Minas Gerais cresceram 0,5% em outubro de 2025.", N, "sem_evidencia", "O release nacional não traz dados de Minas Gerais."),
    ("v-pim-ba", "ibge-pim-regional-2025-10", [(119, None)], "Em outubro de 2025, a produção industrial da Bahia cresceu 6,5%.", N, "sem_evidencia", "O trecho cita Goiás com 6,5%; não traz dado da Bahia."),
    ("v-pim-go", "ibge-pim-regional-2025-10", [(119, None)], "Em outubro de 2025, a produção industrial de Goiás cresceu 6,5%.", S, "parafrase", "O trecho cita Goiás com 6,5%."),
    # Outras fontes.
    ("v-carnes-1", "conab-carnes-2026", [(306, [0, 1])], "A produção de carnes bovina, suína e de aves deve atingir 34,08 milhões de toneladas em 2026, segundo a Conab.", S, "parafrase", "Projeção da Conab: 34,08 milhões em 2026."),
    ("v-carnes-2", "conab-carnes-2026", [(306, [0, 1])], "A produção de carnes bovina, suína e de aves deve atingir 34,08 milhões de toneladas em 2027, segundo a Conab.", R, "periodo_trocado", "Para 2027 a projeção é 34,26 milhões."),
    ("v-conab-2627", "conab-safra-2026-27", [(308, [0, 1])], "A Conab projeta uma safra de grãos de 366,6 milhões de toneladas no ciclo 2026/27.", S, "parafrase", "Projeção da Conab: 366,6 milhões."),
    ("v-elnino-1", "inmet-elnino-2026", [(332, [0, 1])], "Há probabilidade de 75% de o El Niño atual ser o mais forte registrado desde 1950.", S, "parafrase", "O texto informa 75%."),
    ("v-elnino-2", "inmet-elnino-2026", [(332, [0, 1])], "Há probabilidade de 90% de o El Niño atual ser o mais forte registrado desde 1950.", R, "entidade_trocada", "90% é a probabilidade de evento muito forte; a de ser o mais forte desde 1950 é 75%."),
    ("v-bolsa-1", "mercado-2026-10-05", [(503, [0, 1])], "Em 5 de outubro de 2026, o Ibovespa subiu 7,85% e passou pela primeira vez dos 200 mil pontos.", S, "parafrase", "O texto informa +7,85% e a marca inédita de 200 mil pontos."),
    ("v-bolsa-2", "mercado-2026-10-05", [(503, [0, 1])], "Em 5 de outubro de 2026, o dólar subiu 4,12%.", R, "direcao_invertida", "O dólar caiu 4,12%."),
    ("v-tse-1", "tse-painel-2026-10", [(531, [0, 1])], "Segundo o TSE, a pausa na divulgação do resultado da eleição presidencial durou 50 minutos.", S, "parafrase", "O texto informa pausa de 50 minutos."),
    ("v-tse-2", "tse-painel-2026-10", [(531, [0, 1])], "Segundo o TSE, a pausa na divulgação alterou a contagem dos votos.", R, "direcao_invertida", "O TSE afirma que não houve influência na contabilização."),
    ("v-tse-3", "tse-painel-2026-10", [(531, [0, 1])], "O TSE vai multar a empresa responsável pelo painel de resultados.", N, "sem_evidencia", "O texto não fala em multa."),
    ("v-ideb-1", "mec-ideb-painel-2026", [(314, [0, 1])], "O Ideb de 2025 do ensino médio foi de 4,5.", N, "sem_evidencia", "O texto fala do painel, não traz o valor do Ideb."),
]


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
