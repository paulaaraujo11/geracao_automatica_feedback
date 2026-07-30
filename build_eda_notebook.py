"""Gera eda_turma_feedback.ipynb a partir de celulas definidas aqui.
Executar: python build_eda_notebook.py
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))


md("""# EDA — Feedback aos alunos (`turma_feedback_parsed.csv`)

Dataset em formato **longo**: uma linha por *trecho* de feedback (o menor pedaco
avaliavel de uma resposta — um excerto da resposta do aluno + categoria de
acerto + explicacao). Uma atividade (`id_atividade`) tem N questoes
(`num_questao`), e cada questao pode ter M trechos avaliados.

Colunas:
- `id_atividade`: identifica a atividade/submissao (linha original do CSV bruto)
- `disciplina`, `secao`, `tipo` (GOOGLE/MOODLE)
- `aluno_id`: id anonimizado (hash), sem email/nome
- `data_resposta`, `data_entrega`, `data_disponibilizacao`
- `nota_atividade`: nota da atividade (repetida em todos os trechos da mesma atividade)
- `num_questao`, `pergunta`, `resposta_aluno`
- `categoria_feedback`: ACERTOS / ACERTOS PARCIAIS / ERROS / NAO_RESPONDIDA /
  SEM_FEEDBACK_PROFESSOR / TEXTO_LIVRE / VAZIO / SEM_QUESTOES
- `trecho`: excerto da resposta do aluno julgado (quando aplicavel)
- `explicacao`: justificativa do feedback para aquele trecho

Gerado por `parse_feedback.py` a partir do `turma-feedback.csv` bruto.
""")

code("""import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

pd.set_option('display.max_colwidth', 120)
plt.rcParams['figure.figsize'] = (9, 4.5)

df = pd.read_csv('turma_feedback_parsed.csv')
df['nota_atividade'] = pd.to_numeric(df['nota_atividade'], errors='coerce')
df['data_resposta'] = pd.to_datetime(df['data_resposta'], errors='coerce')

print(df.shape)
df.head()
""")

md("## 1. Visão geral e qualidade dos dados")

code("""df.info()
""")

code("""missing = df.isna().mean().sort_values(ascending=False).mul(100).round(1)
missing.to_frame('% nulo')
""")

md("""Note que `nota_atividade`, `data_entrega`, `data_disponibilizacao`, `pergunta` e
`resposta_aluno` sao atributos por **atividade/questao**, nao por trecho — o
percentual de nulos aqui e inflado pela granularidade longa (varios trechos por
questao). As secoes abaixo desduplicam para o nivel correto antes de analisar
cada aspecto.""")

md("## 2. Granularidade dos dados: atividades, questões e trechos")

code("""df_atividade = df.drop_duplicates('id_atividade').copy()
df_questao = df.drop_duplicates(['id_atividade', 'num_questao']).copy()

print(f"Atividades (submissoes) unicas: {df_atividade.shape[0]}")
print(f"Pares atividade+questao unicos: {df_questao.shape[0]}")
print(f"Trechos de feedback (linhas do csv): {df.shape[0]}")
print(f"Alunos unicos: {df['aluno_id'].nunique()}")
print(f"Disciplinas unicas: {df['disciplina'].nunique()}")
""")

md("## 3. Distribuição por disciplina e tipo (GOOGLE/MOODLE)")

code("""contagem_disciplina = df_atividade['disciplina'].value_counts()
contagem_disciplina
""")

code("""fig, ax = plt.subplots(figsize=(9, 6))
contagem_disciplina.sort_values().plot(kind='barh', ax=ax, color='#4C72B0')
ax.set_xlabel('Nº de atividades (submissões)')
ax.set_title('Atividades por disciplina')
plt.tight_layout()
plt.show()
""")

code("""df_atividade['tipo'].value_counts().plot(kind='bar', color='#55A868')
plt.title('Atividades por tipo de plataforma')
plt.ylabel('Nº de atividades')
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()
""")

md("""## 4. Categorias de feedback

Distribuição das categorias no nível de **trecho** (unidade mais granular) —
mostra o quanto do corpus é feedback estruturado (ACERTOS/ERROS/PARCIAIS) vs.
texto livre, não respondido, ou sem feedback do professor.""")

code("""cat_counts = df['categoria_feedback'].value_counts()
cat_pct = (cat_counts / cat_counts.sum() * 100).round(1)
pd.DataFrame({'contagem': cat_counts, '%': cat_pct})
""")

code("""cat_counts.sort_values().plot(kind='barh', color='#C44E52')
plt.xlabel('Nº de trechos')
plt.title('Distribuição das categorias de feedback (nível trecho)')
plt.tight_layout()
plt.show()
""")

md("""### Categoria por disciplina (%)

Normaliza por disciplina para comparar o "perfil" de feedback entre turmas —
por exemplo, quais disciplinas têm mais `SEM_FEEDBACK_PROFESSOR` (indicando
correção sem comentário docente) ou `NAO_RESPONDIDA`.""")

code("""tab = pd.crosstab(df['disciplina'], df['categoria_feedback'], normalize='index') * 100
tab = tab.round(1)
tab
""")

code("""fig, ax = plt.subplots(figsize=(10, 7))
tab.plot(kind='barh', stacked=True, ax=ax, colormap='tab10')
ax.set_xlabel('% dos trechos')
ax.set_title('Perfil de categoria de feedback por disciplina')
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
plt.tight_layout()
plt.show()
""")

md("## 5. Distribuição de notas (`nota_atividade`)")

code("""notas = df_atividade['nota_atividade'].dropna()
print(notas.describe())
print()
print('Atividades sem nota registrada:', df_atividade['nota_atividade'].isna().sum(),
      f"({df_atividade['nota_atividade'].isna().mean()*100:.1f}%)")
""")

code("""fig, ax = plt.subplots()
notas.plot(kind='hist', bins=30, ax=ax, color='#8172B2', edgecolor='white')
ax.set_xlabel('Nota da atividade')
ax.set_title('Distribuição de notas (todas as disciplinas)')
plt.tight_layout()
plt.show()
""")

md("""Atenção: escalas de nota **não são comparáveis entre disciplinas** — algumas
usam 0–10, outras 0–100. Vale normalizar por disciplina antes de qualquer
comparação agregada.""")

code("""escalas = df_atividade.groupby('disciplina')['nota_atividade'].agg(['min', 'max', 'mean', 'count'])
escalas.round(2)
""")

md("## 6. Número de questões por atividade")

code("""n_questoes = df_questao.groupby('id_atividade').size()
print(n_questoes.describe())
n_questoes.plot(kind='hist', bins=30, color='#64B5CD', edgecolor='white')
plt.xlabel('Nº de questões por atividade')
plt.title('Distribuição do nº de questões')
plt.tight_layout()
plt.show()
""")

md("## 7. Tamanho dos textos (respostas, perguntas, explicações)")

code("""def n_palavras(s):
    if pd.isna(s):
        return np.nan
    return len(str(s).split())

df_questao['len_pergunta'] = df_questao['pergunta'].apply(n_palavras)
df_questao['len_resposta'] = df_questao['resposta_aluno'].apply(n_palavras)
df['len_explicacao'] = df['explicacao'].apply(n_palavras)
df['len_trecho'] = df['trecho'].apply(n_palavras)

df_questao[['len_pergunta', 'len_resposta']].describe()
""")

code("""df[['len_trecho', 'len_explicacao']].describe()
""")

code("""fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
df_questao['len_resposta'].dropna().clip(upper=df_questao['len_resposta'].quantile(0.95)).plot(
    kind='hist', bins=30, ax=axes[0], color='#4C72B0', edgecolor='white')
axes[0].set_title('Palavras por resposta do aluno (p95 cap)')
df['len_explicacao'].dropna().clip(upper=df['len_explicacao'].quantile(0.95)).plot(
    kind='hist', bins=30, ax=axes[1], color='#DD8452', edgecolor='white')
axes[1].set_title('Palavras por explicação de feedback (p95 cap)')
plt.tight_layout()
plt.show()
""")

md("## 8. Atividade dos alunos (submissões por aluno)")

code("""por_aluno = df_atividade.groupby('aluno_id').size().sort_values(ascending=False)
print(por_aluno.describe())
por_aluno.head(10)
""")

code("""por_aluno.plot(kind='hist', bins=30, color='#937860', edgecolor='white')
plt.xlabel('Nº de atividades por aluno')
plt.title('Distribuição de submissões por aluno')
plt.tight_layout()
plt.show()
""")

md("## 9. Evolução temporal das submissões (`data_resposta`)")

code("""serie = df_atividade.dropna(subset=['data_resposta']).set_index('data_resposta').resample('W').size()
serie.plot(kind='line', marker='o', color='#4C72B0')
plt.ylabel('Nº de atividades respondidas')
plt.title('Submissões por semana (apenas registros com data_resposta)')
plt.tight_layout()
plt.show()
print(f"Cobertura de data_resposta: {df_atividade['data_resposta'].notna().mean()*100:.1f}% das atividades")
""")

md("""## 10. Notas de qualidade / próximos passos

- `nota_atividade`, `data_entrega`, `data_disponibilizacao` foram extraídos por
  regex do HTML de introdução — formatos de data mistos (DD/MM/AAAA, timestamp
  Unix, "Sem prazo de entrega") não foram normalizados aqui.
- `SEM_FEEDBACK_PROFESSOR`, `NAO_RESPONDIDA` e `VAZIO` são sinais de cobertura,
  não de conteúdo — úteis para medir o quanto do corpus tem feedback real
  analisável por NLP.
- Para experimentos de NLP/ML sobre qualidade de feedback, os campos mais úteis
  são `resposta_aluno` + `trecho` + `explicacao` dentro de
  `categoria_feedback in {ACERTOS, ACERTOS PARCIAIS, ERROS}` — é o subconjunto
  estruturado e comparável a um rótulo (certo/parcial/errado) + justificativa.
- `aluno_id` é anonimizado (hash), mas **não é anônimo de fato**: cruzar
  `disciplina` + `data_resposta` + `nota_atividade` ainda pode reidentificar
  alguém num grupo pequeno. Tratar como pseudonimizado, não anonimizado.
""")

nb['cells'] = cells
nbf.write(nb, 'eda_turma_feedback.ipynb')
print('notebook escrito: eda_turma_feedback.ipynb')
