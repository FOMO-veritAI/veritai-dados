# AVeriTeC como teste de estresse da VeritAI (08/10/2026)

**Isto não é medição de desempenho da VeritAI.** As alegações são de 2020, centradas nos EUA (41%; há uma única brasileira) e vêm com evidência-ouro escolhida por anotadores, em perguntas e respostas curtas. O objetivo é achar **tipos de erro** que os conjuntos escritos a partir dos releases não exercitam.

## Dados e conversão

- **Origem:** desenvolvimento do AVeriTeC (500 alegações; Hugging Face `chenxwh/AVeriTeC`, revisão `2ca9dee`, SHA-256 conferido) e a tradução do AVERITEC-BR (Delucis et al., 2025), as duas já baixadas e analisadas na EDA da FOP (relatório, seção 4).
- **Licenças:** AVeriTeC em CC BY-NC 4.0, só para uso não comercial e com atribuição. AVERITEC-BR sem licença declarada; por ser derivado, vale no mínimo a mesma restrição. Os dados ficam fora do git, em `saida/averitec/`.
- **Conversor:** `averitec/converter.py` gera o formato do `eval/avaliar.py`. A análise por classe, tipo e estratégia é feita por `averitec/analisar.py`.
  - **Evidência:** uma por resposta, com o texto "pergunta + resposta" (mais a explicação, nas booleanas).
  - **Fonte:** o domínio original da URL, sem o prefixo do web.archive.org.
  - **Justificativa:** nunca entra como evidência, porque verbaliza o veredito.
  - **Unanswerable:** respostas "No answer could be found." ficam fora por padrão (variante `--com-unanswerable`).
- **Português** (`--traducao`): ficam de fora as 76 alegações com alguma resposta truncada pela tradução, o defeito medido na EDA. Restam 424 (263 R, 103 S, 30 NEE, 28 CE).

Comandos (a partir de `veritai-dados/`, com o ambiente do `veritai`):

```bash
PY=../veritai/.venv/bin/python
$PY averitec/converter.py <EDA>/data/raw/averitec/dev.json [--traducao <EDA>/data/raw/averitec_br/dev.json]
cd ../veritai && .venv/bin/python eval/avaliar.py --perfil v1 --arquivo ../veritai-dados/saida/averitec/dev-pt.jsonl [--sem-verificador]
```

## Resultados

Mac M4, código da branch `melhorias/entidade-numero` (`a533066`). Linha de base da classe majoritária (REFUTED): macro-F1 de 0,189.

| Conjunto | Perfil | Verificador | Macro-F1 (IC95) | Falsas aprovações (IC95) |
|---|---|---|---|---|
| EN, 500 | V0 | sem | 0,195 [0,16; 0,23] | 9,0% [6,1; 12,0] |
| EN, 500 | V0 | com | 0,128 [0,09; 0,16] | 8,5% [5,7; 11,4] |
| EN, 500 | V1 | sem | 0,289 [0,25; 0,33] | 10,3% [7,4; 13,5] |
| EN, 500 | V1 | com | 0,149 [0,12; 0,19] | 5,3% [3,1; 7,5] |
| PT, 424 | V0 | sem | 0,252 [0,21; 0,29] | 10,6% [7,0; 14,2] |
| PT, 424 | V0 | com | 0,172 [0,13; 0,22] | 7,2% [4,2; 10,1] |
| PT, 424 | V1 | sem | **0,313** [0,27; 0,36] | 7,8% [5,1; 10,7] |
| PT, 424 | V1 | com | 0,157 [0,12; 0,20] | 3,1% [1,5; 5,2] |

Variantes da V1 em inglês, com verificador:
- com as respostas Unanswerable: 0,152 de macro-F1;
- sem as respostas vindas do próprio site da checagem (54): 0,154.

Os dois atalhos medidos na EDA quase não afetam a VeritAI, que não aprende com esses dados.

## Achado 1: neste cenário, o verificador custa mais do que protege

Na V1 em português, o verificador corta as falsas aprovações de 7,8% para 3,1%. Em troca, o recall de SUPPORTED cai de 0,37 para 0,13 e o de REFUTED de 0,37 para 0,13, e 355 das 424 predições viram NEE. Nos releases, onde ele foi ajustado, acontecia o contrário: o macro-F1 subia.

Relações fortes (NLI ≥ 0,72) que ele neutralizou na V1 em português:

| Regra | Rótulo neutralizado | Ocorrências | Alegações afetadas |
|---|---|---|---|
| Entidade ausente | contradição | 115 | 119 |
| Entidade ausente | apoio | 57 | (incluídas acima) |
| Número sem correspondente | apoio | 17 | 13 |
| Período divergente | contradição | 6 | 4 |

Parte disso é artefato da conversão. A regra de entidade procura a entidade no "documento", que aqui é uma resposta de uma ou duas frases; em produção, é a página inteira. Com o conjunto das respostas da alegação fazendo o papel do documento, a V1 com verificador sobe de 0,157 para 0,205 em português e de 0,149 para 0,180 em inglês, mas continua longe dos 0,313 e 0,289 sem verificador.

O resto são lacunas reais, que também valem para notícias brasileiras:
- **A troca é a própria refutação.** Quando a afirmação erra a entidade, a data ou o ano, a evidência certa cita outra entidade ou outro período, e a regra apaga a contradição:
  - "ataque à embaixada francesa" × "a embaixada alemã";
  - "patente registrada em 2015" × "maio de 2020";
  - "Facebook declarou em 1996" × "Zuckerberg tinha 12 anos em 1996".

  É a mesma troca consciente já anotada para "troca de pessoa vira NEE", mas aqui ela é a regra, não a exceção: 115 contradições fortes.
- **Variantes de nome:**
  - "EUA" × "Estados Unidos" (23 bloqueios);
  - "Suprema Corte" × "Supremo Tribunal";
  - "Covid" × "Covid-19" (a comparação por palavra inteira, que separa "IPCA" de "IPCA-15", aqui atrapalha);
  - "Amy Barrett", quando a fonte só diz "Barrett".
- **Palavras em maiúscula que não são entidades:**
  - meio de frase: "Presidente", "Lei", "Comissão", "Eles", "Endossou";
  - texto todo em maiúsculas: "PEDASTRIA é agora LEGAL na CALIFÓRNIA".
- **Comparação na afirmação:** em "dez vezes mais do que tinha em 2016", o ano da comparação conta como período da afirmação. O verificador tira as comparações da janela, mas não da afirmação. É um defeito simples de corrigir.
- **Número que exige conta:** "60 anos de existência", com evidência "de 1966, durou 13 anos". O bloqueio está certo pela regra; a lacuna é de raciocínio.

**Limite importante desta conclusão:** com evidência-ouro, toda evidência é sobre a alegação. O teste mede o custo do verificador (refutações e apoios perdidos), mas não o benefício para o qual ele foi feito: barrar documentos vizinhos trazidos pela busca (release de outro mês, outro estado). Para pesar os dois lados, é preciso um teste com recuperação, seja a base própria com pares mínimos de período vizinho, seja o knowledge store do AVeriTeC já baixado na EDA (11,5 GB, só o desenvolvimento).

## Achado 2: lacunas da V1 independentes do verificador

Os números abaixo são da V1 sem verificador, em português:
- **NEE demais:** 233 das 424 predições (55%), contra 7% de NEE nos rótulos. As respostas curtas e indiretas ("Qual a idade de Zuckerberg em 1996? Doze") raramente dão NLI forte.
- **CONFLICTING quase nunca sai:** recall de 0,07 (2 de 28). A regra de agregação só produz CONFLICTING com apoio e contradição fortes de fontes independentes; cherry-picking verdadeiro (dado certo, conclusão enganosa) não tem esse formato.
- **Citações** ("Quote Verification") são o pior tipo, com 0,30 de acerto. Uma citação fora de contexto é apoiada pelo texto literal.
- **Falsas aprovações** (19 refutadas marcadas como SUPPORTED) com padrões que nenhum conjunto nosso tinha:
  - alegações sobre o que **não se sabe** ("Não está claro como Biden enriqueceu", "É desconhecido se menores de 20 transmitem");
  - citação tirada de contexto (Fauci);
  - **novidade** ("novo vírus", conhecido desde 2009);
  - conclusões que exigem juntar evidências (BLM e Antifa "apoiaram Biden", quando doaram para lados opostos);
  - alertas de golpe ("uma mensagem será enviada…").

## Próximos passos sugeridos

1. **Corrigir o que é defeito, sem mudar a filosofia do verificador,** e medir de novo nos releases e no AVERITEC-BR:
   - tirar as comparações também da afirmação;
   - na regra de entidade, aceitar o último nome de um nome composto ("Barrett") e uma tabela de equivalentes (EUA/Estados Unidos, Covid/Covid-19);
   - ignorar texto todo em maiúsculas com mais de 6 letras.
2. **Decidir com o grupo e o dev se a regra de entidade e a de período devem bloquear contradições.** A alternativa é bloquear só quando o documento inteiro não trata da afirmação (nenhuma outra entidade em comum), e não quando só a entidade trocada falta. É uma decisão de troca de erros, não um defeito.
3. **Medir o benefício do verificador num cenário com recuperação** (pares mínimos de período e entidade vizinhos na base própria), para pesar contra o custo medido aqui.
4. **Levar os padrões de falsa aprovação** (incerteza, citação fora de contexto, novidade, golpe) para o conjunto de afirmações reais do passo 2, com versões brasileiras.
