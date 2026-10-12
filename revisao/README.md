# Revisão humana dos rótulos

Os rótulos dos conjuntos da VeritAI foram feitos por IA (`claude-pre`) ou gerados automaticamente. Enquanto duas pessoas não os revisarem, **nenhum número de avaliação conta como desempenho**. Esta pasta tem tudo para a revisão:

| Arquivo | Para quê |
|---|---|
| `planilhas/revisao_M.xlsx`, `planilhas/revisao_I.xlsx` | uma pasta de trabalho por anotador, **cega**: sem o rótulo nem a justificativa da IA |
| `gerar_planilhas.py` | gera as planilhas (só rode de novo se os conjuntos mudarem; isso apaga o que foi preenchido) |
| `consolidar.py` | mede a concordância, lista as divergências e grava as classes finais nos conjuntos |

## Regras do processo

1. **Cada um preenche só a própria planilha,** sem conversar sobre os itens nem olhar a do outro.
2. **Não abra os arquivos de rótulos** (`rotulos/*.jsonl`, `mapeamento/revisao-checagens.csv`) durante a anotação: eles mostram a resposta da IA.
3. Preencha só as colunas amarelas. As colunas de classe têm lista suspensa: use só os valores dela.
4. Na dúvida, escolha a melhor opção, marque `confianca` = baixa e explique na `observacao`. Não deixe em branco: em branco não entra na concordância.
5. Pode fazer em várias sessões; salve o arquivo com o mesmo nome. Uma estimativa grosseira de tempo total por pessoa: de 6 a 8 horas, divididas assim:
   - Afirmações: 2 a 3 h;
   - Checagens: cerca de 2 h, porque é preciso abrir os artigos;
   - Vizinhos: 30 min;
   - Extração: 2 a 3 h.

## Aba "Afirmações" (108 itens: desenvolvimento + validação)

Leia a afirmação e as evidências da linha. **Julgue só pelo que as evidências mostradas dizem**, na data da notícia, sem usar o que você sabe de fora: é exatamente o que a VeritAI vê.

| Classe | Quando |
|---|---|
| `apoiada` | As evidências confirmam a afirmação: mesmo fato, mesma entidade, mesmo período, mesmo valor. |
| `refutada` | As evidências mostram que a afirmação está errada: outro valor para a mesma coisa no mesmo período, direção oposta (subiu × caiu), data errada. |
| `insuficiente` | As evidências tratam do assunto, mas não confirmam nem desmentem: outro período, outra entidade, o número não aparece. |
| `conflitante` | Uma evidência confirma e outra desmente. É raro nestes conjuntos. |

**Casos difíceis**

| Caso | Exemplo | Classe |
|---|---|---|
| Troca de entidade com o valor certo na mesma frase | "408 pontos em Matemática"; a evidência diz "408 em Leitura, 377 em Matemática" | `refutada`: a evidência dá o valor de Matemática |
| Mês vizinho | Afirmação sobre julho; a evidência é o release de agosto | `insuficiente`, se o valor de julho não aparece |
| Mês vizinho citado no release | O release de agosto cita "abaixo dos 0,07% de julho" | Pode apoiar ou refutar a afirmação sobre julho |
| Ano implícito | "O IPCA de dezembro", num release de 09/01/2026 | É dezembro de 2025: use a data da evidência |
| Arredondamento | "mais de 152 mil inscritos" × 152.966 | `apoiada` |
| Ordem de grandeza | "cerca de 1.300 sites" × 13.241 | `refutada` |
| Afirmação sobre outro recorte | "jovens de 18 a 24 anos", quando a evidência só tem o total | `insuficiente` |
| Intenção ou previsão | "pretende disputar"; a evidência não fala disso | `insuficiente` |

## Aba "Checagens" (45 itens)

Abra o artigo da agência (`url`) e classifique **a alegação checada**, segundo o que o artigo conclui. O `veredito_original` é a palavra da agência ("Enganoso", "Sem contexto"…); ele ajuda, mas não deve ser convertido mecanicamente.

| Classe | Quando |
|---|---|
| `refutada` | A afirmação central é falsa, mesmo que a agência diga "enganoso". Exemplo: "o IBGE maquiou o desemprego", quando o critério é o mesmo desde 2012. |
| `conflitante` | Há partes verdadeiras e partes falsas relevantes, ou dado verdadeiro usado para uma conclusão errada (cherry-picking). |
| `apoiada` | O artigo confirma a afirmação, mesmo com ressalvas menores. |
| `insuficiente` | A agência não conseguiu concluir ("insustentável", "ainda é cedo"). |
| `fora_de_escopo` | Não é afirmação factual verificável: pergunta, opinião, previsão, fala contraditória. |

## Aba "Vizinhos" (amostra de 20)

São afirmações geradas dos títulos dos releases do IBGE; aqui se confere se a construção acertou. Abra o release indicado (`release_url`). Julgue **considerando só o que estava publicado até a `data_noticia`**: se o release foi publicado depois dela (`release_publicado_em`), ele não conta, e a resposta tende a ser `insuficiente`.

## Abas "Extração" e "Faltantes"

Siga o guia em `../rotulos/extracao-v0/README.md`: para cada afirmação proposta, responda `verificavel`, `atomica` e `compreensivel_sozinha` (s/n) e corrija o texto se preciso. Em "Faltantes", liste o que o extrator deixou passar, uma afirmação por linha dentro da célula, ou "nenhuma".

## Depois da anotação

Com as duas planilhas preenchidas em `planilhas/`, a partir de `veritai-dados/` e com o ambiente do `veritai`:

```bash
PY=../veritai/.venv/bin/python        # precisa do openpyxl: $PY -m pip install openpyxl
$PY revisao/consolidar.py             # resultado/resumo.md e resultado/divergencias.xlsx
```

1. **Leiam o `resultado/resumo.md`:** concordância e kappa por aba. Como referência:
   - kappa ≥ 0,8: concordância forte;
   - de 0,6 a 0,8: substancial;
   - abaixo de 0,6: o guia está ambíguo e precisa ser revisto antes de seguir.
2. **Discutam juntos as divergências** em `resultado/divergencias.xlsx`. Só agora aparece o rótulo proposto pela IA. Preencham `classe_final` em cada linha.
3. **Rodem `$PY revisao/consolidar.py --aplicar`.** As classes acordadas e as finais vão para os conjuntos:
   - nos JSONL, `rotulo` passa a ser o humano, o anterior fica em `rotulo_pre`, `revisao` vira `"humana"` e `revisores` guarda as duas respostas;
   - nas checagens, a classe da IA fica em `classe_ia`.

   Itens sem classe final continuam pendentes.
4. **Rodem de novo as avaliações** (`eval/avaliar.py` e a bateria). Só então os números passam a valer como medição, e os limiares podem ser definidos.
