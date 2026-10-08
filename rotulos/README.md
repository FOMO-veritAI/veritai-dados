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

## Conjunto de vizinhos (`conjunto-vizinhos-v0.jsonl`)

Gerado por `gerar_vizinhos.py` a partir dos **títulos oficiais** dos releases mensais do IBGE que estão na base própria: IPCA, IPCA-15, IPP, construção civil, produção industrial, serviços, varejo e desocupação. O rótulo vem da construção, não de anotação (`"autor": "gerado-de-titulos"`), mas a leitura dos títulos pode errar: confira uma amostra (`"revisao": "conferir_amostra"`).

Os itens **não têm evidências**: a VeritAI busca na base, com o filtro pela data da notícia, e por isso os releases de meses vizinhos e de séries parecidas aparecem junto. É o cenário que o verificador deve proteger. Para rodar: `investigacoes/teste_vizinhos.py`.

| Tipo | Rótulo | Construção |
|---|---|---|
| `valor_certo` | SUPPORTED | valor do mês X, com a notícia datada no dia do release de X |
| `valor_do_mes_anterior` | REFUTED | valor de X-1 atribuído a X, mesma data |
| `antes_do_release` | NOT_ENOUGH_EVIDENCE | valor certo de X, com a notícia datada na véspera do release de X; só há releases de outros meses |
| `ipca_x_ipca15` | REFUTED | valor do IPCA-15 atribuído ao IPCA do mesmo mês, e vice-versa |

São 35 itens por tipo, sorteados com semente 0 entre 193 releases. O conjunto depende do conteúdo da base (`artefatos/veritai.sqlite3.gz`, migrada para o esquema 2).
