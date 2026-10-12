# Conjunto de notícias reais (v0): conferência cega

São 71 afirmações tiradas de 29 notícias reais da base (Agência Brasil, Agência Gov, gov.br/INEP) pela extração do `/extrair`. Ficaram as candidatas que a pré-rotulagem marcou como verificáveis e com um fato só, na versão corrigida quando havia (55 delas). Cada uma foi analisada pela VeritAI (perfil V1, base própria, sem web) com a notícia de origem e as cópias dela **fora da busca**: no FOMO, a notícia ainda não foi publicada quando é analisada. Gerado por `investigacoes/noticias_reais.py`.

## Arquivos

| Arquivo | O que é | Abrir antes de conferir? |
|---|---|---|
| `conferencia.csv` | afirmação e evidências que a VeritAI mostrou, sem o resultado dela | **sim**, é aqui que se anota |
| `predicoes-veritai.jsonl` | o resultado da VeritAI e a relação de cada evidência | **não** |
| `conferencia-ia.csv` | a mesma conferência feita por IA (subagente Claude Haiku, às cegas) | **não** |

## Como conferir

Em `conferencia.csv`, para cada linha, preencha a coluna `rotulo` com o resultado que a verificação **deveria** dar, **julgando só pelos trechos mostrados** em `evidencias` (não use o que você sabe de fora):

| Rótulo | Quando |
|---|---|
| `apoiada` | algum trecho confirma: mesmo fato, mesma entidade, mesmo período, mesmo valor |
| `refutada` | algum trecho mostra que está errada: outro valor para a mesma coisa no mesmo período, direção oposta, data ou entidade trocada |
| `insuficiente` | os trechos não confirmam nem desmentem (outro assunto, outro período, o dado não aparece). Falta de evidência é `insuficiente`, nunca `refutada` |
| `conflitante` | um trecho confirma e outro desmente |

Use só esses quatro valores, em minúsculas. A `observacao` é livre. Escreva seu nome em `anotador`.

## Depois

```bash
python investigacoes/comparar_conferencias.py
```

O script mostra a concordância e o kappa entre humano e IA, humano e VeritAI, e IA e VeritAI, com as divergências, e as métricas da VeritAI tomando a sua conferência como referência.

**Limites:** as afirmações vêm da pré-rotulagem por IA da extração, e as versões corrigidas foram escritas pela IA a partir da notícia. A evidência é só a da base própria (590 documentos), então muitas afirmações não têm documento que trate delas.
