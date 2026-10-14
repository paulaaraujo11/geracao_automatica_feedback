"""
Passo 1 - Seleciona as N questoes do experimento a partir do dataset processado.

Unidade = questao (id_atividade + num_questao). Estratifica pelo desempenho
indicado no feedback do professor e espalha entre disciplinas, com no maximo
uma questao por aluno e por atividade.

Uso:
    python experiments/01_amostra.py
Gera:
    experiments/results/amostra_10.csv
"""
import random
import re
import sys
from collections import Counter

import pandas as pd

import config as cfg

STOP_PT = {"de", "que", "não", "nao", "é", "uma", "um", "para", "com", "os", "as", "do", "da", "por", "mais", "como", "são"}
STOP_EN = {"the", "is", "of", "and", "to", "it", "that", "in", "for", "are", "this", "with", "be", "not", "can"}


def idioma_aprox(texto):
    palavras = re.findall(r"\w+", (texto or "").lower())
    pt = sum(p in STOP_PT for p in palavras)
    en = sum(p in STOP_EN for p in palavras)
    if pt == en:
        return "indef"
    return "pt" if pt > en else "en"


def estrato_da_questao(grupo):
    cont = Counter(c for c in grupo["categoria_feedback"] if c in cfg.CATEGORIAS_ESTRUTURADAS)
    acertos = cont["ACERTOS"]
    problemas = cont["ACERTOS PARCIAIS"] + cont["ERROS"]
    if problemas == 0:
        return "so_acertos"
    if cont["ERROS"] > 0 and cont["ERROS"] >= acertos:
        return "predominio_erros"
    return "misto"


def montar_candidatas(df):
    # so questoes cujo feedback e totalmente estruturado (sem NAO_RESPONDIDA, TEXTO_LIVRE etc.)
    ok = df.groupby(["id_atividade", "num_questao"])["categoria_feedback"].transform(
        lambda s: s.isin(cfg.CATEGORIAS_ESTRUTURADAS).all()
    )
    df = df[ok]

    linhas = []
    for (ativ, num), g in df.groupby(["id_atividade", "num_questao"], sort=False):
        r = g.iloc[0]
        if pd.isna(r.pergunta) or pd.isna(r.resposta_aluno) or pd.isna(r.feedback_completo):
            continue
        if len(str(r.resposta_aluno).split()) < cfg.MIN_PALAVRAS_RESPOSTA:
            continue
        linhas.append({
            "id_questao": f"{ativ}_Q{num}",
            "id_atividade": ativ,
            "num_questao": num,
            "disciplina": r.disciplina,
            "aluno_id": r.aluno_id,
            "nota_atividade": r.nota_atividade,
            "idioma": idioma_aprox(f"{r.pergunta} {r.resposta_aluno}"),
            "estrato": estrato_da_questao(g),
            "n_itens_professor": len(g),
            "pergunta": r.pergunta,
            "resposta_aluno": r.resposta_aluno,
            "feedback_completo": r.feedback_completo,
        })
    cand = pd.DataFrame(linhas)
    if cfg.IDIOMA:
        cand = cand[cand.idioma == cfg.IDIOMA]
    return cand


def selecionar(cand):
    rng = random.Random(cfg.SEED)
    usados_aluno, usados_ativ = set(), set()
    uso_disc = Counter()
    escolhidas = []

    for estrato, n in cfg.ESTRATOS.items():
        pool = cand[cand.estrato == estrato].to_dict("records")
        rng.shuffle(pool)
        for _ in range(n):
            validas = [q for q in pool
                       if q["aluno_id"] not in usados_aluno and q["id_atividade"] not in usados_ativ]
            if not validas:
                sys.exit(f"Candidatas insuficientes no estrato '{estrato}'. Ajuste ESTRATOS/IDIOMA em config.py.")
            # prioriza a disciplina menos usada ate agora (espalha a amostra)
            q = min(validas, key=lambda x: uso_disc[x["disciplina"]])
            escolhidas.append(q)
            pool.remove(q)
            usados_aluno.add(q["aluno_id"])
            usados_ativ.add(q["id_atividade"])
            uso_disc[q["disciplina"]] += 1
    return pd.DataFrame(escolhidas)


def main():
    assert sum(cfg.ESTRATOS.values()) == cfg.N_QUESTOES, "ESTRATOS deve somar N_QUESTOES"
    df = pd.read_csv(cfg.DATASET, dtype=str)
    cand = montar_candidatas(df)
    print(f"Questoes candidatas: {len(cand)}")
    print(cand.estrato.value_counts().to_string())

    amostra = selecionar(cand)
    cfg.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    amostra.to_csv(cfg.AMOSTRA_PATH, index=False, encoding="utf-8")

    print(f"\nAmostra ({len(amostra)} questoes) -> {cfg.AMOSTRA_PATH}")
    print(amostra[["id_questao", "estrato", "idioma", "disciplina"]].to_string(index=False))


if __name__ == "__main__":
    main()
