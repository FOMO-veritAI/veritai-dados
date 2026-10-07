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
- **Tempo:** a V1 continua lenta nesta máquina (cerca de 11 s por item com 1 a 3 evidências; cerca de 70 s por afirmação com a base). O verificador quase não pesa.
