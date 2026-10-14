# Experimento piloto: 10 questões × 5 condições = 50 feedbacks

| Condição | Fonte | Teoria | Modelo |
|---|---|---|---|
| C0 | Tutoria original (dataset) | — | — |
| C1 | LLM | Hattie & Timperley | gpt-4.1-mini (OpenAI) |
| C2 | LLM | Hattie & Timperley | qwen2.5:7b (Ollama) |
| C3 | LLM | Nicol & Macfarlane-Dick | gpt-4.1-mini (OpenAI) |
| C4 | LLM | Nicol & Macfarlane-Dick | qwen2.5:7b (Ollama) |

Tudo é configurado em [config.py](config.py): modelos, temperatura, seed, estratos da amostra, idioma, anotadores e rubrica.

## Pipeline de geração

O passo 2 reaproveita o pipeline da tutoria ([llm_analises_education/prompt_tutoria.py](https://github.com/paulaaraujo11/llm_analises_education/blob/main/prompt_tutoria.py)). Todas as etapas devolvem JSON.

```
por (questão, modelo)  ->  referencia.txt      -> resposta de referência
                           conceito.txt        -> conceito principal da referência
                           conceito.txt        -> conceito principal da resposta do aluno
por (questão, condição) -> hattie_timperley.txt | nicol_macfarlane_dick.txt
                           (entrada: entrada_avaliacao.txt)
                           -> nota_sugerida + tags (titulo, trecho, tipo, feedback) + campos da teoria
```

- A referência e os conceitos são gerados uma vez por modelo e compartilhados pelas duas teorias. Dentro de um mesmo modelo, só a camada teórica muda.
- As tags seguem as mesmas regras e o mesmo padrão de título do `sugerir_nota` da tutoria, por exemplo "Erro Processador: Armazenamento". Assim, ACERTOS, ACERTOS PARCIAIS e ERROS ficam no mesmo formato do C0.
- `02_gerar.py` mede, para cada feedback, a `conformidade` ao esquema JSON e o `trecho_literal`: a fração das tags cujo trecho existe de fato na resposta do aluno, que funciona como indicador de alucinação.

## Preparação (uma vez)

```bash
pip install -r requirements.txt
cp experiments/.env.example experiments/.env    # e coloque a OPENAI_API_KEY
ollama pull qwen2.5:7b
ollama serve                                    # se o Ollama não estiver rodando
```

## Execução

```bash
python experiments/01_amostra.py                # seleciona as 10 questões -> results/amostra_10.csv
python experiments/02_gerar.py --dry-run        # confere um prompt montado, sem chamar API
python experiments/02_gerar.py                  # 40 feedbacks (+60 chamadas de preparo) -> geracoes_brutas.jsonl + feedbacks_50.csv
python experiments/03_preparar_avaliacao.py     # normaliza + planilhas cegas por anotador
python experiments/04_metricas.py               # ROUGE-L, BERTScore, tamanho, conformidade
#   ... anotadores preenchem as planilhas -> salvar em results/avaliacao/anotacoes/
python experiments/05_analise.py                # concordância, Friedman, Wilcoxon+Holm, teste cego, gráficos
```

`02_gerar.py` pode ser retomado: rodar de novo só gera o que falta. Use `--condicoes C2 C4` para rodar apenas um provedor.

## Avaliação cega

- Envie aos anotadores só `planilha_anotador_<X>.csv` e `guia_rubrica.txt`. A ordem é embaralhada de forma diferente para cada anotador.
- **Não envie** `chave_CONFIDENCIAL.csv`, que diz qual condição gerou cada feedback.
- A versão mostrada (`feedback_aluno`) remove os marcadores `[nível: ...]`, as seções vazias e a "Nota para o professor".
- As métricas de similaridade usam `feedback_normalizado`, que contém só ACERTOS, ACERTOS PARCIAIS e ERROS, no mesmo formato da tutoria original.
- `autoria_percebida`: O = original da tutoria, N = novo (gerado no experimento).

## Saídas (`results/`)

| Arquivo | Conteúdo |
|---|---|
| `amostra_10.csv` | questões selecionadas + feedback do professor |
| `geracoes_brutas.jsonl` | log completo de cada chamada: prompt, resposta, versão do modelo, tokens, tempo |
| `feedbacks_50.csv` | os 50 feedbacks (bruto, normalizado, versão aluno) |
| `metricas_automaticas.csv` | métricas por feedback |
| `avaliacao/` | planilhas, guia e chave |
| `analise/` | tabelas estatísticas e gráficos |
