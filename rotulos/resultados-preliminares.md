# Resultados preliminares: conjunto-base-v0 (07/10/2026)

**Isto não é medição de desempenho.** Os rótulos ainda não passaram por revisão humana, o conjunto é pequeno (65 itens) e as afirmações foram escritas por IA a partir de evidências reais. Os números servem só para orientar a revisão e o trabalho no comparador.

Comando: `eval/avaliar.py --perfil {v0,v1} --arquivo ../veritai-dados/rotulos/conjunto-base-v0.jsonl`, na VeritAI `5f16d67` com a branch `dados/data-publicacao-plone`, em CPU (i5-1334U).

| Métrica | V0 (MiniLM) | V1 (e5 + mDeBERTa) |
|---|---|---|
| Macro-F1 (IC95) | 0,287 [0,227; 0,446] | 0,436 [0,356; 0,675] |
| Falsas aprovações (IC95) | **33%** [16%; 50%] | **3%** [0%; 10%] |
| F1 SUPPORTED / REFUTED / NEE | 0,72 / 0,00 / 0,43 | 0,78 / 0,68 / 0,29 |
| Tempo de inferência | 16 s | 1.099 s |

## Acertos por tipo

| Tipo | V0 | V1 |
|---|---|---|
| parafrase | 21/28 | 18/28 |
| numero_alterado | 0/9 | 6/9 |
| direcao_invertida | 0/7 | 7/7 |
| periodo_trocado | 0/4 | 2/4 |
| entidade_trocada | 0/4 | 1/4 |
| ipca_x_ipca15 | 0/2 | 0/2 |
| armadilha_temporal | 3/3 | 3/3 |
| sem_evidencia | 8/8 | 4/8 |

## O que chama atenção

1. **O V0 nunca prevê REFUTED.** Das 25 afirmações falsas, aprovou 11 como SUPPORTED, entre elas "408 pontos em Matemática" (o valor é de Leitura) e "subiram 0,8%" (as vendas caíram).
2. **No V1, falta de evidência vira contradição em 4 de 8 casos.** Exemplos: "A produção industrial de Pernambuco cresceu" e "O PIB do Nordeste cresceu 2%" saíram REFUTED. Isso viola a regra "falta de evidência nunca vira contradição" do `AGENTS.md`.
3. **No V1, os 7 itens de IPCA e IPCA-15 saíram NOT_ENOUGH_EVIDENCE**, inclusive paráfrases quase literais. É preciso investigar; as hipóteses são o sinal negativo, o "p.p." na divisão em frases ou a tokenização de percentuais.
4. **Troca de entidade é o ponto mais fraco dos dois perfis.** Quando o número certo aparece na mesma frase ligado a outra entidade (Enamed × Revalida, Leitura × Matemática), o NLI não separa.
5. **A armadilha temporal passou nos dois perfis.** Isso acontece porque, aqui, todas as evidências são do mesmo domínio (um grupo só) e os outros meses não geraram contradição forte. Na base real, com os releases do mesmo indicador trazidos pela busca, o problema apareceu (teste de ponta a ponta de 07/10).
6. **O V1 é cerca de 70 vezes mais lento** nesta máquina. *(08/10: em boa parte por carregar o NLI em float16; corrigido, veja `investigacoes/verificador-resultados.md`.)*
