# Verificador de entidade, período e número: resultados (07/10/2026)

Código na branch local `melhorias/verificador` do veritai (worktree `veritai-dev`), sobre `dados/data-publicacao-plone`. Rode `eval/avaliar.py --sem-verificador` para a ablação com o mesmo código.

**Isto não é medição de desempenho.** Os conjuntos têm rótulos pré-anotados por IA, ainda sem revisão humana, e são pequenos: veja os intervalos de confiança. Os números servem para decidir se vale levar a proposta ao dev.

## O que o verificador faz

Entre o NLI e as regras de agregação. **Ele só rebaixa** apoio ou contradição para neutro e nunca cria um resultado:

| Regra | Bloqueia | Exemplo |
|---|---|---|
| Entidade ausente | apoio e contradição | "produção de **Pernambuco**" contra release nacional; "**IPCA**" contra release do IPCA-15 |
| Período divergente (sem contar períodos de comparação) | apoio e contradição | afirmação sobre agosto de 2026 contra janela sobre junho de 2026 |
| Número sem correspondente (valor, unidade %/p.p., direção e período do trecho) | só apoio | "0,32%" contra "-0,32%"; "subiram 0,8%" contra "caem 0,8%"; "-0,32% em julho" quando o -0,32% é de agosto |
| Ano de referência | entrada do NLI | "IPCA de dezembro", publicado em 09/01/2026, vira "dezembro de 2025" só para o NLI |

As relações neutralizadas entram nas `limitacoes` do relatório. O contrato com o FOMO não muda.

## Resultados

**Validação** (43 itens, escrita e com commit **antes** da implementação; documentos diferentes dos do diagnóstico):

| | V0 antes | V0 com verificador | V1 antes | V1 com verificador |
|---|---|---|---|---|
| Macro-F1 (IC95) | 0,288 [0,19; 0,50] | 0,406 [0,30; 0,50] | 0,423 [0,32; 0,67] | **0,572** [0,47; 0,87] |
| Falsas aprovações (IC95) | 52,4% [30; 75] | 19,0% [5; 38] | 9,5% [0; 23] | **4,8%** [0; 16] |

**Desenvolvimento** (conjunto-base-v0, 65 itens, usado para ajustar as regras e, portanto, otimista):

| | V1 antes | V1 com verificador |
|---|---|---|
| Macro-F1 | 0,436 | 0,564 |
| Falsas aprovações | 3,0% (1 item) | 6,1% (2 itens) |

**Contraste** (28 itens sintéticos, só sanidade): V0 0,530 → 0,488 e V1 0,639 → 0,608 de macro-F1; falsas aprovações iguais. A V1 perde o P06b (troca de pessoa: REFUTED → NOT_ENOUGH_EVIDENCE). A V0 perde dois apoios.

**Ponta a ponta com a base própria** (8 afirmações, sem web): V0 de 4/8 para 6/8, V1 de 5/8 para 7/8. O falso CONFLICTING causado por releases de outros meses sumiu.

## Limitações e troca de erros

- **Troca de pessoa vira "insuficiente":** quando a afirmação cita alguém que a fonte não cita, a regra de entidade impede a refutação. O erro vai para o lado seguro (NOT_ENOUGH_EVIDENCE), mas perde uma refutação legítima.
- **Mais falsas aprovações no desenvolvimento** (1 → 2 itens): "o superávit foi o maior da história" é apoiado por uma frase sobre outra grandeza (corrente de comércio). Sem números na afirmação, o verificador não tem o que conferir.
- **Não resolvido:**
  - entidade trocada dentro da mesma frase ("408 pontos em Matemática", sendo 408 a nota de Leitura);
  - recortes sem nome próprio ("jovens de 18 a 24 anos");
  - intenção ("pretende disputar").

  No V1, esses casos ainda saem REFUTED ou SUPPORTED.
- **Regras feitas à mão e ajustadas no conjunto de desenvolvimento.** O conjunto de validação foi escrito pelo mesmo autor, sabendo dos problemas, então não é cego. Antes de qualquer decisão, é preciso revisão humana dos rótulos e um conjunto de afirmações de notícias reais.
- **Ano de referência:** heurística para releases retrospectivos. Não anota datas com dia nem frases com marcas de futuro, mas pode errar em textos que citam meses futuros sem essas marcas.
- **Tempo:** a V1 continua lenta nesta máquina (cerca de 11 s por item com 1 a 3 evidências; cerca de 70 s por afirmação com a base). O verificador quase não pesa. *(08/10: a maior parte disso era o NLI carregado em float16; veja "Desempenho da V1" abaixo.)*

## Entidade ligada ao número (08/10/2026)

Branch local `melhorias/entidade-numero` (no repositório pessoal `fomo-veritai-local`). A regra de número passa a exigir também que o número da janela não esteja ligado a outra entidade. Cada número fica ligado às entidades do seu trecho de frase: até a vírgula, o ponto e vírgula, o fim de parêntese ou o "e" mais próximos, sem passar por outro número. O número da janela só deixa de valer quando duas coisas acontecem juntas: ele está ligado a outra entidade, e a entidade da afirmação está ligada a outro número da mesma janela. Assim, "0,5%, segundo o IBGE" não é bloqueado. Como as outras regras de número, esta só bloqueia o apoio.

**Ablação limpa** (mesma máquina, mesmo ambiente; o commit `ae17a22` contra a branch, em todos os conjuntos e nos dois perfis): **uma única predição muda**, o `pisa-2` ("408 pontos em Matemática", sendo 408 a nota de Leitura), de SUPPORTED para NOT_ENOUGH_EVIDENCE, tanto na V0 quanto na V1. Validação e contraste ficam idênticos.

| Desenvolvimento (65) | antes | depois |
|---|---|---|
| V0: macro-F1 / falsas aprovações | 0,408 / 6,1% | 0,411 / 3,0% |
| V1: macro-F1 / falsas aprovações | 0,568 / 9,1% | 0,564 / 6,1% |

A regra foi escrita para o caso do `pisa-2`, que está no conjunto de desenvolvimento, então isso mostra que ela funciona no caso que motivou a mudança e que não quebra os outros. Não é evidência de ganho geral. O item continua errado (o rótulo é REFUTED), mas o erro passa para o lado seguro.

**Reprodutibilidade entre máquinas.** Rodado aqui (Mac M4, Python 3.14, torch 2.14.1, transformers 5.19, só CPU), o mesmo código do commit `ae17a22` não reproduz 2 das 244 predições guardadas em `artefatos/saida/`, que vieram do Windows:
- **`pisa-2`, V1:** dá SUPPORTED aqui e NOT_ENOUGH_EVIDENCE lá. A janela decisiva tem entailment 0,720, exatamente no limiar `nli_forte` (≥ 0,72), e uma diferença numérica mínima vira o resultado.
- **`varejo-jul-2`, V0:** dá NOT_ENOUGH_EVIDENCE aqui e SUPPORTED lá, com a mesma similaridade máxima. Não identifiquei a causa.

Por isso, o dev V1 "antes" registrado acima (9,1%) difere do 6,1% anotado na seção anterior. Comparações só valem com antes e depois rodados na mesma máquina. É mais um argumento para definir os limiares por perfil e com dados revisados: hoje há decisões presas a ±0,001 do corte.

## Desempenho da V1 (08/10/2026)

Medido no Mac M4 (4 threads do torch, só CPU), com `teste_base.py` e com os 141 pares (janela, afirmação) que a análise com a base leva ao NLI nas 8 afirmações:
- **Onde ia o tempo:** de 53 s de análise, 46 s eram do NLI. O embedding e5 levava 7 s, e a busca na base menos de 1 s.
- **Causa:** o transformers 5 carrega os pesos no tipo do checkpoint, e o do mDeBERTa da V1 é **float16**. Em CPU, as multiplicações em float16 são muito lentas (no perfil do torch, `addmm` e `bmm` respondiam por 96% do tempo). A V0 não tinha o problema, porque o checkpoint dela já é float32.
- **Correção** (`veritai/modelos.py`, carregar com `.float()`): os mesmos 141 pares caem de 48,5 s para 6,7 s. O desvio máximo nas probabilidades é de 0,017 (médio de 0,0007), e nenhum par cruza o limiar de 0,72.
- **Efeito nas predições:** nenhuma muda no desenvolvimento, na validação e no contraste. Inferência do eval: dev de 95,5 s para 22,7 s; validação de 41,0 s para 9,9 s. Ponta a ponta com a base: de 53 s para 21 s nas 8 afirmações (de cerca de 6,7 s para cerca de 2,6 s por afirmação), mantendo 7/8.
- **Outras opções medidas antes da correção** (ainda em float16, por isso só valem como ordem de grandeza):
  - 8 threads em vez de 4: cerca de 13% mais rápido;
  - lotes de 4 pares ordenados por comprimento: cerca de 30% mais rápido, porque o padding de hoje ocupa 1,83 vez as posições úteis; a ordem dos pares muda as probabilidades em até 0,01;
  - quantização int8 dinâmica: não roda neste torch sem trocar o engine (`qnnpack` no ARM); não testada.

  Nenhuma dessas foi aplicada. Com o float32, o ganho que sobra é pequeno perto do risco de mexer em resultados que estão no limiar.
- **Não confirmado no i5-1334U** (Windows), onde se mediram os cerca de 70 s por afirmação. O mais provável é que fosse a mesma causa, mas é preciso medir lá.
