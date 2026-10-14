# Geração Automática de Feedback Educacional Utilizando Large Language Models: Preparação e Estruturação do Dataset

**Etapa 1 da Dissertação de Mestrado**
## edit readme
---

## 1. Objetivo

O presente trabalho visa investigar a viabilidade e efetividade da utilização de Modelos de Linguagem Grande (Large Language Models – LLMs) para a geração automática de feedback educacional personalizado em contextos de educação superior. Especificamente, pretende-se:

- Caracterizar os padrões de feedback educacional existentes em ambientes virtuais de aprendizado (AVA);
- Estruturar um conjunto de dados de referência contendo feedbacks originais fornecidos por docentes;
- Avaliar a qualidade dos feedbacks gerados por LLMs em comparação com os feedbacks originais;
- Identificar as melhores estratégias de engenharia de prompts para otimizar a relevância, clareza e coerência do feedback automático.

Esta etapa constitui o fundamento metodológico para as fases subsequentes de experimentação e validação.

## 2. Motivação

A provisão de feedback de qualidade é reconhecidamente um dos fatores mais críticos para o aprendizado efetivo em contextos educacionais, particularmente em cursos de grande escala (Hattie & Timperley, 2007; Sadler, 1989). Entretanto, professores frequentemente enfrentam limitações de tempo e recursos para fornecer retroação detalhada e personalizada a cada estudante.

Os avanços recentes em modelos de linguagem generativos — particularmente os Transformers — abrem oportunidades para automatizar a geração de feedback mantendo qualidade e personalização. Contudo, a ausência de estudos sistemáticos sobre a aplicação desses modelos no contexto educacional brasileiro, bem como a falta de datasets públicos estruturados, constitui uma lacuna significativa na literatura.

Esta pesquisa busca preencher essa lacuna, fornecendo: (1) um corpus estruturado de feedback educacional em português; (2) uma metodologia reproduzível de estruturação de dados; (3) evidências empíricas sobre a viabilidade de LLMs para feedback automático.

## 3. Descrição do Dataset Original

O dataset original foi coletado a partir de um sistema de gerenciamento de aprendizado (Learning Management System – LMS) institucional, compreendendo respostas de estudantes e feedbacks fornecidos por docentes em disciplinas de Engenharia de Software e Arquitetura de Computadores, ofertadas durante o período August–December 2024.

### 3.1 Características Gerais

**Fonte e Origem**: O dataset foi consolidado a partir de exportações de:
- Plataforma Google Classroom (submissões e respostas automáticas);
- LMS Moodle (avaliações formuladas com questões de diversos tipos).

**Escopo**: 
- **Disciplinas**: 4 oferecimentos distintos (Fall 2024 – CT-365, CT-370, CT-371, CT-373);
- **Estudantes**: Aproximadamente 150 submetentes únicos;
- **Questões**: 200+ questões avaliadas;
- **Atividades**: 800+ submissões totais;
- **Idioma**: Principalmente português (feedback) e inglês (respostas de alunos internacionais).

**Estrutura Original**: O CSV bruto apresenta uma linha por atividade/submissão, contendo:
- Identificadores: `disciplina`, `secao`, `tipo` (plataforma), `aluno_email`;
- Metadados temporais: `data_resposta`, `data_entrega`, `data_disponibilizacao`;
- Conteúdo: Questão e resposta do aluno (frequentemente em HTML);
- Avaliação: Nota numérica (`nota_total`);
- Feedback: Campo `feedback_final_html` contendo markup HTML com categorias de acerto (ACERTOS, ACERTOS PARCIAIS, ERROS, etc.) e explicações.

### 3.2 Formato e Granularidade

O HTML contido no campo de feedback apresenta estrutura hierárquica:
```
Cabeçalho: Cumprimento + nome do aluno + nota + data
Corpo: Para cada questão respondida:
  - Categoria de acerto (ACERTOS, ACERTOS PARCIAIS, ERROS)
  - Lista de tópicos avaliados
  - Explicações textuais por tópico
Fechamento: Saudação personalizada + nome do aluno
```

Essa granularidade aninhada demanda processamento sofisticado para extração estruturada.

## 4. Problemas Encontrados na Base Raw

A análise preliminar do dataset bruto identificou várias deficiências que comprometem seu uso direto para análise e experimentação:

### 4.1 Problemas de Dados

**Encoding Misto**: O dataset consolidado contém mistura de codificações UTF-8 com caracteres de aspas tipográficas em CP-1252, resultante de exportações de múltiplas plataformas. Exemplo:
```
"...Você alcançou a nota "25" na atividade..."
  (aspas tipográficas não-ASCII em sessões UTF-8)
```

**Estruturas HTML Inconsistentes**: O markup não segue um DTD rigoroso:
- Tags `<ul>` e `<li>` apresentam atributos de estilo inline inconsistentes;
- Alguns feedbacks carecem de estrutura esperada;
- Caracteres especiais não são escapados uniformemente.

**Valores Faltantes e Anômalos**: 
- Campo `data_resposta` frequentemente vazio (não capturado pela plataforma);
- Notas negativas (-1) indicam submissões incompletas ou não avaliadas;
- Alguns feedbacks contêm categorias não-padrão ou textos livres não categorizados.

**Identificação Pessoal Exposta**: 
- Nomes de alunos aparecem em textos de cumprimento ("Olá, [NOME]!");
- Emails em claro no campo `aluno_email`;
- Assinaturas do professor incluem identificação pessoal.

**Granularidade Inadequada**: Cada linha representa uma atividade completa (múltiplas questões, múltiplos trechos de feedback), dificultando análises a nível de questão, categoria ou segmento avaliativo.

### 4.2 Implicações Metodológicas

Esses problemas comprometem:
- **Reprodutibilidade**: Análises sem padronização não podem ser replicadas;
- **Privacidade**: Violações potenciais da LGPD;
- **Comparabilidade**: Estruturas inconsistentes impedem comparação sistemática com LLMs.

## 5. Necessidade de Pré-processamento

O pré-processamento não é um passo meramente operacional, mas fundamental para a integridade científica e reprodutibilidade da pesquisa. Justificamos a importância em três eixos:

### 5.1 Reprodutibilidade Científica

A NCR (normal operating conditions) em pesquisa computacional exige que:
1. Os dados de entrada sejam públicos ou reproduzíveis;
2. Os procedimentos de transformação sejam explícitos e documentados;
3. Os artefatos intermediários possam ser auditados.

O pré-processamento documenta cada transformação (encoding, anonimização, parsing), permitindo que pesquisadores validem ou repliquem o trabalho. Sem isso, conclusões sobre efetividade de LLMs ficariam contaminadas por artefatos de tratamento de dados.

### 5.2 Conformidade Regulatória e Ética

A LGPD (Lei Geral de Proteção de Dados) exige que identificadores pessoais sejam removidos em datasets de pesquisa. O pré-processamento:
- Implementa anonimização criptográfica (hashing determinístico);
- Mantém rastreabilidade apenas em arquivo confidencial, separado do corpus público;
- Permite disseminação científica sem risco legal.

### 5.3 Qualidade Analítica

Dados estruturados e limpos ampliam a validade interna dos experimentos:
- Métricas de coerência e clareza requerem texto bem-formado;
- Comparações entre feedbacks e LLM-gerados dependem de tokenização consistente;
- Análises de categorias de acerto requerem campos estruturados.

## 6. Estratégia de Anonimização

A anonimização foi implementada seguindo o padrão Deterministic Hashing com Salt:

### 6.1 Procedimento Técnico

Para cada email de aluno (atributo sensível):
```
aluno_id = SHA256_HASH(SALT + email_lowercase)[:10]
            |
            └─> Resultado: ALU_<10 dígitos hexadecimais>
```

**Parâmetros**:
- **Algoritmo**: SHA-256 (criptograficamente seguro);
- **Salt**: `"experimento_v1_feedback"` (constante, garante estabilidade);
- **Truncamento**: 10 caracteres do hash (suficiente para 10¹⁰ combinações, reduz huella de correlação);
- **Prefixo**: `ALU_` (identifica claramente o domínio).

### 6.2 Preservação de Rastreabilidade

Um arquivo separado (`turma_feedback_mapping_CONFIDENCIAL.csv`) mantém a correspondência:
```
email,aluno_id
akram4506858@cloud.neduet.edu.pk,ALU_643310c0e7
ali4507399@cloud.neduet.edu.pk,ALU_b3f3077d9c
...
```

**Contratos de Guarda**:
- Armazenado em servidor protegido;
- Acesso restrito ao pesquisador responsável;
- Não incluído em publicações ou repositórios públicos.

### 6.3 Redação de Nomes em Feedback

Nomes de alunos frequentemente aparecem em saudações e despedidas do feedback. Foram extraídos via regex:

```regex
GREETING_RE = r"^(?:Olá|Bom dia)[, ]*<b>?\s*([^!<,\n]{2,80}?)\s*</b>?\s*[!,]"
CLOSING_RE  = r"Até logo[,!]?\s*<b>?\s*([^.<\n]{2,80}?)\s*</b>?\s*\.\s*$"
```

Cada nome extraído é substituído por placeholder `[ALUNO]`, mantendo coerência textual.

## 7. Extração de Campos

O processamento converte o HTML bruto em estrutura longa (long format), quebrando cada feedback original em linhas independentes, uma por "trecho" (unidade atômica).

### 7.1 Definição de Trecho

Um **trecho** é o menor segmento de feedback avaliativo: uma porção da resposta do aluno (ou ausência dela) associada a uma categoria de acerto e explicação do professor. 

**Exemplo Original**:
```
Q1: "Does the use of standard templates guarantee refactoring?"
Resposta: "Templates alone don't guarantee..."
Feedback HTML:
  [ACERTOS]
    - Can't guarantee
      "You correctly identify..."
    - Applies concepts
      "Moreover, your explanation shows..."
```

**Três trechos extraídos**:
1. Trecho 1: Resposta completa + ACERTOS + "Can't guarantee" + explicação 1
2. Trecho 2: Resposta completa + ACERTOS + "Applies concepts" + explicação 2
...

### 7.2 Processamento HTML

1. **Parse BeautifulSoup**: Converte HTML para árvore DOM;
2. **Extração Hierárquica**: Para cada questão, extrai categorias e itens;
3. **Limpeza de Markup**: Remove tags de estilo `<b>`, `<ul>`, `<li>`; converte para texto plano;
4. **Normalização**: Unescape de entidades HTML (`&quot;`, `&lt;`, etc.).

### 7.3 Extração de Metadados

Campos numéricos e temporais são extraídos via regex do cabeçalho HTML:

```regex
NOTA_RE = r"nota[^<]{0,60}?<b>\s*(-?\d+(?:[.,]\d+)?)\s*</b>"
DATA_RE = r"entregue no dia <b>([^<]+)</b>"
```

Resultados:
- `nota_atividade`: Numérica, coercida a float;
- `data_entrega`: Convertida para ISO 8601;
- `data_disponibilizacao`: Idem.

## 8. Estrutura da Nova Base

O dataset processado (`turma_feedback_parsed.csv`) em formato **long** apresenta a seguinte estrutura:

### 8.1 Esquema de Campos

| Campo | Tipo | Descrição | Cardinality |
|-------|------|-----------|------------|
| `id_atividade` | Integer | Identificador único da atividade/submissão (chave da linha original) | 1:N |
| `aluno_id` | String | Hash anônimo do email em formato ALU_xxxxxxxxxx | M:1 |
| `disciplina` | String | Nome da disciplina (ex: "Fall_24_CT-365_SE") | 1:N |
| `secao` | String | Seção (ex: "CT (A & B)", "Turma 01") | 1:N |
| `tipo` | String | Plataforma (GOOGLE ou MOODLE) | 1:N |
| `data_resposta` | Date | Data/hora de submissão da resposta pelo aluno | 1:N |
| `data_entrega` | Date | Prazo original da atividade | 1:N |
| `data_disponibilizacao` | Date | Data de abertura da atividade | 1:N |
| `email_enviado` | Boolean | Se feedback foi enviado via email (SIM/NAO) | 1:N |
| `nota_atividade` | Float | Nota numérica atribuída à atividade | 1:N |
| `num_questao` | Integer | Número sequencial da questão dentro da atividade | 1:N |
| `pergunta` | String | Texto completo da questão (até 1000 caracteres) | 1:1 |
| `resposta_aluno` | String | Resposta fornecida pelo aluno (até 5000 caracteres) | 1:1 |
| `categoria_feedback` | String | Classificação: ACERTOS / ACERTOS_PARCIAIS / ERROS / NAO_RESPONDIDA / TEXTO_LIVRE / SEM_FEEDBACK / VAZIO | 1:N |
| `trecho` | String | Subtema ou item específico avaliado (até 200 caracteres) | 1:1 |
| `explicacao` | String | Justificativa do feedback para o trecho (até 2000 caracteres) | 1:1 |
| `feedback_completo` | String | Feedback inteiro da questão (todas as categorias: acertos, acertos parciais, erros, com trecho -> explicação), repetido em cada linha da questão | N:1 |

### 8.2 Tabela Estrutura Esperada da Fase 2 (Integração com LLM)

Após integração com LLMs, a estrutura será expandida para incluir:

| Campo | Tipo | Descrição | Fonte |
|-------|------|-----------|-------|
| `id` | Integer (PK) | Identificador único do registro no formato longo | Gerado |
| `student_id` | String (FK) | Referência anônima ao aluno | Herdado |
| `disciplina` | String | Disciplina ofertante | Herdado |
| `secao` | String | Seção/turma | Herdado |
| `tipo` | String | Tipo de plataforma | Herdado |
| `pergunta` | String | Enunciado da questão | Herdado |
| `resposta` | String | Resposta do aluno | Herdado |
| `feedback_original` | String | Feedback do professor (ground truth) | Processado |
| `nota` | Float | Nota numérica | Herdado |
| `data` | Date | Data da submissão | Herdado |
| `idioma` | String (ENUM) | Idioma do feedback (PT, EN) | Detectado |
| `feedback_llm` | String | Feedback gerado pelo modelo | **LLM** |
| `modelo` | String | Identificação do modelo utilizado (ex: gpt-4, claude-3) | Experimento |
| `prompt` | String | Prompt enviado ao modelo | Experimento |
| `estrategia_prompt` | String (ENUM) | Tipo de prompt (zero-shot, few-shot, chain-of-thought) | Experimento |
| `avaliacao` | String (ENUM) | Rótulo de qualidade: EQUIVALENTE / INFERIOR / SUPERIOR / N/A | Anotador |
| `clareza` | Integer (1-5) | Escala Likert de clareza (1=pouco claro, 5=muito claro) | Anotador |
| `coerencia` | Integer (1-5) | Escala Likert de coerência com currículo | Anotador |
| `feed_up` | Boolean | Se o feedback promove aprendizado futuro (feed-up) | Anotador |
| `feed_back` | Boolean | Se o feedback reconhece êxitos prévios (feed-back) | Anotador |
| `feed_forward` | Boolean | Se o feedback oferece próximas ações (feed-forward) | Anotador |

### 8.3 Cardinalidade e Chaves

- **Chave Primária**: `id` (estabelecida na Fase 2);
- **Chaves Estrangeiras**: `student_id` (referencia tabela de alunos anônimos);
- **Cardinalidade**: 
  - Um aluno pode ter múltiplas atividades (1:N);
  - Uma atividade pode ter múltiplas questões (1:N);
  - Uma questão pode gerar múltiplos trechos (1:N).

## 9. Fluxo Completo do Pipeline

O pipeline de procesamento implementa a seguinte sequência:

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 0: AQUISIÇÃO E ARMAZENAMENTO SEGURO                      │
├─────────────────────────────────────────────────────────────┤
│ Dataset Bruto (Google Classroom + Moodle)                      │
│  │ → Consolidação em CSV único                               │
│  │ → Encoding normalizado (UTF-8)                            │
│  └─→ turma-feedback-original.csv                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: ANONIMIZAÇÃO E PRÉ-PROCESSAMENTO                     │
├─────────────────────────────────────────────────────────────┤
│ Script: parse_feedback.py                                     │
│  1. Leitura com fallback de encoding misto                   │
│  2. Hash determinístico SHA-256 de emails → aluno_id         │
│  3. Extração de nomes (regex) → redação                      │
│  4. Parsing HTML com BeautifulSoup                           │
│  5. Extração de: notas, datas, categorias, trechos           │
│  6. Conversão para formato longo (1 linha/trecho)            │
│  7. Limpeza e normalização de texto                          │
│                                                               │
│ Saídas:                                                       │
│  ├─ turma_feedback_parsed.csv (PÚBLICO)                      │
│  └─ turma_feedback_mapping_CONFIDENCIAL.csv (RESTRITO)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 1.5: ANÁLISE EXPLORATÓRIA DE DADOS (EDA)               │
├─────────────────────────────────────────────────────────────┤
│ Notebook: eda_turma_feedback.ipynb                            │
│  • Estatísticas descritivas (n=linhas, shape, tipos)         │
│  • Distribuição por disciplina, seção, plataforma            │
│  • Análise de valores faltantes (% nulo por coluna)          │
│  • Granularidade: atividades vs. questões vs. trechos        │
│  • Visualizações (matplotlib, seaborn)                       │
│  • Qualidade de texto (comprimento, idioma)                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: ENGENHARIA DE PROMPTS E GERAÇÃO LLM (PRÓXIMA)       │
├─────────────────────────────────────────────────────────────┤
│ Para cada feedback estruturado:                               │
│  1. Construir prompt (zero-shot, few-shot, etc.)             │
│  2. Invocar LLM (GPT-4, Claude, Llama, etc.)                 │
│  3. Armazenar resposta + metadados                           │
│  4. Expandir dataset com campos feedback_llm, modelo, prompt │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: AVALIAÇÃO HUMANA E COMPARAÇÃO                       │
├─────────────────────────────────────────────────────────────┤
│ Anotadores humanos (blind evaluation):                        │
│  • Escala Likert: clareza, coerência (1-5)                   │
│  • Categorias: equivalente / inferior / superior             │
│  • Dimensões de feedback: feed-up, feed-back, feed-forward   │
│  • Inter-rater reliability (Cohen's Kappa, Krippendorff's α) │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: ANÁLISE QUANTITATIVA E VISUALIZAÇÃO                 │
├─────────────────────────────────────────────────────────────┤
│ Métricas:                                                     │
│  • BLEU, ROUGE, METEOR (similaridade textual)                │
│  • BERTScore (semântica contextualizada)                     │
│  • Análise de variância (ANOVA): modelo × disciplina × nota  │
│  • Curvas de aprendizado de LLMs vs. estratégias de prompt  │
│                                                               │
│ Visualizações (Streamlit):                                   │
│  └─ Dashboard interativo (filtros, gráficos, exploração)     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 5: REDAÇÃO E DISSEMINAÇÃO CIENTÍFICA                    │
├─────────────────────────────────────────────────────────────┤
│ Artefatos:                                                    │
│  • Artigo em conferência (ex: EDULEARN, INTED)               │
│  • Corpus público (turma_feedback_parsed.csv)                 │
│  • Código reproduzível (GitHub com README)                   │
│  • Recomendações para praticidade pedagógica                 │
└─────────────────────────────────────────────────────────────┘
```

## 10. Próximas Etapas da Pesquisa

### 10.1 Curto Prazo (Próximos 2 meses)

1. **Engenharia de Prompts**:
   - Design de templates de prompts nas estratégias: zero-shot, few-shot (exemplares de qualidade), chain-of-thought;
   - Estudo piloto com 50 trechos para calibração;
   - Variação de temperatura e parâmetros de sampling.

2. **Seleção de Modelos LLM**:
   - GPT-4 Turbo (referência closed-source, state-of-the-art);
   - Claude 3 Opus (alternativa, foco em harmlessness);
   - Llama 3 70B (modelo open-source para reprodutibilidade);
   - GPT-3.5 Turbo (baseline econômico).

3. **Infraestrutura Experimental**:
   - API wrappers (OpenAI, Anthropic, Together AI para self-hosted);
   - Logging e versionamento de experimentos (MLflow/Weights & Biases);
   - Gestão de custos (orçamento por modelo).

### 10.2 Médio Prazo (2-4 meses)

4. **Geração em Escala**:
   - Lançar 1000+ feedbacks através de cada modelo-estratégia;
   - Implementar retry logic e tratamento de falhas;
   - Armazenar resultados em banco de dados (PostgreSQL/MongoDB).

5. **Anotação Humana**:
   - Recrutar 3-5 anotadores (professores de Engenharia de Software, mestrandos);
   - Treinar em protocolo de avaliação (guidelines);
   - Blind evaluation: anotadores não sabem qual feedback é do professor vs. LLM;
   - Calcular inter-rater reliability.

6. **Análise Preliminar**:
   - Tabulação de resultados de avaliação;
   - Análise exploratória: qual modelo/estratégia máxima; desempenho por disciplina/nível de dificuldade;
   - Identificação de falhas sistemáticas.

### 10.3 Longo Prazo (4-6 meses)

7. **Testing Estatístico**:
   - Testes de hipótese (H0: feedback_llm ≠ feedback_professor);
   - Análise de variância (ANOVA) multifatorial;
   - Regressão ordinal (variáveis Likert);
   - Análise de efeito (effect size: Cohen's d, τ de Kendall).

8. **Aprofundamento Qualitativo**:
   - Análise temática dos erros do LLM;
   - Classificação de falhas: alucinações, falta de contexto pedagógico, viés;
   - Estudo de casos: exemplos de sucesso e fracasso.

9. **Refinamento Iterativo**:
   - Fine-tuning de modelos abertos (Llama) em subset de dados rotulados;
   - Estratégias de retrieval-augmented generation (RAG) para contexto pedagógico;
   - Ensemble de modelos.

10. **Disseminação e Impacto**:
    - Submissão de artigo científico em conferência de educação/IA;
    - Publicação de corpus e código em repositório público (GitHub);
    - Desenvolvimento de protótipo Streamlit para professores;
    - Recomendações de boas prácticas para implementação em AVAs.

### 10.4 Limitações e Desafios Esperados

- **Custo Computacional**: Milhares de chamadas a APIs comerciais (GPT-4) custam centenas de dólares;
- **Variabilidade de LLMs**: Modelos comerciais evoluem, afetando reprodutibilidade;
- **Escassez de Feedbacks**: Dataset brasileiro é pequeno em relação a grandes corpora internacionais;
- **Subjetividade Humana**: Avaliação de qualidade depende fortemente da expertise e dos critérios dos anotadores.

## Conclusão

A primeira etapa desta pesquisa estabelece os alicerces metodológicos para investigação rigorosa da aplicação de LLMs em feedback educacional. Através do pré-processamento cuidadoso, anonimização completa e estruturação sistemática dos dados, garantimos reprodutibilidade, conformidade regulatória e qualidade analítica nos estudos subsequentes. O dataset estruturado e o pipeline documentado constituem contribuições científicas autônomas, viabilizando futuras pesquisas neste domínio emergente.

---

**Referências Selecionadas**

Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research*, 77(1), 81–112.

Sadler, D. R. (1989). Formative assessment and the design of instructional systems. *Instructional Science*, 18(2), 119–144.

Vaswani, A., et al. (2017). Attention is all you need. *Proceedings of the 31st NeurIPS*, 5998–6008.

Raffel, C., et al. (2020). Exploring the limits of transfer learning with a unified text-to-text transformer. *Journal of Machine Learning Research*, 21(140), 1–67.

OpenAI. (2024). GPT-4 technical report. arXiv preprint arXiv:2303.08774.

LGPD – Lei Geral de Proteção de Dados Pessoais. Lei nº 13.709/2018.

---

**Apêndice A: Estatísticas Descritivas do Dataset Processado**

*[Para ser preenchido após conclusão da EDA]*

- Total de linhas (trechos): _____
- Total de atividades: _____
- Total de questões únicas: _____
- Total de alunos anônimos: _____
- Distribuição por disciplina: [gráfico]
- Distribuição por categoria de feedback: [tabela frequências]
- Comprimento médio de explicações: _____ caracteres (σ = _____)
- % de registros com data_resposta preenchida: _____%
- % de registros com nota válida (≥ 0): _____%

---

**Apêndice B: Estrutura de Diretórios e Arquivos**

```
experimento_feedbacks_tutoria/
├── README.md                                  # Overview do projeto
├── turma-feedback-original.csv                # Dataset raw (não compartilhar)
├── turma_feedback_parsed.csv                  # Dataset processado (PÚBLICO)
├── turma_feedback_mapping_CONFIDENCIAL.csv    # Email → aluno_id (RESTRITO)
├── parse_feedback.py                          # Script de processamento
├── eda_turma_feedback.ipynb                   # Análise exploratória
├── build_eda_notebook.py                      # Gerador do notebook EDA
├── requirements.txt                           # Dependências Python
├── Dissertacao_Etapa_1.md                     # Este documento
└── experiments/                               # [Criado na Fase 2]
    ├── prompts/
    ├── results/
    └── evaluation/
```

