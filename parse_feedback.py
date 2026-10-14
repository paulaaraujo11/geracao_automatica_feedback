"""
Parser do CSV bruto de feedback (Google Forms / Moodle) para formato longo,
anonimizado, um registro por "trecho" de feedback (unidade atomica: um pedaco
da resposta do aluno + categoria de acerto + explicacao).

Uso:
    python parse_feedback.py

Gera:
    turma_feedback_parsed.csv          -> dataset anonimizado para EDA/pesquisa
    turma_feedback_mapping_CONFIDENCIAL.csv -> email -> aluno_id (NAO compartilhar)
"""
import codecs
import csv
import hashlib
import re
import sys
from html import unescape

import warnings

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

INPUT_PATH = "turma-feedback-original.csv"
OUTPUT_PATH = "turma_feedback_parsed.csv"
MAPPING_PATH = "turma_feedback_mapping_CONFIDENCIAL.csv"

STOPLIST_NOMES = {
    "aluno não encontrado",
    "aluno nao encontrado",
    "aluno não cadastrado",
    "aluno nao cadastrado",
}

SALT = "experimento_v1_feedback"  # apenas para estabilidade do hash, nao seguranca criptografica


# ---------------------------------------------------------------------------
# 1. Encoding misto (UTF-8 com aspas tipograficas coladas em cp1252)
# ---------------------------------------------------------------------------
def _mixed_fallback(err):
    bad = err.object[err.start:err.end]
    return bad.decode("cp1252", errors="replace"), err.end


codecs.register_error("mixedfallback", _mixed_fallback)


def load_rows(path):
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("utf-8", errors="mixedfallback")
    reader = csv.DictReader(text.splitlines(keepends=True))
    return list(reader)


# ---------------------------------------------------------------------------
# 2. Anonimizacao
# ---------------------------------------------------------------------------
def anon_id_for(email, cache):
    if email not in cache:
        h = hashlib.sha256((SALT + email.lower().strip()).encode("utf-8")).hexdigest()[:10]
        cache[email] = f"ALU_{h}"
    return cache[email]


GREETING_RE = re.compile(
    r"^(?:Ol[áa]|Bom dia)[, ]*(?:<b>)?\s*([^!<,\n]{2,80}?)\s*(?:</b>)?\s*[!,]",
    re.IGNORECASE,
)
CLOSING_RE = re.compile(
    r"At[ée] logo,?!?\s*(?:<b>)?\s*([^.<\n]{2,80}?)\s*(?:</b>)?\s*\.\s*$",
    re.IGNORECASE,
)


def extract_names(html):
    names = set()
    m = GREETING_RE.match(html)
    if m:
        names.add(m.group(1).strip())
    m = CLOSING_RE.search(html)
    if m:
        names.add(m.group(1).strip())
    return {n for n in names if n and n.lower() not in STOPLIST_NOMES}


def redact_names(html, names, placeholder):
    for name in names:
        if name:
            html = html.replace(name, placeholder)
    return html


# ---------------------------------------------------------------------------
# 3. Campos do cabecalho (nota, datas)
# ---------------------------------------------------------------------------
NOTA_RE = re.compile(r"nota[^<]{0,60}?<b>\s*(-?\d+(?:[.,]\d+)?)\s*</b>", re.IGNORECASE)
ENTREGA_RE = re.compile(r"entregue no dia\s*<b>(.*?)</b>", re.IGNORECASE)
DISPONIB_RE = re.compile(r"disponibilizad[ao] no dia\s*<b>(.*?)</b>", re.IGNORECASE)

Q_MARKER_RE = re.compile(r"Q(\d+)\.")
TRAILING_SIGNOFF_RE = re.compile(r"(?:<br\s*/?>\s*)*At[ée] logo.*$", re.IGNORECASE | re.DOTALL)

BLOCK_RE = re.compile(
    r"^\s*(?:<b>(?P<pergunta>.*?)</b>\s*<br\s*/?>\s*(?P<resposta>.*?))?"
    r"\s*<br\s*/?>\s*<br\s*/?>\s*Feedback:\s*(?P<feedback>.*)$",
    re.IGNORECASE | re.DOTALL,
)


def clean_text(html_fragment):
    if html_fragment is None:
        return ""
    text = BeautifulSoup(html_fragment, "lxml").get_text(separator=" ")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_feedback_block(feedback_html):
    """Retorna lista de dicts {categoria, trecho, explicacao} para um bloco de feedback."""
    stripped = feedback_html.strip()

    if re.match(r"^\s*N[ãa]o respondida", stripped, re.IGNORECASE):
        return [{"categoria": "NAO_RESPONDIDA", "trecho": None, "explicacao": None}]

    if re.match(r"^\s*<b>\s*Sem feedback do professor", stripped, re.IGNORECASE):
        return [{"categoria": "SEM_FEEDBACK_PROFESSOR", "trecho": None, "explicacao": None}]

    if "<h2>" not in stripped:
        texto = clean_text(stripped)
        if not texto:
            return [{"categoria": "VAZIO", "trecho": None, "explicacao": None}]
        return [{"categoria": "TEXTO_LIVRE", "trecho": None, "explicacao": texto}]

    soup = BeautifulSoup(stripped, "lxml")
    out = []
    for h2 in soup.find_all("h2"):
        categoria = clean_text(str(h2)).upper()
        ul = h2.find_next_sibling("ul")
        if ul is None:
            continue
        trechos_li = ul.find_all("li", recursive=False)
        if not trechos_li:
            out.append({"categoria": categoria, "trecho": None, "explicacao": None})
            continue
        for li in trechos_li:
            nested_ul = li.find("ul")
            if nested_ul is not None:
                explicacao = clean_text(str(nested_ul))
                trecho_html = str(li)
                trecho_html = trecho_html[: trecho_html.find("<ul")]
                trecho = clean_text(trecho_html)
                nested_ul.extract()  # nao usado depois, so por clareza
            else:
                trecho = clean_text(str(li))
                explicacao = None
            out.append({"categoria": categoria, "trecho": trecho, "explicacao": explicacao})
    if not out:
        out.append({"categoria": "OUTRO", "trecho": None, "explicacao": clean_text(stripped)})
    return out


ROTULOS_SEM_CONTEUDO = {
    "NAO_RESPONDIDA": "Não respondida",
    "SEM_FEEDBACK_PROFESSOR": "Sem feedback do professor",
    "VAZIO": "",
}


def montar_feedback_completo(itens):
    """Junta todos os itens de uma questao (acertos, parciais, erros...) em um texto unico."""
    linhas = []
    categoria_atual = None
    for item in itens:
        cat = item["categoria"]
        if cat in ROTULOS_SEM_CONTEUDO:
            if ROTULOS_SEM_CONTEUDO[cat]:
                linhas.append(ROTULOS_SEM_CONTEUDO[cat])
            continue
        if cat in ("TEXTO_LIVRE", "OUTRO"):
            if item["explicacao"]:
                linhas.append(item["explicacao"])
            continue
        if cat != categoria_atual:
            linhas.append(f"{cat}:")
            categoria_atual = cat
        partes = [p for p in (item["trecho"], item["explicacao"]) if p]
        if partes:
            linhas.append("- " + " -> ".join(partes))
    return "\n".join(linhas) or None


def split_questions(html_after_intro):
    """Divide o corpo (apos remover intro) em blocos por marcador Q<n>."""
    parts = Q_MARKER_RE.split(html_after_intro)
    # parts = [texto_antes_do_primeiro_Q(vazio), num1, bloco1, num2, bloco2, ...]
    blocks = []
    for i in range(1, len(parts), 2):
        num = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        blocks.append((num, body))
    return blocks


def parse_row(row, idx, id_cache):
    html = row["feedback_final_html"] or ""

    names = extract_names(html)
    email = (row["aluno_email"] or "").strip()
    aluno_id = anon_id_for(email, id_cache) if email else "SEM_EMAIL"
    html = redact_names(html, names, f"[{aluno_id}]")

    m = Q_MARKER_RE.search(html)
    intro = html[: m.start()] if m else html
    corpo = html[m.start():] if m else ""

    nota_m = NOTA_RE.search(intro)
    nota = nota_m.group(1) if nota_m else None
    entrega_m = ENTREGA_RE.search(intro)
    data_entrega = clean_text(entrega_m.group(1)) if entrega_m else None
    disponib_m = DISPONIB_RE.search(intro)
    data_disponibilizacao = clean_text(disponib_m.group(1)) if disponib_m else None

    base = {
        "id_atividade": idx,
        "disciplina": row["disciplina"],
        "secao": row["secao"],
        "tipo": row["tipo"],
        "aluno_id": aluno_id,
        "data_resposta": row["data_resposta"],
        "email_enviado": row["email_enviado"],
        "nota_atividade": nota,
        "data_entrega": data_entrega,
        "data_disponibilizacao": data_disponibilizacao,
    }

    out_rows = []
    blocks = split_questions(corpo)

    if not blocks:
        texto = clean_text(intro)
        out_rows.append({
            **base, "num_questao": None, "pergunta": None, "resposta_aluno": None,
            "categoria_feedback": "SEM_QUESTOES", "trecho": None, "explicacao": texto or None,
            "feedback_completo": texto or None,
        })
        return out_rows

    for num, body in blocks:
        bm = BLOCK_RE.match(body)
        if bm:
            pergunta = clean_text(bm.group("pergunta"))
            resposta = clean_text(bm.group("resposta"))
            feedback_html = bm.group("feedback")
        else:
            pergunta, resposta, feedback_html = None, None, body

        feedback_html = TRAILING_SIGNOFF_RE.sub("", feedback_html)
        itens = parse_feedback_block(feedback_html)
        feedback_completo = montar_feedback_completo(itens)
        for item in itens:
            out_rows.append({
                **base,
                "num_questao": num,
                "pergunta": pergunta or None,
                "resposta_aluno": resposta or None,
                "categoria_feedback": item["categoria"],
                "trecho": item["trecho"],
                "explicacao": item["explicacao"],
                "feedback_completo": feedback_completo,
            })
    return out_rows


def main():
    rows = load_rows(INPUT_PATH)
    id_cache = {}
    out_rows = []
    for idx, row in enumerate(rows):
        out_rows.extend(parse_row(row, idx, id_cache))

    fieldnames = [
        "id_atividade", "disciplina", "secao", "tipo", "aluno_id", "data_resposta",
        "email_enviado", "nota_atividade", "data_entrega", "data_disponibilizacao",
        "num_questao", "pergunta", "resposta_aluno", "categoria_feedback", "trecho", "explicacao",
        "feedback_completo",
    ]
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    with open(MAPPING_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["aluno_email", "aluno_id"])
        for email, aid in id_cache.items():
            writer.writerow([email, aid])

    print(f"Linhas de entrada (atividades): {len(rows)}")
    print(f"Linhas de saida (trechos de feedback): {len(out_rows)}")
    print(f"Alunos unicos: {len(id_cache)}")
    print(f"-> {OUTPUT_PATH}")
    print(f"-> {MAPPING_PATH}  (CONFIDENCIAL - nao commitar/compartilhar)")


if __name__ == "__main__":
    main()
