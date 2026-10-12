# Verificador: custo, benefício e a alternativa "contradição só fora do tema" (08/10/2026)

**Isto não é medição de desempenho.** Releases e contraste são pré-rotulagem por IA; o conjunto de vizinhos tem rótulo por construção, a partir de títulos oficiais, mas sem revisão; o AVeriTeC é estrangeiro, de 2020 e com evidência-ouro. Os números orientam decisões de regra.

## O que foi medido

Quatro configurações do verificador, nos mesmos conjuntos, na mesma máquina (Mac M4, só CPU):
- **sem:** verificador desligado;
- **original:** o verificador do commit `a533066`, antes das correções;
- **corrigido:** os defeitos achados no AVeriTeC corrigidos (`29283a8`, `b8ae170`):
  - comparações tiradas também da afirmação;
  - nomes compostos e ligados por "de/da/do/ao" juntos, identificados pela última palavra;
  - tabela de equivalentes (EUA = Estados Unidos, Covid = Covid-19);
  - cargos e pronomes fora da lista de entidades;
  - lista de entidades comparada sem acentos;
  - texto gritado deixa de virar sigla;
- **alternativa:** corrigido + `verificador.contradicao_so_fora_do_tema` (`19d90ba`, `cc91e8d`). Entidade ausente e período divergente só bloqueiam a contradição quando o documento inteiro está fora do tema. Fora do tema quer dizer uma de três coisas:
  - o documento tem outro período de referência;
  - ele não cita nenhum nome da afirmação;
  - a afirmação não tem nomes, e então não há como confirmar o tema.

O conjunto novo, **vizinhos com busca** (`rotulos/conjunto-vizinhos-v0.jsonl`, 140 itens; rodar com `investigacoes/teste_vizinhos.py`), é o cenário para o qual o verificador foi feito. A VeritAI busca na base própria, que tem releases da mesma série em vários meses e de séries parecidas no mesmo mês. Tipos de item:
- `valor_certo`: SUPPORTED;
- `valor_do_mes_anterior`: REFUTED;
- `antes_do_release`: NEE, com a notícia datada na véspera do release;
- `ipca_x_ipca15`: REFUTED.

## Resultados

Macro-F1 / taxa de falsas aprovações.

**V1**

| Conjunto | sem | original | corrigido | alternativa |
|---|---|---|---|---|
| Vizinhos com busca (140) | 0,264 / 7,6% | **0,617 / 0,0%** | 0,617 / 0,0% | 0,617 / 0,0% |
| Releases dev (65) | 0,436 / 3,0% | 0,564 / 6,1% | 0,564 / 6,1% | 0,564 / 6,1% |
| Releases validação (43) | 0,423 / 9,5% | 0,572 / 4,8% | 0,572 / 4,8% | 0,572 / 4,8% |
| Contraste (28) | 0,639 / 0,0% | 0,608 / 0,0% | 0,608 / 0,0% | 0,608 / 0,0% |
| AVERITEC-BR (424) | 0,313 / 7,8% | 0,157 / 3,1% | 0,193 / 3,7% | **0,256 / 3,4%** |
| AVeriTeC EN (500) | 0,289 / 10,3% | 0,149 / 5,3% | 0,172 / 6,1% | 0,220 / 5,8% |

**V0**

| Conjunto | sem | original | corrigido | alternativa |
|---|---|---|---|---|
| Vizinhos com busca (140) | 0,206 / 35,2% | **0,392 / 1,9%** | 0,392 / 1,9% | 0,392 / 1,9% |
| Releases dev (65) | 0,287 / 33,3% | 0,411 / 3,0% | 0,411 / 3,0% | 0,411 / 3,0% |
| Releases validação (43) | 0,288 / 52,4% | 0,406 / 19,0% | 0,406 / 19,0% | 0,406 / 19,0% |
| Contraste (28) | 0,530 / 12,5% | 0,488 / 12,5% | 0,488 / 12,5% | 0,488 / 12,5% |
| AVERITEC-BR (424) | 0,252 / 10,6% | 0,172 / 7,2% | 0,198 / 7,8% | 0,232 / 6,5% |

### 1. Com busca, o verificador é indispensável

Nos vizinhos, a V1 vai de 0,264 para 0,617 de macro-F1, e as falsas aprovações de 7,6% para 0%. A V0 vai de 35,2% para 1,9% de falsas aprovações.

Sem o verificador, na V1:
- só 5 dos 35 valores certos saem SUPPORTED; 17 viram CONFLICTING por causa dos releases de outros meses;
- 19 das 35 afirmações feitas antes do release saem REFUTED, com base em meses vizinhos.

O custo medido no AVeriTeC (seção 3) não é motivo para desligá-lo.

### 2. As correções só mexem onde havia defeito

Releases, contraste e vizinhos ficam idênticos nos dois perfis. O AVERITEC-BR sobe de 0,157 para 0,193 (V1) e de 0,172 para 0,198 (V0).

### 3. A alternativa recupera refutações sem custo no cenário com busca

Na versão final, a alternativa não muda nenhuma predição em releases, contraste e vizinhos, nos dois perfis. No AVERITEC-BR, a V1 sobe de 0,193 para 0,256.

| Mudança no AVERITEC-BR, de corrigido para alternativa | V1 | V0 |
|---|---|---|
| REFUTED recuperadas (eram NEE) | **+38** | +28 |
| CONFLICTING que viram REFUTED (erro dos dois lados) | 7 | 3 |
| **Verdadeiras que passam a REFUTED** (falsa refutação) | **2** | **14** |
| Outras | 1 | 6 |

Na V1, a troca é favorável: 38 refutações corretas por 2 falsas refutações. Na V0, cujo NLI é mais fraco, o custo é bem maior: 14 alegações verdadeiras refutadas, numa plataforma em que isso vira alarme para o revisor.

**Como a alternativa chegou aqui.** A primeira versão custava 0,03 nos vizinhos da V1 (0,617 → 0,588). Ela tratava "Índice de Preços ao Produtor" como três nomes, e um release do IPCA, que contém "Índice" e "Preços", parecia ser do mesmo assunto. A segunda versão juntou os nomes ligados por conectivos e eliminou essa perda. Ainda deixava passar uma contradição no `cesta-1`, uma afirmação sem nomes; a terceira versão trata afirmação sem nomes como fora do tema. As três versões estão nos commits citados.

## Lacunas que sobram com o verificador (V1, vizinhos)

- **Indicador vizinho do mesmo mês.** Há 8 falsas refutações antes do release e 11 CONFLICTING em valores certos, quase todas vindas de outra série do mesmo mês:
  - os "preços da indústria" (IPP) contradizem a produção industrial;
  - o varejo contradiz serviços;
  - o IPCA contradiz o IPP;
  - a tabela do IPCA-15 contradiz a desocupação.

  A afirmação não tem nome próprio ("a produção industrial variou 0,9%"), então a regra de entidade não atua. Falta uma regra de **grandeza**: o sujeito medido na afirmação precisa estar ligado ao número na janela. É o mesmo problema do "maior superávit" apoiado pela corrente de comércio, agora também como contradição.
- **Outra medida do mesmo release:** "vendas cresceram 0,5% em junho" é contradito pela "média móvel trimestral variou -0,3%".
- **Variação nula:** "variou 0,0%" é contradito por "registra variação nula (0,0%)", um erro do NLI.
- **V0 quase não refuta:** com o verificador, 28 de 35 `valor_do_mes_anterior` e 31 de 35 `ipca_x_ipca15` saem NEE. É o lado seguro, mas sem refutação.

## Recomendação

1. **Manter o verificador ligado**, com as correções. O benefício com busca é grande, e o custo aparece só com evidência-ouro.
2. **Alternativa: ligar junto com a V1, manter desligada na V0.** Na V1, ela ganha 0,063 de macro-F1 no AVERITEC-BR, sem custo nos cenários com busca, ao preço de 2 falsas refutações em 424. Na V0, ela produz 14 falsas refutações. Hoje é uma chave global (`verificador.contradicao_so_fora_do_tema`, desligada); para valer por perfil, ela teria de ir para dentro de `perfis` no config, o que é decisão do dev.
3. **Próxima regra a estudar: grandeza ligada ao número.** É a maior fonte de erro que sobra no cenário com busca.

Comandos, a partir de `veritai/`, com `VERITAI_BASE` apontando para a base migrada:

```bash
.venv/bin/python eval/avaliar.py --perfil v1 --arquivo <conjunto> [--sem-verificador | --contradicao-so-fora-do-tema]
.venv/bin/python ../veritai-dados/investigacoes/teste_vizinhos.py v1 [--sem-verificador | --contradicao-so-fora-do-tema] [--codigo <worktree>]
```
