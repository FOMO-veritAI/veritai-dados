# Conjunto rotulado (v0, pré-rotulagem)

`conjunto-base-v0.jsonl` está no formato do `eval/avaliar.py` da VeritAI. Ele é gerado por `gerar_conjunto.py`, que lê as evidências da base própria: texto, URL, data e `documento_base` reais.

## Estado: pendente de revisão humana

As afirmações e os rótulos foram escritos por IA (`"autor": "claude-pre"`) a partir de documentos reais, e todos os itens estão com `"revisao": "pendente_humano"`.

Antes de usar o conjunto para escolher limiares ou como teste:
1. **Dupla anotação:** duas pessoas rotulam cada item sem ver o rótulo proposto.
2. **Concordância:** medir o kappa; discordâncias se resolvem em discussão.
3. **Registro:** atualizar `revisao`, `autor` e `justificativa`.

## O que tem

| Tipo | O que testa |
|---|---|
| `parafrase` | Afirmação correta, reescrita |
| `numero_alterado` | Número trocado (casa decimal, ordem de grandeza) |
| `direcao_invertida` | Subiu ↔ caiu, maior ↔ menor |
| `periodo_trocado` | Valor de outro mês, trimestre ou ano |
| `entidade_trocada` | Número de outra entidade (Enamed × Revalida, Leitura × Matemática) |
| `ipca_x_ipca15` | Indicadores de nome parecido |
| `armadilha_temporal` | Evidência certa junto com releases do mesmo indicador em outros meses: o rótulo continua SUPPORTED |
| `sem_evidencia` | O assunto aparece na evidência, mas a resposta não |

## Limitações

- **Sem CONFLICTING_EVIDENCE:** não há, na base, duas fontes que divirjam de verdade sobre o mesmo fato.
- **Sintéticas ancoradas em evidência real:** as afirmações não vêm de notícias reais, então medem o comparador e as regras, não a extração de afirmações.
- **Separação por evento:** use o campo `evento` (20 eventos). Itens do mesmo evento compartilham a evidência e não podem ficar em partições diferentes.
- **Recorte limitado:** o conjunto é pequeno (65 itens) e concentrado em economia (IBGE) e educação (INEP).
