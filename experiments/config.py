"""
Configuracao central do experimento piloto:
10 questoes x 5 condicoes (professor + 2 teorias x 2 modelos) = 50 feedbacks.

Todos os scripts numerados (01_ ... 05_) importam daqui. Altere aqui, nao nos scripts.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DATASET = RAIZ.parent / "turma_feedback_parsed.csv"
PROMPTS_DIR = RAIZ / "prompts"
RESULTS_DIR = RAIZ / "results"
AVALIACAO_DIR = RESULTS_DIR / "avaliacao"
ANOTACOES_DIR = AVALIACAO_DIR / "anotacoes"   # planilhas preenchidas pelos anotadores
ANALISE_DIR = RESULTS_DIR / "analise"

AMOSTRA_PATH = RESULTS_DIR / "amostra_10.csv"
GERACOES_PATH = RESULTS_DIR / "geracoes_brutas.jsonl"
FEEDBACKS_PATH = RESULTS_DIR / "feedbacks_50.csv"
METRICAS_PATH = RESULTS_DIR / "metricas_automaticas.csv"
CHAVE_PATH = AVALIACAO_DIR / "chave_CONFIDENCIAL.csv"   # id_opaco -> condicao (NAO enviar aos anotadores)

SEED = 42

# ---------------------------------------------------------------------------
# Amostra
# ---------------------------------------------------------------------------
N_QUESTOES = 10
# estrato -> quantidade de questoes (soma deve ser N_QUESTOES)
ESTRATOS = {"so_acertos": 3, "misto": 4, "predominio_erros": 3}
IDIOMA = "pt"   # "pt", "en" ou None (sem filtro)
MIN_PALAVRAS_RESPOSTA = 5

CATEGORIAS_ESTRUTURADAS = ["ACERTOS", "ACERTOS PARCIAIS", "ERROS"]

# ---------------------------------------------------------------------------
# Modelos e condicoes
# ---------------------------------------------------------------------------
# Pipeline da tutoria (llm_analises_education/prompt_tutoria.py), por questao e modelo:
#   referencia -> conceito da referencia -> conceito do aluno -> feedback (teoria)
# Referencia e conceitos sao gerados uma vez por (questao, modelo) e compartilhados pelas
# duas teorias, entao dentro de um modelo so a camada teorica muda.
PROMPT_REFERENCIA = PROMPTS_DIR / "referencia.txt"
PROMPT_CONCEITO = PROMPTS_DIR / "conceito.txt"
PROMPT_ENTRADA = PROMPTS_DIR / "entrada_avaliacao.txt"   # mensagem do usuario na etapa de feedback
TEORIAS = {
    "hattie": PROMPTS_DIR / "hattie_timperley.txt",
    "nicol": PROMPTS_DIR / "nicol_macfarlane_dick.txt",
}
NOTA_MAXIMA = 10   # -100 = questao nao passivel de nota (regra da tutoria)

MODELOS = {
    "gpt41mini": {"provedor": "openai", "modelo": "gpt-4.1-mini"},
    "qwen": {"provedor": "ollama", "modelo": "qwen2.5:7b"},
}

# condicao -> (teoria, modelo); C0 = feedback original da tutoria (dataset)
CONDICOES = {
    "C0": (None, None),
    "C1": ("hattie", "gpt41mini"),
    "C2": ("hattie", "qwen"),
    "C3": ("nicol", "gpt41mini"),
    "C4": ("nicol", "qwen"),
}

GERACAO = {
    "temperature": 0.0,
    "seed": SEED,
    "max_tokens": 1000,
}
N_REPETICOES = 1   # geracoes por (questao, condicao); a analise usa a repeticao 1

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
TIMEOUT_S = 300

# ---------------------------------------------------------------------------
# Avaliacao humana
# ---------------------------------------------------------------------------
ANOTADORES = ["A", "B", "C"]

# coluna -> descricao (vai para o cabecalho/guia da planilha)
RUBRICA = {
    "correcao": "1-5: sem erros conceituais ou alucinacoes (5 = totalmente correto)",
    "clareza": "1-5: facil de entender para o aluno",
    "especificidade": "1-5: cita/aponta elementos concretos da resposta do aluno",
    "utilidade": "1-5: ajuda o aluno a melhorar",
    "feed_up": "0/1: explicita o objetivo / o que se esperava",
    "feed_back": "0/1: diz como o aluno foi (acertos/erros)",
    "feed_forward": "0/1: indica proximos passos",
    "nivel_predominante": "T=tarefa, P=processo, R=autorregulacao, S=pessoal",
    "autoavaliacao": "0/1: estimula o aluno a se autoavaliar (Nicol P2)",
    "fechar_lacuna": "0/1: mostra como fechar a lacuna (Nicol P6)",
    "autoria_percebida": "O=original da tutoria, N=novo (gerado no experimento)",
    "comentario": "texto livre (opcional)",
}
ESCALAS_ORDINAIS = ["correcao", "clareza", "especificidade", "utilidade"]
ESCALAS_BINARIAS = ["feed_up", "feed_back", "feed_forward", "autoavaliacao", "fechar_lacuna"]

# Metricas automaticas
BERTSCORE_MODEL = "bert-base-multilingual-cased"


def carregar_env():
    """Le experiments/.env (KEY=VALOR) sem depender de python-dotenv."""
    env_path = RAIZ / ".env"
    if not env_path.exists():
        return
    for linha in env_path.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
