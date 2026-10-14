"""
Conversao dos feedbacks (JSON do LLM ou texto do professor/tutoria) para texto, e
geracao das versoes usadas no experimento:

- renderizar(js, teoria): JSON do LLM -> texto em secoes (ACERTOS / ACERTOS PARCIAIS /
  ERROS no mesmo formato "- titulo -> feedback" do feedback_completo da tutoria).
- feedback_normalizado: so ACERTOS / ACERTOS PARCIAIS / ERROS -> metricas de similaridade.
- feedback_aluno: o que o aluno veria, sem marcadores que revelem a condicao
  ([nivel: ...]), sem secoes vazias e sem a NOTA PARA O PROFESSOR -> avaliacao cega.
- validar(js, teoria, resposta): conformidade ao esquema e literalidade dos trechos.
"""
import json
import re
import unicodedata

SECOES_DIAGNOSTICO = ["ACERTOS", "ACERTOS PARCIAIS", "ERROS"]
SECOES_OCULTAS_ALUNO = {"NOTA PARA O PROFESSOR"}
TIPO_SECAO = {"HIT": "ACERTOS", "PARTIAL_HIT": "ACERTOS PARCIAIS", "ERROR": "ERROS"}

# campos obrigatorios do JSON por teoria (justificativa pode ser "")
CAMPOS = {
    "hattie": ["nota_sugerida", "feed_up", "tags", "justificativa", "feed_forward"],
    "nicol": ["nota_sugerida", "criterios", "tags", "justificativa", "como_melhorar",
              "autoavaliacao", "para_conversar", "nota_professor"],
}
CAMPOS_TAG = ["titulo", "trecho", "tipo", "feedback"]

HEADER_RE = re.compile(r"^([A-ZÀ-Ý][A-ZÀ-Ý ]+?)\s*(?:\([^)]*\))?\s*:\s*(.*)$")
MARCADOR_RE = re.compile(r"\s*\[\s*n[íi]vel\s*:[^\]]*\]", re.IGNORECASE)
NENHUM_RE = re.compile(r"^-?\s*nenhum\.?$", re.IGNORECASE)
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


# ---------------------------------------------------------------------------
# JSON do LLM
# ---------------------------------------------------------------------------
def extrair_json(texto):
    """Le o JSON da resposta, tolerando <think>, cercas ``` e texto em volta."""
    texto = THINK_RE.sub("", texto or "").strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        ini, fim = texto.find("{"), texto.rfind("}")
        if ini == -1 or fim <= ini:
            raise ValueError("resposta sem JSON")
        return json.loads(texto[ini:fim + 1])


def _txt(item, chave):
    """Itens de lista podem vir como string ou como dict ({"acao": ...})."""
    if isinstance(item, dict):
        return str(item.get(chave) or next(iter(item.values()), "")).strip()
    return str(item).strip()


def _nivel(item):
    return f" [nível: {item['nivel']}]" if isinstance(item, dict) and item.get("nivel") else ""


def _lista(valor):
    if not valor:
        return []
    return valor if isinstance(valor, list) else [valor]


def renderizar(js, teoria):
    blocos = []

    def secao(nome, linhas):
        linhas = [l for l in linhas if l.strip(" -")]
        if linhas:
            blocos.append(f"{nome}:\n" + "\n".join(linhas))

    if teoria == "hattie":
        secao("OBJETIVO", [str(js.get("feed_up") or "")])
    else:
        secao("O QUE SE ESPERAVA", [f"- {_txt(c, 'criterio')}" for c in _lista(js.get("criterios"))])

    tags = [t for t in _lista(js.get("tags")) if isinstance(t, dict)]
    for tipo, nome in TIPO_SECAO.items():
        secao(nome, [f"- {t.get('titulo', '')} -> {t.get('feedback', '')}{_nivel(t)}"
                     for t in tags if str(t.get("tipo", "")).upper() == tipo])

    secao("COMENTÁRIO GERAL", [str(js.get("justificativa") or "")])

    if teoria == "hattie":
        secao("PRÓXIMOS PASSOS", [f"- {_txt(p, 'acao')}{_nivel(p)}" for p in _lista(js.get("feed_forward"))])
    else:
        secao("COMO MELHORAR", [f"- {_txt(p, 'acao')}" for p in _lista(js.get("como_melhorar"))])
        secao("AUTOAVALIAÇÃO", [f"- {_txt(p, 'pergunta')}" for p in _lista(js.get("autoavaliacao"))])
        secao("PARA CONVERSAR", [_txt(p, "pergunta") for p in _lista(js.get("para_conversar"))])
        secao("NOTA PARA O PROFESSOR", [_txt(p, "nota") for p in _lista(js.get("nota_professor"))])
    return "\n".join(blocos)


def _norm(s):
    """Ignora caixa, acentos, aspas e pontuacao: so conta trecho inventado ou alterado."""
    s = unicodedata.normalize("NFKD", str(s).casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def validar(js, teoria, resposta_aluno):
    """
    conformidade: fracao dos campos obrigatorios presentes (e nao vazios, exceto justificativa)
                  com tags bem formadas.
    trecho_literal: fracao das tags cujo trecho aparece literalmente na resposta do aluno
                    (indicador de alucinacao na marcacao).
    """
    campos = CAMPOS[teoria]
    ok = 0
    for c in campos:
        if c == "justificativa":
            ok += c in js
        elif c == "tags":
            tags = js.get("tags")
            ok += bool(tags) and all(isinstance(t, dict) and all(t.get(k) for k in CAMPOS_TAG)
                                     and str(t["tipo"]).upper() in TIPO_SECAO for t in tags)
        else:
            ok += js.get(c) not in (None, "", [])
    tags = [t for t in _lista(js.get("tags")) if isinstance(t, dict)]
    resp = _norm(resposta_aluno)
    literais = [bool(t.get("trecho")) and _norm(t["trecho"]) in resp for t in tags]
    return {
        "conformidade": ok / len(campos),
        "n_tags": len(tags),
        "trecho_literal": sum(literais) / len(literais) if literais else None,
    }


# ---------------------------------------------------------------------------
# Texto em secoes
# ---------------------------------------------------------------------------
def _limpar_markdown(linha):
    linha = re.sub(r"^#+\s*", "", linha.strip())
    return linha.replace("**", "").replace("__", "")


def parse_secoes(texto):
    """Retorna lista ordenada [(secao, [linhas])]. Texto antes do 1o cabecalho vai em secao ''."""
    secoes = [("", [])]
    for bruta in (texto or "").splitlines():
        linha = _limpar_markdown(bruta)
        if not linha:
            continue
        m = HEADER_RE.match(linha)
        if m:
            secoes.append((m.group(1).strip(), []))
            if m.group(2).strip():
                secoes[-1][1].append(m.group(2).strip())
        else:
            secoes[-1][1].append(MARCADOR_RE.sub("", linha).rstrip())
    return [(s, ls) for s, ls in secoes if s or ls]


def _renderizar_secoes(secoes):
    blocos = [(f"{s}:\n" if s else "") + "\n".join(ls) for s, ls in secoes]
    return "\n".join(blocos).strip()


def normalizar(texto):
    secoes = []
    for s, ls in parse_secoes(texto):
        if s in SECOES_DIAGNOSTICO:
            itens = [l for l in ls if not NENHUM_RE.match(l)]
            if itens:
                secoes.append((s, itens))
    return _renderizar_secoes(secoes)


def versao_aluno(texto):
    secoes = []
    for s, ls in parse_secoes(texto):
        itens = [l for l in ls if not NENHUM_RE.match(l)]
        if s not in SECOES_OCULTAS_ALUNO and itens:   # secao "- Nenhum" denunciaria o LLM
            secoes.append((s, itens))
    return _renderizar_secoes(secoes)
