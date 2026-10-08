# Extração de afirmações por regras, abordagem A (08/10/2026)

O módulo é `veritai/extracao.py`: uma função pura, `extrair(titulo, texto, data)`, ainda **sem endpoint**. Um `/extrair` muda o contrato com o FOMO e precisa ser combinado com o dev. Não há LLM.

## Como funciona

1. **Frases:** o título e o texto são divididos por parágrafo e por fim de frase, sem partir abreviações ("p.p.", "Dr.") nem iniciais ("Robert E. Lee"). Partes separadas por ponto e vírgula viram candidatas próprias.
2. **Descarte:**
   - rotina de página (navegação, "Publicado em", créditos, rodapé como "Compartilhe essa notícia" ou "Relacionadas");
   - tamanho fora de 6 a 70 palavras;
   - pergunta;
   - opinião (exclamação, primeira pessoa, léxico avaliativo);
   - frase sem número, nome próprio ou data.
3. **Pontuação:** número +2; período +1; nome próprio +1; atribuição ("segundo", "informou") +1; verbo de fato +1; futuro ou intenção −1. Fica quem soma 3 ou mais. Saem no máximo 10 candidatas (o limite do `/analisar`), das mais fortes para as mais fracas, sem repetir frases quase iguais com os mesmos números.
4. **Datas completadas pela data da notícia,** a única descontextualização feita:
   - meses sem ano ganham o ano;
   - "nesta terça-feira (6)" vira "nesta terça-feira (6 de outubro de 2026)", conferido o dia da semana no calendário.
5. **Alertas para o publicador:**
   - sem período;
   - depende da frase anterior (começa com "Isso", "A taxa"… ou é um fragmento do ponto e vírgula);
   - futuro ou intenção;
   - citação.

Também são registrados os sinais e a atribuição ("segundo o IBGE" → `IBGE`).

## Resultados

**Notícias da base** (290: Agência Brasil, Agência Gov e gov.br/INEP; `extracao/extrair_noticias.py`):
- **Volume:** 1.415 candidatas, mediana de 4 por notícia, 54 notícias no limite de 10 e 10 notícias sem nenhuma.
- **Alertas:**

  | Alerta | Candidatas |
  |---|---|
  | sem período | 40% |
  | depende da frase anterior | 8% |
  | futuro ou intenção | 6% |
  | citação | 5% |

- **Datas completadas:** 115 candidatas tiveram a data completada.
- **Sem medida de qualidade ainda:** não há anotação. A amostra de 30 notícias (153 candidatas) e o guia estão em `rotulos/extracao-v0/`.

**CheckThat! 2025 T2 PT** (`veritai/eval/avaliar_extracao.py`; posts de rede social contra a alegação normalizada):

| Teste (225 posts) | F1 de palavras | ROUGE-L | Cobertura da referência |
|---|---|---|---|
| Extrator (1ª candidata) | 0,100 | 0,091 | 0,128 |
| Post inteiro, limpo | 0,323 | 0,289 | 0,598 |
| Primeira frase do post | 0,311 | 0,283 | 0,365 |

O extrator não propõe nada em 72% dos posts (74% no dev). Os motivos de descarte das frases desses posts:

| Motivo | Frases |
|---|---|
| sem número, nome nem data | 179 |
| opinião | 123 |
| tamanho | 121 |
| pontuação baixa | 150 |
| pergunta | 46 |

É o comportamento esperado para posts opinativos, não para notícias de veículo verificado. Nos 63 posts em que o extrator propõe algo, a primeira candidata tem F1 de 0,357, contra 0,330 do post inteiro e 0,341 da primeira frase. O CheckThat! não serve para medir esta abordagem: a referência é uma reescrita com informação de fora do post. O METEOR oficial não foi calculado, para não acrescentar dependência.

## Defeito achado de passagem (corrigido)

O `anotar_ano` do verificador tratava "Rio de Janeiro" como o mês de janeiro ("no Rio de Janeiro de 2026") na entrada do NLI. Corrigido no verificador e no extrator. Efeito na V1: o `v-pim-go` da validação passa de NEE para SUPPORTED (macro-F1 de 0,572 para 0,589); nada muda no desenvolvimento, no contraste nem no AVERITEC-BR.

## Limites da abordagem A

- **Não descontextualiza:** "A taxa caiu para 5,3%" continua sem dizer qual taxa; só as datas são completadas.
- **Não separa fatos ligados por "e" na mesma oração.**
- **Não decide se vale checar:** a pontuação é heurística. A ordem das candidatas não é importância jornalística.
- **Regras de operação,** não validadas: a anotação da amostra é o próximo passo.
