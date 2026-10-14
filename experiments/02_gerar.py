"""
Passo 2 - Gera os feedbacks das condicoes LLM (C1-C4) com o pipeline da tutoria
(llm_analises_education/prompt_tutoria.py):

    por (questao, modelo):  referencia -> conceito_ref -> conceito_aluno   (uma vez, compartilhado)
    por (questao, condicao): feedback com o prompt da teoria (hattie | nicol)

Todas as chamadas pedem JSON. Cada uma e gravada em results/geracoes_brutas.jsonl assim
que termina; rodar de novo pula o que ja foi feito (retomavel). No fim monta
results/feedbacks_50.csv com C0 (tutoria original) + C1-C4.

Uso:
    python experiments/02_gerar.py                     # todas as condicoes
    python experiments/02_gerar.py --condicoes C2 C4   # so Ollama
    python experiments/02_gerar.py --dry-run           # mostra os prompts da 1a questao, nao chama nada

Pre-requisitos:
    OpenAI: OPENAI_API_KEY no ambiente ou em experiments/.env
    Ollama: `ollama serve` rodando e `ollama pull qwen2.5:7b`
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

import config as cfg
from normalizacao import extrair_json, renderizar, validar


# ---------------------------------------------------------------------------
# Provedores (system + user, saida em JSON)
# ---------------------------------------------------------------------------
_openai_client = None


def chamar_openai(modelo, system, user):
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
    t0 = time.time()
    resp = _openai_client.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=cfg.GERACAO["temperature"],
        seed=cfg.GERACAO["seed"],
        max_tokens=cfg.GERACAO["max_tokens"],
    )
    return {
        "texto": resp.choices[0].message.content,
        "modelo_versao": resp.model,
        "fingerprint": resp.system_fingerprint,
        "tokens_entrada": resp.usage.prompt_tokens,
        "tokens_saida": resp.usage.completion_tokens,
        "finish_reason": resp.choices[0].finish_reason,
        "tempo_s": round(time.time() - t0, 2),
    }


_ollama_digest = {}


def digest_ollama(modelo):
    if modelo not in _ollama_digest:
        with urllib.request.urlopen(f"{cfg.OLLAMA_URL}/api/tags", timeout=30) as r:
            tags = json.loads(r.read().decode("utf-8"))["models"]
        _ollama_digest[modelo] = next((m["digest"] for m in tags if m["name"] == modelo), None)
        if _ollama_digest[modelo] is None:
            sys.exit(f"Modelo '{modelo}' nao encontrado no Ollama. Rode: ollama pull {modelo}")
    return _ollama_digest[modelo]


def chamar_ollama(modelo, system, user):
    digest = digest_ollama(modelo)
    payload = {
        "model": modelo,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": cfg.GERACAO["temperature"],
            "seed": cfg.GERACAO["seed"],
            "num_predict": cfg.GERACAO["max_tokens"],
        },
    }
    req = urllib.request.Request(f"{cfg.OLLAMA_URL}/api/chat", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=cfg.TIMEOUT_S) as r:
        resp = json.loads(r.read().decode("utf-8"))
    return {
        "texto": resp["message"]["content"],
        "modelo_versao": f"{modelo}@{digest[:12]}",
        "fingerprint": digest,
        "tokens_entrada": resp.get("prompt_eval_count"),
        "tokens_saida": resp.get("eval_count"),
        "finish_reason": resp.get("done_reason"),
        "tempo_s": round(time.time() - t0, 2),
    }


PROVEDORES = {"openai": chamar_openai, "ollama": chamar_ollama}


# ---------------------------------------------------------------------------
# Etapas do pipeline
# ---------------------------------------------------------------------------
def ler(caminho):
    return caminho.read_text(encoding="utf-8")


def mensagens_preparo(etapa, q, prep):
    if etapa == "referencia":
        return ler(cfg.PROMPT_REFERENCIA), f"Disciplina: {q['disciplina']}\nPergunta: {q['pergunta']}"
    if etapa == "conceito_ref":
        return ler(cfg.PROMPT_CONCEITO), prep["referencia"]["resposta_referencia"]
    if etapa == "conceito_aluno":
        return ler(cfg.PROMPT_CONCEITO), q["resposta_aluno"]
    raise ValueError(etapa)


def mensagens_feedback(teoria, q, prep):
    user = ler(cfg.PROMPT_ENTRADA).format(
        disciplina=q["disciplina"],
        pergunta=q["pergunta"],
        resposta_aluno=q["resposta_aluno"],
        conceito_aluno=prep["conceito_aluno"].get("conceito_principal", ""),
        resposta_referencia=prep["referencia"].get("resposta_referencia", ""),
        conceito_referencia=prep["conceito_ref"].get("conceito_principal", ""),
        nota_maxima=cfg.NOTA_MAXIMA,
    )
    return ler(cfg.TEORIAS[teoria]), user


ETAPAS_PREPARO = ["referencia", "conceito_ref", "conceito_aluno"]


def executar(out, modelo_key, system, user, registro_base):
    m = cfg.MODELOS[modelo_key]
    res = PROVEDORES[m["provedor"]](m["modelo"], system, user)
    js = extrair_json(res["texto"])   # ValueError/JSONDecodeError -> tratado por quem chama
    registro = {
        **registro_base,
        "modelo_key": modelo_key, "modelo": m["modelo"], "provedor": m["provedor"],
        "parametros": cfg.GERACAO,
        "prompt_sha256": hashlib.sha256((system + "\n\n" + user).encode("utf-8")).hexdigest(),
        "system": system, "user": user,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **res, "json": js,
    }
    out.write(json.dumps(registro, ensure_ascii=False) + "\n")
    out.flush()
    return registro


def carregar_registros():
    if not cfg.GERACOES_PATH.exists():
        return []
    with open(cfg.GERACOES_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def montar_feedbacks_50(amostra, registros):
    linhas = [{
        "id_questao": q["id_questao"], "condicao": "C0", "fonte": "tutoria_original",
        "teoria": None, "modelo": None, "modelo_versao": None, "repeticao": 1,
        "feedback_bruto": q["feedback_completo"],
    } for q in amostra.to_dict("records")]

    resposta = amostra.set_index("id_questao").resposta_aluno
    for g in registros:
        if g["etapa"] != "feedback":
            continue
        linhas.append({
            "id_questao": g["id_questao"], "condicao": g["condicao"], "fonte": "llm",
            "teoria": g["teoria"], "modelo": g["modelo"], "modelo_versao": g["modelo_versao"],
            "repeticao": g["repeticao"],
            "feedback_bruto": renderizar(g["json"], g["teoria"]),
            "feedback_json": json.dumps(g["json"], ensure_ascii=False),
            "nota_sugerida": g["json"].get("nota_sugerida"),
            **validar(g["json"], g["teoria"], resposta[g["id_questao"]]),
            "tokens_saida": g["tokens_saida"], "tempo_s": g["tempo_s"],
        })
    df = pd.DataFrame(linhas)
    df = df.merge(amostra[["id_questao", "pergunta", "resposta_aluno"]], on="id_questao")
    df.sort_values(["id_questao", "condicao", "repeticao"]).to_csv(
        cfg.FEEDBACKS_PATH, index=False, encoding="utf-8")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condicoes", nargs="+", default=[c for c in cfg.CONDICOES if c != "C0"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg.carregar_env()
    amostra = pd.read_csv(cfg.AMOSTRA_PATH, dtype=str)

    if args.dry_run:
        q = amostra.iloc[0]
        falso = {"referencia": {"resposta_referencia": "<gerada na etapa referencia>"},
                 "conceito_ref": {"conceito_principal": "<gerado>"},
                 "conceito_aluno": {"conceito_principal": "<gerado>"}}
        for etapa in ETAPAS_PREPARO:
            print(f"===== {etapa} | user =====\n{mensagens_preparo(etapa, q, falso)[1]}\n")
        teoria = cfg.CONDICOES[args.condicoes[0]][0]
        system, user = mensagens_feedback(teoria, q, falso)
        print(f"===== feedback {teoria} | system =====\n{system}\n===== feedback | user =====\n{user}")
        return

    registros = carregar_registros()
    prep = {}   # (id_questao, modelo_key) -> {etapa: json}
    feitos = set()
    for g in registros:
        if g["etapa"] == "feedback":
            feitos.add((g["id_questao"], g["condicao"], g["repeticao"]))
        else:
            prep.setdefault((g["id_questao"], g["modelo_key"]), {})[g["etapa"]] = g["json"]

    tarefas = [(q, cond, rep)
               for cond in args.condicoes
               for q in amostra.to_dict("records")
               for rep in range(1, cfg.N_REPETICOES + 1)
               if (q["id_questao"], cond, rep) not in feitos]
    print(f"{len(tarefas)} feedbacks pendentes ({len(feitos)} ja feitos)")

    with open(cfg.GERACOES_PATH, "a", encoding="utf-8") as out:
        for i, (q, cond, rep) in enumerate(tarefas, 1):
            teoria, modelo_key = cfg.CONDICOES[cond]
            p = prep.setdefault((q["id_questao"], modelo_key), {})
            rotulo = f"[{i}/{len(tarefas)}] {q['id_questao']} {cond}"
            try:
                for etapa in ETAPAS_PREPARO:
                    if etapa not in p:
                        system, user = mensagens_preparo(etapa, q, p)
                        reg = executar(out, modelo_key, system, user,
                                       {"id_questao": q["id_questao"], "etapa": etapa})
                        p[etapa] = reg["json"]
                        print(f"{rotulo} {etapa} ok ({reg['tempo_s']}s)")
                system, user = mensagens_feedback(teoria, q, p)
                reg = executar(out, modelo_key, system, user, {
                    "id_questao": q["id_questao"], "etapa": "feedback",
                    "condicao": cond, "teoria": teoria, "repeticao": rep})
            except Exception as e:  # registra e segue; rodar de novo tenta outra vez
                print(f"{rotulo} ERRO: {type(e).__name__}: {e}")
                continue
            v = validar(reg["json"], teoria, q["resposta_aluno"])
            print(f"{rotulo} feedback ok ({reg['tempo_s']}s, {reg['tokens_saida']} tokens, "
                  f"conformidade={v['conformidade']:.2f}, tags={v['n_tags']}, literal={v['trecho_literal']})")

    df = montar_feedbacks_50(amostra, carregar_registros())
    print(f"\n{len(df)} feedbacks -> {cfg.FEEDBACKS_PATH}")
    print(df.groupby("condicao").size().to_string())


if __name__ == "__main__":
    main()
