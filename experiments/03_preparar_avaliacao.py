"""
Passo 3 - Normaliza os 50 feedbacks e monta as planilhas da avaliacao humana cega.

Uso:
    python experiments/03_preparar_avaliacao.py
Gera:
    results/feedbacks_50.csv                       (atualizado com versoes normalizadas)
    results/avaliacao/planilha_anotador_<X>.csv    (uma por anotador, ordem embaralhada diferente)
    results/avaliacao/guia_rubrica.txt
    results/avaliacao/chave_CONFIDENCIAL.csv       (id_opaco -> condicao; NAO enviar aos anotadores)

As planilhas usam ';' e UTF-8 com BOM para abrir direto no Excel em portugues.
Depois de preenchidas, salve-as em results/avaliacao/anotacoes/ com o mesmo nome.
"""
import random

import pandas as pd

import config as cfg
from normalizacao import normalizar, versao_aluno


def main():
    df = pd.read_csv(cfg.FEEDBACKS_PATH, dtype=str)
    df["feedback_normalizado"] = df.feedback_bruto.map(normalizar)
    df["feedback_aluno"] = df.feedback_bruto.map(versao_aluno)
    df.to_csv(cfg.FEEDBACKS_PATH, index=False, encoding="utf-8")

    avaliar = df[df.repeticao == "1"].copy()
    esperado = cfg.N_QUESTOES * len(cfg.CONDICOES)
    if len(avaliar) != esperado:
        print(f"AVISO: {len(avaliar)} feedbacks para avaliar (esperado {esperado}). Faltam geracoes?")
        print(avaliar.groupby("condicao").size().to_string())

    rng = random.Random(cfg.SEED)
    ids = [f"F{i:02d}" for i in range(1, len(avaliar) + 1)]
    rng.shuffle(ids)
    avaliar["id_opaco"] = ids

    cfg.AVALIACAO_DIR.mkdir(parents=True, exist_ok=True)
    cfg.ANOTACOES_DIR.mkdir(parents=True, exist_ok=True)
    avaliar[["id_opaco", "id_questao", "condicao", "teoria", "modelo"]].sort_values("id_opaco").to_csv(
        cfg.CHAVE_PATH, index=False, encoding="utf-8")

    base = avaliar[["id_opaco", "pergunta", "resposta_aluno", "feedback_aluno"]].rename(
        columns={"feedback_aluno": "feedback"})
    for col in cfg.RUBRICA:
        base[col] = ""

    for i, anotador in enumerate(cfg.ANOTADORES):
        planilha = base.sample(frac=1, random_state=cfg.SEED + i)
        caminho = cfg.AVALIACAO_DIR / f"planilha_anotador_{anotador}.csv"
        planilha.to_csv(caminho, index=False, sep=";", encoding="utf-8-sig")
        print(f"-> {caminho}")

    guia = ["GUIA DA RUBRICA", "",
            "Avalie cada feedback considerando a pergunta e a resposta do aluno.",
            "Voce nao sabe qual sistema gerou cada feedback. Avalie cada um isoladamente.", ""]
    guia += [f"{col}: {desc}" for col, desc in cfg.RUBRICA.items()]
    (cfg.AVALIACAO_DIR / "guia_rubrica.txt").write_text("\n".join(guia), encoding="utf-8")

    print(f"-> {cfg.CHAVE_PATH}  (CONFIDENCIAL - nao enviar aos anotadores)")


if __name__ == "__main__":
    main()
