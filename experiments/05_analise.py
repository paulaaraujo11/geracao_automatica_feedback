"""
Passo 5 - Analise das anotacoes humanas (e das metricas automaticas, se existirem).

Le results/avaliacao/anotacoes/planilha_anotador_*.csv (preenchidas), junta com a
chave e calcula:
  - concordancia entre anotadores (alfa de Krippendorff)
  - descritivas por condicao (mediana, IQR, proporcoes)
  - Friedman entre as 5 condicoes + W de Kendall
  - Wilcoxon pareado nos contrastes de interesse, correcao de Holm, r rank-biserial
  - teste cego: % de acerto em "autoria_percebida" (original da tutoria x novo)
  - boxplots

Uso:
    python experiments/05_analise.py
Gera:
    results/analise/*.csv e *.png
"""
import importlib.util
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

import config as cfg

CONTRASTES = [
    ("C1", "C3", "teoria (gpt-4.1-mini)"),
    ("C2", "C4", "teoria (qwen)"),
    ("C1", "C2", "modelo (hattie)"),
    ("C3", "C4", "modelo (nicol)"),
    ("C1", "C0", "vs tutoria original"),
    ("C2", "C0", "vs tutoria original"),
    ("C3", "C0", "vs tutoria original"),
    ("C4", "C0", "vs tutoria original"),
]


def carregar_anotacoes():
    arquivos = sorted(cfg.ANOTACOES_DIR.glob("planilha_anotador_*.csv"))
    if not arquivos:
        raise SystemExit(f"Nenhuma planilha preenchida em {cfg.ANOTACOES_DIR}")
    partes = []
    for arq in arquivos:
        a = pd.read_csv(arq, sep=";", encoding="utf-8-sig", dtype=str)
        a["anotador"] = arq.stem.replace("planilha_anotador_", "")
        partes.append(a)
    anot = pd.concat(partes, ignore_index=True)
    chave = pd.read_csv(cfg.CHAVE_PATH, dtype=str)
    anot = anot.drop(columns=["pergunta", "resposta_aluno", "feedback"], errors="ignore").merge(chave, on="id_opaco")
    for col in cfg.ESCALAS_ORDINAIS + cfg.ESCALAS_BINARIAS:
        anot[col] = pd.to_numeric(anot[col].str.replace(",", "."), errors="coerce")
    print(f"{len(arquivos)} anotadores, {len(anot)} avaliacoes")
    return anot


def holm(pvalores):
    p = np.asarray(pvalores, dtype=float)
    ordem = np.argsort(p)
    m = len(p)
    ajust = np.empty(m)
    acumulado = 0.0
    for rank, idx in enumerate(ordem):
        acumulado = max(acumulado, min(1.0, (m - rank) * p[idx]))
        ajust[idx] = acumulado
    return ajust


def rank_biserial(x, y):
    d = np.asarray(x) - np.asarray(y)
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(d))
    return (ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum()


def concordancia(anot):
    if not importlib.util.find_spec("krippendorff"):
        print("krippendorff nao instalado: pulando concordancia")
        return None
    import krippendorff
    linhas = []
    for col, nivel in [(c, "ordinal") for c in cfg.ESCALAS_ORDINAIS] + [(c, "nominal") for c in cfg.ESCALAS_BINARIAS]:
        matriz = anot.pivot_table(index="anotador", columns="id_opaco", values=col, aggfunc="first")
        try:
            alfa = krippendorff.alpha(reliability_data=matriz.to_numpy(), level_of_measurement=nivel)
        except ValueError:
            alfa = np.nan
        linhas.append({"dimensao": col, "nivel": nivel, "alfa_krippendorff": round(alfa, 3)})
    return pd.DataFrame(linhas)


def testes(por_questao, dimensoes, condicoes):
    friedman, pares = [], []
    for col in dimensoes:
        tab = por_questao.pivot(index="id_questao", columns="condicao", values=col)[condicoes].dropna()
        n, k = tab.shape
        if n >= 2:
            try:
                chi2, p = stats.friedmanchisquare(*[tab[c] for c in condicoes])
                friedman.append({"dimensao": col, "n": n, "chi2": chi2, "p": p,
                                 "W_kendall": chi2 / (n * (k - 1))})
            except ValueError:
                pass
        for a, b, rotulo in CONTRASTES:
            if a not in tab or b not in tab:
                continue
            x, y = tab[a], tab[b]
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    p = stats.wilcoxon(x, y).pvalue
            except ValueError:
                p = np.nan
            if np.isnan(p):   # todas as diferencas iguais a zero
                p = 1.0
            pares.append({"dimensao": col, "contraste": f"{a} x {b}", "tipo": rotulo,
                          "mediana_a": x.median(), "mediana_b": y.median(),
                          "p": p, "r_rank_biserial": rank_biserial(x, y)})
    pares = pd.DataFrame(pares)
    if not pares.empty:
        pares["p_holm"] = pares.groupby("dimensao").p.transform(holm)
    return pd.DataFrame(friedman).round(4), pares.round(4)


def analisar_humana(anot):
    out = cfg.ANALISE_DIR
    alfa = concordancia(anot)
    if alfa is not None:
        alfa.to_csv(out / "concordancia.csv", index=False)
        print("\nConcordancia entre anotadores:\n" + alfa.to_string(index=False))

    # media entre anotadores -> uma nota por (questao, condicao)
    dims = cfg.ESCALAS_ORDINAIS + cfg.ESCALAS_BINARIAS
    por_questao = anot.groupby(["id_questao", "condicao"], as_index=False)[dims].mean()
    por_questao.to_csv(out / "notas_por_questao.csv", index=False)

    desc = por_questao.groupby("condicao")[dims].agg(
        ["median", lambda s: s.quantile(.75) - s.quantile(.25), "mean"]).round(2)
    desc.columns = [f"{d}_{m if isinstance(m, str) else 'iqr'}".replace("<lambda_0>", "iqr") for d, m in desc.columns]
    desc.to_csv(out / "descritivas.csv")
    print("\nMedianas por condicao:\n" + por_questao.groupby("condicao")[dims].median().round(2).to_string())

    fried, pares = testes(por_questao, dims, list(cfg.CONDICOES))
    fried.to_csv(out / "friedman.csv", index=False)
    pares.to_csv(out / "wilcoxon_pares.csv", index=False)
    print("\nFriedman (5 condicoes):\n" + fried.to_string(index=False))

    nivel = pd.crosstab(anot.condicao, anot.nivel_predominante.str.upper().str.strip(), normalize="index").round(2)
    nivel.to_csv(out / "nivel_hattie.csv")
    print("\nNivel predominante (proporcao):\n" + nivel.to_string())

    autoria = anot.dropna(subset=["autoria_percebida"]).copy()
    if not autoria.empty:
        real = np.where(autoria.condicao == "C0", "O", "N")
        autoria["acertou"] = autoria.autoria_percebida.str.upper().str.strip() == real
        acc = autoria.groupby("condicao").acertou.mean().round(2)
        acc.to_csv(out / "teste_cego.csv")
        print(f"\nTeste cego - acerto geral: {autoria.acertou.mean():.0%}\n" + acc.to_string())

    longo = por_questao.melt(id_vars=["id_questao", "condicao"], value_vars=cfg.ESCALAS_ORDINAIS,
                             var_name="dimensao", value_name="nota")
    g = sns.catplot(data=longo, x="condicao", y="nota", col="dimensao", kind="box",
                    col_wrap=2, height=3.2, aspect=1.3, order=list(cfg.CONDICOES))
    g.set(ylim=(0.5, 5.5))
    g.savefig(out / "boxplot_rubrica.png", dpi=150)
    plt.close("all")


def analisar_automatica():
    if not cfg.METRICAS_PATH.exists():
        return
    met = pd.read_csv(cfg.METRICAS_PATH)
    dims = [c for c in ["rougeL_f1", "bertscore_f1", "n_palavras", "conformidade", "trecho_literal"] if c in met]
    llm = [c for c in cfg.CONDICOES if c != "C0"]
    _, pares = testes(met[met.repeticao == 1], dims, llm)
    pares = pares[~pares.contraste.str.contains("C0")] if not pares.empty else pares
    pares.to_csv(cfg.ANALISE_DIR / "wilcoxon_metricas_automaticas.csv", index=False)
    print("\nMetricas automaticas (media):\n" + met.groupby("condicao")[dims].mean().round(3).to_string())


def main():
    cfg.ANALISE_DIR.mkdir(parents=True, exist_ok=True)
    analisar_automatica()
    analisar_humana(carregar_anotacoes())
    print(f"\n-> {cfg.ANALISE_DIR}")


if __name__ == "__main__":
    main()
