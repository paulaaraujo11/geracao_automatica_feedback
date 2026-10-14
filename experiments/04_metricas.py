"""
Passo 4 - Metricas automaticas de C1-C4 contra o feedback original da tutoria (C0).

- ROUGE-L F1 e BERTScore F1 sobre feedback_normalizado (so acertos/parciais/erros)
- n_palavras do feedback_aluno e idioma do feedback
- conformidade ao esquema JSON, % de trechos literais e nota sugerida (vindos do passo 2)

Uso:
    python experiments/04_metricas.py
Gera:
    results/metricas_automaticas.csv
"""
import importlib
import importlib.util

import pandas as pd

import config as cfg

amostra_mod = importlib.import_module("01_amostra")


def main():
    df = pd.read_csv(cfg.FEEDBACKS_PATH, dtype=str).fillna("")
    if "feedback_normalizado" not in df:
        raise SystemExit("Rode antes: python experiments/03_preparar_avaliacao.py")

    ref = df[df.condicao == "C0"].set_index("id_questao").feedback_normalizado
    df["referencia"] = df.id_questao.map(ref)
    df["n_palavras"] = df.feedback_aluno.str.split().str.len()
    df["idioma_feedback"] = df.feedback_aluno.map(amostra_mod.idioma_aprox)

    llm = df[df.condicao != "C0"].copy()

    if importlib.util.find_spec("rouge_score"):
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
        llm["rougeL_f1"] = [scorer.score(r, c)["rougeL"].fmeasure
                            for r, c in zip(llm.referencia, llm.feedback_normalizado)]
    else:
        print("rouge-score nao instalado: pulando ROUGE-L")

    if importlib.util.find_spec("bert_score"):
        from bert_score import score
        _, _, f1 = score(llm.feedback_normalizado.tolist(), llm.referencia.tolist(),
                         model_type=cfg.BERTSCORE_MODEL, verbose=False)
        llm["bertscore_f1"] = f1.numpy()
    else:
        print("bert-score nao instalado: pulando BERTScore")

    saida = pd.concat([df[df.condicao == "C0"], llm]).drop(columns=["referencia"])
    saida.to_csv(cfg.METRICAS_PATH, index=False, encoding="utf-8")

    cols = [c for c in ["rougeL_f1", "bertscore_f1", "n_palavras", "conformidade", "trecho_literal",
                        "n_tags", "nota_sugerida"] if c in saida]
    saida[cols] = saida[cols].apply(pd.to_numeric, errors="coerce")
    print(saida.groupby("condicao")[cols].agg(["mean", "std"]).round(3).to_string())
    print(f"\n-> {cfg.METRICAS_PATH}")


if __name__ == "__main__":
    main()
