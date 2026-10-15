# VeritAI - Dados

Repositório destinado à organização, preparação, validação e análise dos dados utilizados pela **VeritAI**, serviço de Inteligência Artificial responsável pela análise de confiabilidade das afirmações no contexto do FOMO.

Hoje há aqui:

- a análise exploratória dos conjuntos públicos (`eda/`);
- a lista de fontes, a coleta e a carga da base própria de evidências e checagens;
- os conjuntos rotulados e a revisão humana;
- a avaliação, com o notebook da entrega da semana 5.

O serviço e o formato da base ficam no repositório [veritai](https://github.com/FOMO-veritAI/veritai) (`veritai/base/`).

Nada aqui decide resultado. Esta parte só escolhe e carrega os documentos que a VeritAI vai comparar com as afirmações.

## Objetivos

Este repositório concentra as atividades relacionadas a:

- construção e validação do conjunto rotulado em português brasileiro;
- controle de qualidade dos dados;
- análise exploratória dos conjuntos utilizados;
- análise da concordância entre anotadores;
- preparação dos dados para avaliação dos modelos;
- análise de erros e resultados;
- prevenção de vazamento entre conjuntos de treino, validação, calibração e teste.

## Estrutura

```text
eda/                análise exploratória do AVERITEC-BR, do AVeriTeC e do LIAR-BR (notebooks de Isabel Azar e relatório da semana 3)
fontes/fontes.md    fontes propostas, como cada uma entra, robots.txt, licença e situação
coleta/listar.py    monta um manifesto (JSONL) por fonte: url, fonte, titulo, data e, na API do IBGE, texto
coleta/carregar.py  carrega manifestos na base com a carga da própria VeritAI
coleta/consultas-checagens.txt  consultas ao Google Fact Check (importar-checagens --consulta)
mapeamento/vereditos.csv  proposta: veredito da agência → 4 classes da VeritAI
mapeamento/aplicar.py     aplica o mapeamento às checagens da base e gera a planilha de revisão
averitec/converter.py     AVeriTeC/AVERITEC-BR (dev) → formato do eval/avaliar.py, só como teste de estresse (CC BY-NC 4.0; dados fora do git)
averitec/analisar.py      quebra as predições por classe, tipo de alegação e estratégia
rotulos/gerar_vizinhos.py conjunto de vizinhos (releases do IBGE, rótulo pelo título oficial) para testar com busca na base
investigacoes/teste_vizinhos.py  roda o conjunto de vizinhos com busca na base própria
extracao/extrair_noticias.py      extração por regras nas notícias da base e amostra para anotação (rotulos/extracao-v0/)
revisao/                  revisão humana dos rótulos: planilhas cegas por anotador, guia e consolidação (kappa)
rotulos/                  conjuntos rotulados (ver a tabela abaixo) e os scripts que os geram
avaliacao/avaliacao_veritai.ipynb  notebook da entrega: carrega os modelos, analisa uma notícia e mede os conjuntos
avaliacao/bateria.py      perfis × configurações do verificador × conjuntos, num comando só
avaliacao/limiares.py     varredura dos limiares (figuras em avaliacao/figuras/)
investigacoes/            análises de erros e experimentos, cada uma com o seu relatório em Markdown
saida/              manifestos e lotes locais (fora do git)
```

## Conjuntos de dados

| Conjunto | Onde | Tamanho | Como foi feito | Estado dos rótulos |
|---|---|---|---|---|
| Base própria de evidências | gerada por `coleta/` (o arquivo SQLite não vai para o git) | 590 documentos (IBGE 300, Agência Gov 100, INEP 100, Agência Brasil 90), 2.164 trechos | coleta respeitando `robots.txt` e `Crawl-delay`, sem contornar bloqueio anti-robô | não se aplica |
| Checagens | na base própria; mapeamento em `mapeamento/` | 102 checagens de 8 agências; 45 com classe revisada | Google Fact Check Tools (ClaimReview) | veredito original da agência, mais a classe proposta e conferida por um anotador |
| Desenvolvimento | `rotulos/conjunto-base-v0.jsonl` | 65 afirmações, 20 eventos | escritas por IA a partir de evidências reais da base | conferidos por um anotador |
| Validação | `rotulos/conjunto-validacao-v0.jsonl` | 43 afirmações | idem, separado antes de qualquer ajuste de regra | conferidos por um anotador |
| Vizinhos | `rotulos/conjunto-vizinhos-v0.jsonl` | 140 afirmações, 4 tipos × 35 | gerados dos títulos oficiais dos releases do IBGE; a VeritAI busca na base | rótulo pela construção; amostra de 12 conferida |
| Notícias reais | `rotulos/noticias-reais-v0/` | 71 afirmações de 29 notícias | extraídas pelo `/extrair` de notícias da base | conferência por IA; a conferência humana cega está pendente |
| Extração | `rotulos/extracao-v0/` | 150 candidatas de 30 notícias | saída do `/extrair` para anotar | pré-rótulos por IA |
| Contraste | `eval/contraste.jsonl` no repositório veritai | 28 itens | perturbações controladas | só sanidade, não mede desempenho |

O AVeriTeC e o AVERITEC-BR entram só como teste de estresse (`averitec/`), com os dados fora do git (CC BY-NC 4.0). Os detalhes e limites de cada conjunto estão em `rotulos/README.md`.

**Licença dos textos:** os conjuntos guardam trechos curtos dos documentos, com a fonte, a data e a URL de cada um. As fontes e as licenças estão em `fontes/fontes.md`:
- Agência Brasil: CC BY 4.0;
- INEP: CC BY-ND 3.0, que permite reproduzir sem alterar e com atribuição;
- IBGE e Agência Gov: conteúdo de órgão público, reproduzido com citação da fonte; os termos exatos ainda precisam ser confirmados.

## Como rodar

Use o ambiente do repositório `veritai`, clonado ao lado deste, com o extra `modelos` instalado.

```bash
PY=../veritai/.venv/Scripts/python          # no Linux/Mac: ../veritai/.venv/bin/python
$PY coleta/listar.py ibge --quantidade 300
$PY coleta/listar.py agencia-gov --quantidade 100
$PY coleta/listar.py inep --quantidade 100
$PY coleta/listar.py agencia-brasil
$PY coleta/carregar.py saida/manifestos/*.jsonl
cd ../veritai
.venv/Scripts/python -m veritai.base indexar --perfil v0
.venv/Scripts/python -m veritai.base indexar --perfil v1
.venv/Scripts/python -m veritai.base estatisticas
```

A base fica em `../veritai/data/veritai.sqlite3`, o mesmo caminho padrão da API (`VERITAI_BASE`). Ela não vai para o git.

Rode a carga com o `veritai/` deste repositório, que já lê a data de publicação das páginas do gov.br (antes, a branch `dados/data-publicacao-plone`). Sem isso, essas páginas entram sem data (detalhes em `fontes/fontes.md`).

## Regras

- **Só fontes da lista aprovada pelo grupo.** A lista de `fontes/fontes.md` ainda é uma proposta.
- **Sem coleta em massa:**
  - no máximo 100 URLs por carga e uma página por vez;
  - respeitar o `robots.txt` e o `Crawl-delay`;
  - nunca contornar bloqueio anti-robô (Cloudflare, Akamai).
- **Nunca carregar as notícias fictícias da interface do FOMO.**
- **Chave do Google Fact Check só no `.env` do veritai**, nunca no código nem no git.
- **Checagens:** guardar o veredito como a agência escreveu. O mapeamento para as 4 classes (`mapeamento/vereditos.csv`) é uma proposta desta área, conferida por um anotador em 45 checagens.
