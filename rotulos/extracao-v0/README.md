# Anotação da extração de afirmações (v0)

Material para avaliar a extração por regras (`veritai/extracao.py`, abordagem A, sem LLM) em notícias reais da base: Agência Brasil, Agência Gov e gov.br/INEP. A amostra é de 30 notícias sorteadas com semente 0, gerada por `extracao/extrair_noticias.py`.

**Para anotar, use as abas "Extração" e "Faltantes" das planilhas em `../../revisao/planilhas/`**, que já têm as listas suspensas e não mostram pontuação, sinais nem alertas. Os CSVs abaixo são a origem dessas abas.

- `anotacao.csv`: uma linha por afirmação proposta pelo extrator (150 nesta amostra).
- `faltantes.csv`: uma linha por notícia, para listar o que o extrator deixou passar.

Abra a notícia pela URL e leia o texto inteiro antes de anotar. **Dois anotadores, sem ver as respostas um do outro**; o anotador escreve o próprio nome na coluna `anotador`. Depois, mede-se a concordância (kappa) e as divergências são discutidas.

## O que é uma afirmação para a VeritAI

Um fato que uma fonte pública pode confirmar ou desmentir. Não entram:
- opinião ou avaliação: "a medida foi um sucesso";
- previsão ou intenção sem agenda oficial: "o ministro pretende ampliar o programa";
- frases de serviço sem fato: "os portões abrem às 12h" (só entra se o horário em si for a notícia).

## Colunas a preencher em `anotacao.csv`

| Coluna | Pergunta | Valores |
|---|---|---|
| `verificavel (s/n)` | É um fato que uma fonte pública pode confirmar ou desmentir? | s / n |
| `atomica (s/n)` | Tem um fato só? "O PIB cresceu 0,5% e o desemprego caiu" tem dois. | s / n |
| `compreensivel_sozinha (s/n)` | Dá para verificar sem ler a notícia? Precisa dizer quem, o quê, onde e quando. "A taxa caiu para 5,3%" não diz qual taxa. | s / n |
| `afirmacao_corrigida` | Se a resposta anterior foi "n" (ou a afirmação está mal recortada), reescreva como deveria ser, usando só o que está na notícia. | texto |
| `observacao` | Qualquer coisa útil: lixo de página, data errada, citação etc. | texto |

As colunas `sinais` e `alertas` mostram por que o extrator propôs a frase e o que ele pede para conferir. Elas não são a resposta: anote pelo texto. A coluna `afirmacao_proposta` pode ter a data completada pelo extrator ("nesta terça-feira (6 de outubro de 2026)"); confira se a data está certa.

## `faltantes.csv`

Para cada notícia, liste em `afirmacoes_faltantes` as afirmações verificáveis importantes que **não** estão entre as propostas (uma por linha dentro da célula), já escritas para serem compreensíveis sozinhas. Se não faltar nada, escreva "nenhuma".

## O que se mede depois

- **Precisão:** fração das propostas marcadas como verificáveis.
- **Qualidade:** fração das verificáveis que são atômicas e compreensíveis sozinhas, que é o que a abordagem com LLM precisaria melhorar.
- **Cobertura:** propostas verificáveis ÷ (propostas verificáveis + faltantes).
- **Efeito no veredito:** rodar o `/analisar` com as afirmações propostas e com as corrigidas.

Os textos da base são páginas achatadas; o script corta o cabeçalho de cada portal, mas sobras de página ainda aparecem. Marque-as como "n" em `verificavel` e anote na observação.
