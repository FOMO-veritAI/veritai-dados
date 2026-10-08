"""Monta avaliacao/avaliacao_veritai.ipynb. Rode a partir de veritai-dados/ com o .venv do veritai."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {"name": "veritai", "display_name": "VeritAI (.venv)", "language": "python"}
celulas = []
md = lambda s: celulas.append(nbf.v4.new_markdown_cell(s.strip()))
py = lambda s: celulas.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Avaliação da VeritAI

Notebook da entrega de documentação e validação dos modelos de IA (Grupo 5, Challenge 1, Residência em IA — Instituto Eldorado / UnB Gama). Ele **carrega, executa e avalia** a VeritAI, o serviço de verificação de afirmações do FOMO, e reúne as métricas citadas no relatório técnico.

**A VeritAI não tem modelo treinado pela equipe.** Ela combina modelos pré-treinados públicos (embedding de sentenças e inferência em linguagem natural, NLI) com regras explícitas e versionadas. "Carregar o modelo" aqui significa carregar esses modelos e a configuração (`veritai/config.json`); não há pesos próprios a carregar.

**Como rodar:** kernel `VeritAI (.venv)` (o `.venv` do repositório `veritai`, com `pip install -e ".[modelos,dev,notebook]"`), a partir de `veritai-dados/avaliacao/`. A base própria precisa estar em `veritai/data/veritai.sqlite3` (restaurada de `artefatos/veritai.sqlite3.gz` e migrada com `python -m veritai.base migrar`). A execução completa, com as partes ao vivo, leva poucos minutos num Mac M4; as tabelas completas vêm da última execução da bateria (`avaliacao/bateria.py`), porque rodá-la leva de 30 a 45 minutos. Para rodar tudo de novo aqui, mude `RODAR_BATERIA` para `True`.

**Sobre os rótulos:** os conjuntos de releases (desenvolvimento e validação), as checagens e uma amostra dos vizinhos foram escritos por IA e **conferidos por um anotador**, com concordância total; os demais conjuntos são pré-rotulagem. Os números orientam decisões; não são medida definitiva (falta segundo anotador).
""")

py("""
import json, os, subprocess, sys, time
from pathlib import Path

AQUI = Path.cwd()
DADOS = AQUI.parent if AQUI.name == "avaliacao" else AQUI
VERITAI = DADOS.parent / "veritai"
sys.path[:0] = [str(VERITAI), str(VERITAI / "eval"), str(DADOS / "avaliacao")]
os.environ.setdefault("VERITAI_BASE", str(VERITAI / "data" / "veritai.sqlite3"))

import pandas as pd
import matplotlib.pyplot as plt

import avaliar
import bateria
from veritai.config import CONFIG, LIMIARES, VERIFICADOR, caminho_base, perfil

RODAR_BATERIA = False  # True roda a bateria completa aqui (30 a 45 min)
FIGURAS = DADOS / "avaliacao" / "figuras"
FIGURAS.mkdir(exist_ok=True)
pd.set_option("display.max_colwidth", 120)

commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=DADOS, capture_output=True, text=True).stdout.strip()
print(f"commit {commit} | config {CONFIG['versao_config']} | limiares {dict((k, v) for k, v in LIMIARES.items() if not k.startswith('_'))}")
print(f"base própria: {caminho_base()} ({'existe' if caminho_base().exists() else 'NÃO ENCONTRADA'})")
""")

md("""
## 1. Carregar os modelos

**Pergunta:** quais modelos a VeritAI usa, e quanto custa carregá-los?

**Por que importa:** a abordagem escolhida usa modelos prontos; a escolha entre os perfis V0 e V1 é a principal decisão de modelo do projeto.
""")

py("""
from veritai.modelos import ComparadorNLI

perfis = pd.DataFrame([{"perfil": nome, **{k: v for k, v in perfil(nome).items() if k in ("embedding", "nli")}} for nome in ("v0", "v1")])
display(perfis)
comparadores, tempos = {}, {}
for nome in ("v0", "v1"):
    inicio = time.perf_counter()
    comparadores[nome] = ComparadorNLI(nome)
    comparadores[nome].modelos._carregar()
    tempos[nome] = time.perf_counter() - inicio
print({k: f"{v:.1f} s" for k, v in tempos.items()})
""")

md("""
**Conclusão:** os dois perfis carregam em segundos depois do primeiro download (cerca de 0,5 GB para a V0 e 1,7 GB para a V1). O NLI da V1 é carregado em float32: em float16, o padrão do checkpoint, ele ficava cerca de 7 vezes mais lento em CPU.
""")

md("""
## 2. Executar: uma notícia de ponta a ponta

**Pergunta:** como a VeritAI processa uma notícia, da extração das afirmações ao resultado?

O exemplo usa a API real (`criar_app`), com a base própria e sem busca na web: primeiro o `POST /extrair` propõe afirmações a partir de uma notícia; depois o `POST /analisar` verifica duas afirmações, uma correta e uma com o número trocado.
""")

py("""
import sqlite3
from fastapi.testclient import TestClient
from veritai.api import criar_app
from veritai.base import BaseEvidencias
from veritai.fontes import buscar_fontes

comparador = comparadores["v1"]
base = BaseEvidencias(caminho_base(), perfil("v1")["embedding"], comparador.modelos.vetorizar, "v1")
cliente = TestClient(criar_app(comparador, buscar_fontes, base))

titulo, texto, data = sqlite3.connect(caminho_base()).execute(
    "SELECT titulo, texto, data_publicacao FROM documentos WHERE titulo LIKE 'IPCA fica em 0,48% em setembro%' LIMIT 1").fetchone()
extraidas = cliente.post("/extrair", json={"noticia": {"titulo": titulo, "texto": texto[:3000], "data": data}, "maximo": 3}).json()
pd.DataFrame(extraidas["afirmacoes"])[["texto", "sinais", "alertas"]]
""")

py("""
pedido = {"noticia": {"titulo": "Teste", "data": data}, "buscar_na_web": False,
          "afirmacoes": ["O IPCA de setembro de 2025 foi de 0,48%.", "O IPCA de setembro de 2025 foi de 0,84%."]}
relatorio = cliente.post("/analisar", json=pedido).json()
for item in relatorio["afirmacoes"]:
    print(f"{item['afirmacao']}\\n  → {item['resultado']} | fontes independentes: {item['fontes_independentes']} | {item['justificativa']}")
    for e in item["evidencias"][:2]:
        print(f"     [{e['relacao']}] sim {e['similaridade']:.2f} NLI {e['pontuacao_nli']:.2f} | {e['trecho'][:110]}")
print("versões:", relatorio["versoes"])
""")

md("""
**Conclusão:** cada afirmação recebe um resultado próprio, com as evidências, a relação atribuída a cada trecho e a justificativa gerada pelas regras. A porcentagem fica sempre `null`: o sistema não está calibrado.
""")

md("""
## 3. Avaliar: métricas

**Métricas usadas** (todas por afirmação):

- **macro-F1**, com intervalo de confiança de 95% por bootstrap; quando se comparam sistemas que preveem conjuntos de classes diferentes, usa-se também o macro-F1 sobre as classes dos rótulos;
- **falsas aprovações**: SUPPORTED quando o rótulo é outro (o erro mais grave para a plataforma);
- **falsas refutações**: REFUTED quando o rótulo é SUPPORTED (alarme falso para o revisor);
- **taxa de NEE** predita;
- **itens frágeis**: a decisão muda se um limiar de "forte" se mover 0,02;
- **recall da busca** (vizinhos): o documento certo está entre as evidências.

**Conjuntos:** releases — desenvolvimento (65) e validação (43); contraste (28, só sanidade); vizinhos com busca na base (140); AVeriTeC dev em português (AVERITEC-BR, 424) e inglês (500), como teste de estresse; teste intocado (treino do AVeriTeC).

### 3.1 Avaliação ao vivo (V1, verificador padrão)
""")

py("""
ao_vivo = []
for nome in ("dev", "val", "con"):
    inicio = time.perf_counter()
    predicoes = bateria.rodar_conjunto_com_evidencias(comparadores["v1"], avaliar.carregar(bateria.CONJUNTOS[nome]))
    m = bateria.metricas(predicoes)
    ao_vivo.append({"conjunto": nome, "n": m["n"], "macro-F1": round(m["macro_f1"], 3), "IC95": tuple(round(x, 3) for x in m["macro_f1_ic95"]),
                    "falsas aprovações": f"{m['falsas_aprovacoes']:.1%}", "falsas refutações": f"{m['falsas_refutacoes']:.1%}" if m["falsas_refutacoes"] is not None else "—",
                    "NEE": f"{m['taxa_nee']:.1%}", "segundos": round(time.perf_counter() - inicio, 1)})
pd.DataFrame(ao_vivo)
""")

md("""
### 3.2 Bateria completa (perfis × verificador × conjuntos)
""")

py("""
if RODAR_BATERIA:
    subprocess.run([sys.executable, str(DADOS / "avaliacao" / "bateria.py"), "--nome", "completa"], cwd=DADOS, check=True)
pastas = sorted((DADOS / "saida" / "bateria").glob("*-completa"))
assert pastas, "Rode avaliacao/bateria.py --nome completa (ou RODAR_BATERIA = True)."
PASTA_BATERIA = pastas[-1]
resumo = json.loads((PASTA_BATERIA / "resumo.json").read_text(encoding="utf-8"))
tabela = pd.DataFrame(resumo["resultados"])
print(f"bateria: {PASTA_BATERIA.name} (commit {resumo['commit']})")
mostrar = tabela.assign(**{
    "macro-F1": tabela.macro_f1.round(3),
    "falsas aprov.": (100 * tabela.falsas_aprovacoes).round(1),
    "falsas refut.": (100 * tabela.falsas_refutacoes).round(1),
    "NEE %": (100 * tabela.taxa_nee).round(1),
    "recall busca %": (100 * tabela.get("recall_busca")).round(1),
})[["conjunto", "perfil", "config", "n", "macro-F1", "falsas aprov.", "falsas refut.", "NEE %", "frageis", "recall busca %"]]
mostrar
""")

md("""
### 3.3 Ablação do verificador

**Pergunta:** o verificador (regras de entidade, período e número depois do NLI) ajuda ou atrapalha, e onde?
""")

py("""
ordem = ["viz", "dev", "val", "con", "avbr", "aven"]
nomes = {"viz": "Vizinhos\\n(com busca)", "dev": "Releases\\ndev", "val": "Releases\\nvalidação", "con": "Contraste", "avbr": "AVERITEC-BR", "aven": "AVeriTeC EN"}
fig, eixos = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
for eixo, nome_perfil in zip(eixos, ("v1", "v0")):
    t = tabela[tabela.perfil == nome_perfil].pivot(index="conjunto", columns="config", values="macro_f1").reindex([c for c in ordem if c in set(tabela.conjunto)])
    t[["sem", "padrao"]].rename(columns={"sem": "sem verificador", "padrao": "com verificador"}).plot.bar(ax=eixo, rot=0, color=["#bbbbbb", "#2b6cb0"])
    eixo.set_xticklabels([nomes[c] for c in t.index], fontsize=8)
    eixo.set_title(f"Perfil {nome_perfil.upper()}"); eixo.set_xlabel(""); eixo.set_ylabel("macro-F1"); eixo.set_ylim(0, 1)
fig.tight_layout(); fig.savefig(FIGURAS / "ablacao_verificador.png", dpi=200); plt.show()
""")

md("""
**Conclusão:** com busca na base (vizinhos), o verificador é indispensável: sem ele, releases de outros meses e de outros indicadores apoiam ou contradizem a afirmação errada. Com evidência-ouro (AVeriTeC), em que toda evidência é sobre a alegação, ele custa acertos, porque bloqueia refutações por troca de entidade ou data. O cenário de produção é o com busca.
""")

md("""
### 3.4 Matrizes de confusão (V1, verificador padrão)
""")

py("""
def matriz(conjunto, nome_perfil="v1", config="padrao"):
    predicoes = [json.loads(l) for l in (PASTA_BATERIA / "predicoes" / f"{conjunto}-{nome_perfil}-{config}.jsonl").read_text(encoding="utf-8").splitlines()]
    curto = {"SUPPORTED": "S", "REFUTED": "R", "NOT_ENOUGH_EVIDENCE": "NEE", "CONFLICTING_EVIDENCE": "CE"}
    return pd.crosstab(pd.Series([curto[p["rotulo"]] for p in predicoes], name="rótulo"), pd.Series([curto[p["predito"]] for p in predicoes], name="predição"))
for conjunto in ("val", "viz", "avbr"):
    print(conjunto); display(matriz(conjunto))
""")

md("""
## 4. Limiares de decisão

**Pergunta:** os limiares de "forte" (similaridade ≥ 0,43 e NLI ≥ 0,72) são adequados?

**Por que importa:** eles foram definidos como exemplos na fase de requisitos, antes da escolha dos modelos, e nunca tinham sido medidos. A varredura usa os trechos salvos pela bateria (sem rodar os modelos) e escolhe só no desenvolvimento.
""")

py("""
import limiares
dev_v1 = limiares.ler(PASTA_BATERIA, "dev", "v1", "padrao")
grade = pd.DataFrame([[limiares.medir(dev_v1, s, n)[0] for n in sorted(set(limiares.NLIS))] for s in limiares.SIMILARIDADES],
                     index=limiares.SIMILARIDADES, columns=sorted(set(limiares.NLIS)))
fig, eixo = plt.subplots(figsize=(9, 4.5))
imagem = eixo.imshow(grade.values, cmap="Blues", vmin=0, vmax=0.7, aspect="auto")
eixo.set_xticks(range(len(grade.columns)), [f"{c:.2f}" for c in grade.columns], fontsize=8)
eixo.set_yticks(range(len(grade.index)), [f"{i:.2f}" for i in grade.index], fontsize=8)
eixo.set_xlabel("nli_forte"); eixo.set_ylabel("similaridade_forte"); eixo.set_title("Macro-F1 no desenvolvimento (V1)")
for i in range(grade.shape[0]):
    for j in range(grade.shape[1]):
        eixo.text(j, i, f"{grade.values[i, j]:.2f}", ha="center", va="center", fontsize=6)
fig.colorbar(imagem); fig.tight_layout(); fig.savefig(FIGURAS / "limiares_v1.png", dpi=200); plt.show()
""")

md("""
**Conclusão:** na V1, a similaridade não atua até 0,80 (o embedding e5 dá mais de 0,80 a todas as evidências) e o NLI fica num platô entre 0,50 e 0,75, com diferença de um item em 65. Os dados não justificam mudar os limiares; a validação e os vizinhos confirmam que baixar o limiar do NLI cria falsas refutações.
""")

md("""
## 5. Teste intocado

**Pergunta:** como a configuração final se sai em dados nunca usados para ajustar regras ou limiares?

O treino do AVeriTeC (3.068 alegações em inglês; 2.683 em português pelo AVERITEC-BR, sem as traduções truncadas) foi rodado **uma única vez**, com a configuração final (verificador padrão). É evidência-ouro em perguntas e respostas, de 2020 e centrada nos EUA: mede raciocínio sobre evidência, não o domínio brasileiro.
""")

py("""
intocados = sorted((DADOS / "saida" / "bateria").glob("*-intocado"))
if intocados:
    r = json.loads((intocados[-1] / "resumo.json").read_text(encoding="utf-8"))
    t = pd.DataFrame(r["resultados"])
    display(t.assign(**{"IC95": t.macro_f1_ic95.map(lambda x: tuple(round(v, 3) for v in x))})[["conjunto", "perfil", "n", "macro_f1", "IC95", "falsas_aprovacoes", "falsas_refutacoes", "taxa_nee"]].round(3))
else:
    print("Teste intocado ainda não rodado: avaliacao/bateria.py --perfis v1 v0 --configs padrao --conjuntos avbr_teste aven_teste --nome intocado")
""")

md("""
## 6. Extração automática de afirmações

**Pergunta:** a extração por regras (`POST /extrair`) propõe afirmações aproveitáveis?

A amostra de 150 candidatas, de 30 notícias reais da base, foi pré-rotulada por IA (subagente Claude Sonnet, sem ver os sinais do extrator): verificável, um fato só, compreensível sozinha.
""")

py("""
pre = pd.read_csv(DADOS / "rotulos" / "extracao-v0" / "pre-rotulos-ia.csv")
verificaveis = pre[pre["verificavel (s/n)"] == "s"]
prontas = verificaveis[(verificaveis["atomica (s/n)"] == "s") & (verificaveis["compreensivel_sozinha (s/n)"] == "s")]
pd.DataFrame([{"candidatas": len(pre), "verificáveis": f"{len(verificaveis)} ({len(verificaveis)/len(pre):.0%})",
               "um fato só (entre verificáveis)": f"{(verificaveis['atomica (s/n)'] == 's').mean():.0%}",
               "compreensíveis sozinhas": f"{(verificaveis['compreensivel_sozinha (s/n)'] == 's').mean():.0%}",
               "prontas sem edição": f"{len(prontas)} ({len(prontas)/len(verificaveis):.0%})"}])
""")

md("""
**Conclusão:** as regras escolhem bem quais frases propor (90% verificáveis), mas quase todas precisam de edição pelo publicador (falta sujeito ou ano, ou há vários fatos na frase). Por isso o `/extrair` só propõe: o publicador confirma antes do `/analisar`.
""")

md("""
## 7. Notícias reais de ponta a ponta

**Pergunta:** no cenário mais próximo do uso real (afirmações extraídas de notícias, busca na base sem a notícia de origem), a VeritAI concorda com a conferência humana? E uma IA conferindo, concorda?
""")

py("""
conferencia = pd.read_csv(DADOS / "rotulos" / "noticias-reais-v0" / "conferencia.csv")
coluna = "rotulo (apoiada/refutada/insuficiente/conflitante)"
preenchidos = conferencia[coluna].notna().sum()
if preenchidos:
    subprocess.run([sys.executable, str(DADOS / "investigacoes" / "comparar_conferencias.py")], cwd=DADOS, check=True)
else:
    print(f"Conferência humana ainda não feita ({len(conferencia)} afirmações). Os resultados da VeritAI e da IA não são mostrados para manter a conferência cega.")
""")

md("""
## 8. Tempo de execução

**Pergunta:** quanto custa analisar uma afirmação em cada perfil (Mac M4, só CPU)?
""")

py("""
itens = avaliar.carregar(bateria.CONJUNTOS["val"])[:15]
custo = {}
for nome in ("v0", "v1"):
    inicio = time.perf_counter()
    for item in itens:
        comparadores[nome].comparar(item["afirmacao"], avaliar.fontes_do_item(item))
    custo[nome] = (time.perf_counter() - inicio) / len(itens)
pd.DataFrame([{"perfil": k, "segundos por afirmação (evidências fornecidas)": round(v, 2)} for k, v in custo.items()])
""")

md("""
## Resumo

Os números deste notebook alimentam o relatório técnico. Pontos principais: a VeritAI usa modelos pré-treinados e regras, sem treinamento próprio; a V1 é melhor que a V0 em quase todos os conjuntos (empatam no AVERITEC-BR com verificador); o verificador é decisivo no cenário com busca; os limiares estão num platô; a extração por regras escolhe bem as frases, mas não as descontextualiza; e as métricas por classe rara (insuficiente, conflitante) não são estáveis com os tamanhos atuais.
""")

nb.cells = celulas
from pathlib import Path
nbf.write(nb, str(Path(__file__).resolve().parent / "avaliacao_veritai.ipynb"))
print("notebook escrito com", len(celulas), "células")
