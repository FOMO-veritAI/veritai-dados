# Fontes da base própria: proposta inicial

**Situação:** proposta para aprovação do grupo. Pelo `AGENTS.md` da VeritAI, a base só pode ser carregada a partir da lista de fontes confiáveis definida pelo grupo. Esta lista foi usada na primeira carga local, em 06/10/2026, e precisa ser confirmada (ou corrigida) antes de qualquer base compartilhada.

Cada fonte foi conferida em 06/10/2026 com o User-Agent da VeritAI (`VeritAI/0.1 (local research prototype)`).

| Fonte | Como entra | Data de publicação | robots.txt e acesso | Licença (a confirmar pelo grupo) | Situação |
|---|---|---|---|---|---|
| IBGE: releases da Agência de Notícias | API pública oficial `servicodados.ibge.gov.br/api/v3/noticias` (tipo `release`). Entra título + parágrafo de abertura; a URL registrada é a do release. | Campo `data_publicacao` da API | O site da agência responde 403 com desafio anti-robô do Cloudflare. **Não contornar.** A API de dados é o canal oficial para acesso automatizado. | Conteúdo público do IBGE; reprodução permitida citando a fonte (confirmar termos) | Carregada (300 releases mais recentes) |
| Agência Gov (EBC), notícias do governo federal | `sitemap.xml.gz` → página HTML lida pelo leitor da VeritAI | `DC.date.valid_range` da página (exige o ajuste do leitor descrito abaixo) | `Disallow: /*?`: nada de busca com parâmetros; o sitemap é permitido | Conteúdo de órgão público (confirmar) | Carregada (100 mais recentes) |
| INEP (gov.br) | Páginas de categoria de `centrais-de-conteudo/noticias` → página HTML | `datePublished` do JSON-LD da página (mesmo ajuste) | Permitido. Não há sitemap do INEP. | **CC BY-ND 3.0**, declarada no rodapé: atribuição, sem obras derivadas. Guardar trechos e citar é uso compatível, mas confirmar com o grupo. | Carregada (até 100, distribuídas pelas categorias) |
| Agência Brasil (EBC) | Feeds RSS por editoria → página HTML | `article:published_time`; o `pubDate` do RSS cobre a falta | `Crawl-delay: 10`, respeitado (10 s entre requisições) | CC BY 4.0, mas é **veículo de imprensa**: o fluxo v3 só aceitava veículos depois do parecer jurídico | Carregada (até 90, 10 por editoria) |
| TSE | — | — | Akamai responde "Access Denied" a acesso automatizado, inclusive no `robots.txt`. **Não contornar.** | — | **Fora**: precisa de outro canal (dados abertos do TSE ou download manual) |

## Limitações conhecidas

- **IBGE:** a API traz só o parágrafo de abertura (cerca de 270 caracteres, cortado com "..."). Ele carrega os números principais do release, mas não as tabelas nem o texto completo.
- **Volume:** a carga é curada, não em massa. São no máximo 100 URLs por carga, uma página por vez, com intervalo mínimo de 2 s por domínio (10 s na Agência Brasil).
- **Data nas páginas do gov.br (Agência Gov, INEP):** o leitor original da VeritAI só lê `article:published_time`, que esses portais não usam. A Agência Gov tem a data em `DC.date.valid_range`, e o INEP só no JSON-LD (`datePublished`). Sem o ajuste da branch `dados/data-publicacao-plone` do repositório veritai, esses documentos entram **sem data** e escapam do filtro pela data da notícia. Na primeira tentativa de carga, os 100 do INEP entraram sem data, e a base foi recriada depois do ajuste.
- **Timeouts:** o leitor tem limite de 12 s. Algumas páginas da Agência Gov passam disso; basta rodar a carga de novo, porque as que já entraram são puladas.
- **Agência Gov × Agência Brasil:** as duas são da EBC. O domínio é diferente, então contam como fontes independentes, a menos que o texto seja cópia quase literal.
- **PDFs** (Diário Oficial, notas técnicas, relatórios do IBGE e do INEP) não são lidos pelo `importar-urls`. Precisam de extração de texto e entram por `importar-textos`.

## Checagens (Google Fact Check Tools)

Carga de 07/10/2026: 29 consultas de `coleta/consultas-checagens.txt`, com `languageCode=pt` e no máximo 5 resultados por consulta (limite da VeritAI). Entraram **102 checagens** de 8 agências: Aos Fatos 34, UOL 25, Estadão 23, AFP Checamos 10, Comprova 3, Agência Pública 3, Observador 3 e AletheiaFact 1.

- **46 sem data (45%).** A VeritAI usa só `reviewDate`, e a API muitas vezes não manda esse campo. Em parte desses casos existe `claimDate`, que é a data em que a alegação circulou, não a da checagem. É preciso decidir se ela serve como substituta: sem data, não há filtro temporal nem separação por período na avaliação.
- **Desequilíbrio forte:** 56 refutadas e 42 enganosas ou sem contexto, contra só 3 verdadeiras. As agências checam sobretudo o que é falso. Isso não serve como base de rótulos balanceada.
- **Observador é português (Portugal):** `languageCode=pt` não separa Brasil de Portugal. Avaliar se entra.
- **Mapeamento para as 4 classes:** proposta em `mapeamento/vereditos.csv`, aplicada por `mapeamento/aplicar.py` (gera `saida/checagens-mapeadas.csv` para revisão manual). O esquema da base ainda não tem coluna para a classe; o mapeamento vive aqui até o dev incluí-la.
