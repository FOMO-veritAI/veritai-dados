# Análise exploratória dos conjuntos públicos (semana 3)

Análise exploratória (EDA) dos três conjuntos públicos que o levantamento da semana 2 colocou no núcleo do projeto: AVERITEC-BR, AVeriTeC e LIAR-BR. Os notebooks são de **Isabel Azar**, feitos no Google Colab em setembro de 2026. Todos os números, quadros e figuras do relatório do grupo saem deles (Apêndice A do relatório).

| Arquivo | Conjunto | Partições | O que analisa |
|---|---|---|---|
| [`eda_averitec_br.ipynb`](eda_averitec_br.ipynb) | AVERITEC-BR (tradução automática do AVeriTeC) | treino e dev (3.568) | completude, alegações repetidas com rótulos diferentes, distribuição das 4 classes, comprimento, evidências em perguntas e respostas, domínios das fontes, metadados, NER |
| [`eda_averitec.ipynb`](eda_averitec.ipynb) | AVeriTeC original (inglês) | treino e dev (3.568) | os mesmos eixos, para comparar com a tradução |
| [`eda_liar_br.ipynb`](eda_liar_br.ipynb) | LIAR-BR (tradução do LIAR) | treino, validação e teste (12.791) | escala de 6 níveis, registros com falha de leitura, metadados do falante, NER |
| [`relatorio-eda.pdf`](relatorio-eda.pdf) | os três | — | relatório do grupo entregue na semana 3 |

Os notebooks estão salvos com as saídas e as figuras, então dá para ler sem rodar.

## Como a EDA orientou a VeritAI

As implicações da seção 6.2 do relatório chegaram ao serviço assim:

- **O AVeriTeC não virou dado de treino.** Pesaram três achados:
  - alegações idênticas com rótulos diferentes;
  - a associação entre respostas "Unanswerable" e a classe "insuficiente" (24,89% das respostas dessa classe), que funcionaria como atalho;
  - o erro de tradução que inverte o sentido de uma justificativa.

  O AVeriTeC entrou só como teste de estresse: as respostas são a evidência, sem a justificativa e sem as respostas vazias (`../averitec/`).
- **Verificação de números como prioridade.** Cerca de um terço das alegações é numérica. O verificador da VeritAI confere valor, unidade, sinal e período de cada número.
- **Entidades por regra, não por NER genérico.** O `pt_core_news_sm` errou categorias e fragmentou nomes. O verificador usa regras explícitas para entidades.
- **Resultados por classe.** O desbalanceamento levou ao macro-F1, ao F1 por classe e à taxa de falsas aprovações como métricas, em vez da acurácia.

## Como rodar

Os notebooks esperam os arquivos dos conjuntos em `/content/`, a pasta de trabalho do Colab:

| Notebook | Arquivos esperados |
|---|---|
| AVERITEC-BR | `/content/train.json`, `/content/dev.json` |
| AVeriTeC | `/content/train (1).json`, `/content/dev (1).json` |
| LIAR-BR | `/content/train.jsonl`, `/content/valid.jsonl`, `/content/test.jsonl` |

Envie os arquivos pelo painel do Colab, ou troque o caminho na célula de carregamento. Bibliotecas usadas: pandas, numpy, matplotlib, seaborn, nltk e spaCy.

## Onde obter os dados (não versionados aqui)

Os dados brutos são de terceiros e não entram no git.

| Conjunto | Origem | Licença |
|---|---|---|
| AVeriTeC | [fever.ai/dataset/averitec](https://fever.ai/dataset/averitec.html), artigo [arXiv:2305.13117](https://arxiv.org/abs/2305.13117) | CC BY-NC 4.0 |
| AVERITEC-BR e LIAR-BR | Delucis et al. (STIL 2025), [doi:10.5753/stil.2025.37820](https://doi.org/10.5753/stil.2025.37820) | não declarada; o levantamento da semana 2 recomenda confirmar com os autores |

Os detalhes de cada conjunto, e de outros quinze avaliados, estão no levantamento da semana 2 (`fomo-docs/entregas/semana-2-datasets/`).
