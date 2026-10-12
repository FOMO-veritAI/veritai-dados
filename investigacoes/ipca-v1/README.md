# Investigação: itens de IPCA saem NOT_ENOUGH_EVIDENCE na V1 (07/10/2026)

Rode os scripts a partir do repositório `veritai`, com o `.venv` dele:

```bash
.venv/Scripts/python ../veritai-dados/investigacoes/ipca-v1/rastro_ipca.py v1 ipca-ago-1,ipca15-set-1
```

## Causa: o ano não está na evidência

Os releases do IBGE vindos da API dizem "o IPCA **de agosto** foi de -0,32%" sem o ano. A afirmação diz "agosto **de 2026**". O NLI responde "neutro", e isso é tecnicamente correto: a premissa não sustenta o ano. Os releases que trazem "Em agosto de 2026" (produção industrial, PNAD) não têm o problema.

O rastro (`rastro_ipca.py`) descarta as outras hipóteses (sinal negativo, "p.p.", fragmento cortado no fim, janela grande). Os pares controlados de `nli_ipca.py` dão, no V1:

| Premissa × hipótese | Apoio |
|---|---|
| Release sem ano × "setembro de 2026" | 0,001 |
| Release sem ano × "setembro" (sem ano) | 0,996 |
| Release com "setembro de 2026" no texto | 0,978 |

**Abrangência:** 50 dos 300 releases do IBGE na base não têm nenhum ano no texto. As outras fontes (Agência Gov, INEP, Agência Brasil) não têm o problema.

## Correção ingênua: perigosa

Pôr "Publicado em DD/MM/AAAA." na frente da evidência faz o modelo supor que o mês é do ano da publicação (`nli_risco.py`):

| Premissa × hipótese | Apoio |
|---|---|
| "Publicado em 10/01/2026. IPCA de dezembro…" × "dezembro de 2025" (certo) | 0,023 |
| A mesma premissa × "dezembro de 2026" (errado) | **0,970** |

Os releases de janeiro falam de dezembro do ano anterior. Essa correção gera **falsas aprovações**.

## Alternativa testada: período de referência por regra

Regra: o mês citado no título, no ano mais recente em que ele não é posterior à publicação. Um release de 10/01/2026 sobre dezembro vira "dezembro de 2025". Com "Período de referência: dezembro de 2025." na frente, o caso de risco se inverte corretamente: 0,986 para o certo e 0,002 para o errado.

Nos 9 itens de IPCA e IPCA-15 (`teste_referencia.py`, V1), os acertos passam de 1 para 5. Mas surgem dois problemas que o ano ausente escondia:

1. **O NLI ignora o sinal negativo.** "O IPCA de agosto foi de 0,32%" (o real foi -0,32%) passa a sair **SUPPORTED**: é uma falsa aprovação.
2. **IPCA × IPCA-15 do mesmo domínio vira CONFLICTING.** Com os dois releases como evidência, o do outro índice "contradiz", e as regras não sabem que é outro indicador.

## Recomendação

- **Não aplicar a correção do ano sozinha.** Ela troca "evidência insuficiente" (seguro) por falsa aprovação nos casos de sinal.
- **Levar ao dev junto com o verificador numérico** (incremento previsto no fluxo v3): extrair números com sinal e unidade e só decidir quando entidade, unidade e período coincidem.
- **Onde pôr o período de referência:** como metadado da base (campo próprio, preenchido na carga) e não reescrevendo o texto da fonte. Isso exige mudança de esquema na VeritAI.
- **Conjunto rotulado:** incluir mais casos de sinal (−x × x) e de mês de virada de ano (dezembro publicado em janeiro).
