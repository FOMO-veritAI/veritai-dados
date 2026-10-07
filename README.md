# veritai-dados

Dados da **VeritAI**: lista de fontes, coleta e carga da base própria de evidências e checagens. O serviço e o formato da base ficam no repositório [veritai](https://github.com/FOMO-veritAI/veritai) (`veritai/base/`).

Nada aqui decide resultado. Esta parte só escolhe e carrega os documentos que a VeritAI vai comparar com as afirmações.

## Estrutura

```text
fontes/fontes.md    fontes propostas, como cada uma entra, robots.txt, licença e situação
coleta/listar.py    monta um manifesto (JSONL) por fonte: url, fonte, titulo, data e, na API do IBGE, texto
coleta/carregar.py  carrega manifestos na base com a carga da própria VeritAI
coleta/consultas-checagens.txt  consultas ao Google Fact Check (importar-checagens --consulta)
mapeamento/vereditos.csv  proposta: veredito da agência → 4 classes da VeritAI
mapeamento/aplicar.py     aplica o mapeamento às checagens da base e gera a planilha de revisão
saida/              manifestos e lotes locais (fora do git)
```

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

Rode a carga com a branch `dados/data-publicacao-plone` do veritai. Sem ela, as páginas do gov.br entram sem data (detalhes em `fontes/fontes.md`).

## Regras

- **Só fontes da lista aprovada pelo grupo.** A lista de `fontes/fontes.md` ainda é uma proposta.
- **Sem coleta em massa:**
  - no máximo 100 URLs por carga e uma página por vez;
  - respeitar o `robots.txt` e o `Crawl-delay`;
  - nunca contornar bloqueio anti-robô (Cloudflare, Akamai).
- **Nunca carregar as notícias fictícias da interface do FOMO.**
- **Chave do Google Fact Check só no `.env` do veritai**, nunca no código nem no git.
- **Checagens:** guardar o veredito como a agência escreveu. O mapeamento para as 4 classes é tarefa desta área e ainda não foi feito.
