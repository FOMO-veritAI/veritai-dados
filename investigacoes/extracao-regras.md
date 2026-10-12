# Extração de afirmações por regras, abordagem A (08/10/2026)

O módulo é `veritai/extracao.py`, exposto em `POST /extrair` (contrato no README do veritai). O endpoint só propõe candidatas: o publicador confirma, edita ou descarta cada uma antes do `/analisar`. Não há LLM.

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
- **Volume:** 1.371 candidatas, mediana de 3 por notícia, 54 notícias no limite de 10 e 12 notícias sem nenhuma.
- **Alertas:**

  | Alerta | Candidatas |
  |---|---|
  | sem período | 39% |
  | futuro ou intenção | 9% |
  | depende da frase anterior | 7% |
  | citação | 6% |

- **Datas completadas:** 111 candidatas tiveram a data completada.
- **Sem medida de qualidade ainda:** não há anotação. A amostra de 30 notícias (150 candidatas) e o guia estão em `rotulos/extracao-v0/`.
- **Números após dois ajustes** feitos ao testar o endpoint: o ordinal "segundo maior" não é mais lido como atribuição, e "será" passou a contar como futuro. A primeira rodada deu 1.415 candidatas.

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

## Pré-rotulagem da amostra por IA (08/10/2026)

As 150 candidatas da amostra (29 notícias com candidatas) foram rotuladas por um subagente com o Claude Sonnet. Ele recebeu o texto da notícia e as candidatas, **sem** pontuação, sinais e alertas do extrator. O resultado está em `rotulos/extracao-v0/pre-rotulos-ia.csv` (`anotador = claude-sonnet-pre`, `revisao = pendente_humano`), separado do `anotacao.csv`, que continua em branco para a anotação humana cega.

**É pré-rotulagem, não medida.** Nas afirmações e checagens, a revisão humana relatada concordou com todos os rótulos da IA. Mesmo assim, estes números só contam depois de conferidos.

| Medida (pré-rótulos) | Valor |
|---|---|
| Candidatas verificáveis | 135/150 (90%) |
| Entre as verificáveis: um fato só | 53% |
| Entre as verificáveis: compreensíveis sozinhas | 22% |
| Entre as verificáveis: as duas coisas (prontas para o `/analisar` sem edição) | 16 (12%) |

O que isso diz sobre a abordagem A:
- **Escolha das frases:** as regras escolhem bem *quais* frases propor; 90% são fatos verificáveis.
- **Edição necessária:** quase todas precisam de edição. Falta sujeito ou ano, ou a frase junta vários fatos. É o argumento para a abordagem com LLM e travas, que descontextualiza e separa.
- **Valor dos alertas do extrator:**

  | Alerta | Candidatas | Efeito |
  |---|---|---|
  | sem período | 70 | 96% não compreensíveis sozinhas, contra 65% sem o alerta |
  | depende da frase anterior | 10 | 100% não compreensíveis |
  | citação | 7 | 43% não verificáveis, contra 8% |
  | futuro ou intenção | 12 | quase não distingue (83% contra 79%) |

- **Sobras de página:** o subagente marcou intertítulos grudados em várias candidatas ("Região Nordeste Sábado (3)"). Isso vem do texto achatado da base, não do extrator; o texto do publicador teria quebras de linha.

**Defeitos do extrator achados pelo subagente** (c085, c089), ambos no `anotar_ano` do verificador, que também prepara a entrada do NLI. Foram corrigidos:
- **intervalo:** em "entre outubro e dezembro", publicado em outubro de 2026, dezembro virava **2025**. Agora o segundo mês segue o primeiro;
- **ano por extenso:** "setembro do ano passado" virava "setembro de 2026 do ano passado". Agora não se acrescenta ano quando ele já vem dito.

Na V1, rodado antes e depois, nenhuma predição muda nos releases (dev, validação, contraste), no AVERITEC-BR nem nos vizinhos. A amostra de anotação **não** foi regenerada: ela continua com as propostas da versão `regras-2026-10-08`, para que as anotações humanas e os pré-rótulos se refiram ao mesmo texto.

Dúvidas registradas pelo subagente, que valem para a revisão humana:
- **c106 e c020:** horário de apostas e de programa de rádio, que podem ser lidos como frase de serviço;
- **c126:** declaração de uma das partes;
- **c139:** texto cortado no limite de 6.000 caracteres da entrada.
