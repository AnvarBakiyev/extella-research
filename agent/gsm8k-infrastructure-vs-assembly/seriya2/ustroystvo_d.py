#!/usr/bin/env python3
"""Вариант D серии 2: устройство v3.3, перенесённое в Extella.

Отличия от ustroystvo33.py (вариант C) только в том, откуда берутся части:
  - 17 фактов читаются из концептов платформы (префикс GSM8K-FACT), выбор по тем же регулярным выражениям;
  - описание языка плана читается из правил агента <agent-id> (префикс GSM8K-PLAN-LANGUAGE);
  - каждый план сохраняется экспертом на языке steps и исполняется обработчиком steps на устройстве через listener;
    законы обработчика (режим plan) — те же проверки, что правила() в v3.3.
Модель та же: Qwen3.5 9B через локальный Ollama, промпты те же.
Тень: тот же план исполняется локальным кодом v3.3 (верхний + правила); расхождение исхода пишется в журнал.

Запуск:  python3 ustroystvo_d.py sample50 vps     # 50 задач из 101–700, seed 20261025, исполнение на VPS
         python3 ustroystvo_d.py sample10 mac     # первые 10 из той же выборки, исполнение на Mac
"""
import json, os, random, re, sys, time
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import ustroystvo33 as C
import ext

ЗДЕСЬ = os.path.dirname(os.path.abspath(__file__))

def загрузить_платформу():
    конц = ext.call("/concept/list", {"limit": 500}).get("results", [])
    факты_пл = []
    for c in конц:
        t = c.get("concept_text", "")
        if t.startswith("GSM8K-FACT | "):
            _, рег, факт = t.split(" | ", 2)
            факты_пл.append((рег, факт.rstrip()))
    порядок = {рег: i for i, (рег, _, _) in enumerate(C.КОНЦЕПТЫ)}
    факты_пл.sort(key=lambda x: порядок.get(x[0], 999))
    правила = [r.get("rule", "") for r in ext.call("/rules/list", {}).get("results", []) if r.get("rule", "").startswith("GSM8K-PLAN-LANGUAGE")]
    язык = правила[0].split("\n", 1)[1] if правила else None
    сверка = {"фактов": len(факты_пл), "факты_равны_C": [(р, ф) for р, ф in факты_пл] == [(р, ф) for р, _, ф in C.КОНЦЕПТЫ],
              "язык_равен_C": (язык or "").rstrip() == C.ЯЗЫК.rstrip()}
    return факты_пл, язык, сверка

class Исполнитель:
    def __init__(self, цель, ид):
        self.цель, self.ид, self.n = цель, ид, 0
    def __call__(self, план, задача, режим, журнал):
        self.n += 1
        имя = f"gsm_s2_{self.ид}_{self.n}"
        t0 = time.time()
        ext.save(имя, план if план.strip() else "# empty", "steps", "GSM8K series 2 plan written by Qwen3.5 9B", {"problem": "", "mode": "plan"})
        try:
            r, _ = ext.run(имя, {"problem": задача, "mode": режим}, self.цель)
        except Exception as e:
            r = {"status": "error", "reason": f"platform: {str(e)[:120]}"}
        dt = time.time() - t0
        if not isinstance(r, dict) or r.get("status") not in ("success", "refused"):
            r = {"status": "error", "reason": str(r)[:200]}
        # тень: тот же план локальным кодом v3.3
        try:
            P, исп, отм = C.верхний(план)
            if режим == "plan": C.правила(задача, P, исп, отм)
            тень = ("success", round(P, 9))
        except C.Отказ as e:
            тень = ("refused", str(e))
        мой = ("success", round(r["answer"], 9)) if r["status"] == "success" else (r["status"], r.get("reason", ""))
        журнал["исполнений"].append({"эксперт": имя, "секунд": round(dt, 2), "D": мой[0], "совпало_с_C": мой == тень})
        if мой != тень:
            журнал["расхождения_с_C"].append({"эксперт": имя, "D": мой, "C": тень})
        if r["status"] == "success": return r["answer"], r.get("used", []), set(r.get("marked", []))
        if r["status"] == "refused": raise C.Отказ(r.get("reason", ""))
        raise RuntimeError(r.get("reason", "platform error"))

def решить(задача, журнал, ФАКТЫ, ЯЗЫК, исполнить):
    фк = [ф for рег, ф in ФАКТЫ if re.search(рег, задача, re.I)]
    подсказка = ("\n\nFacts that may be needed (use only those the problem actually requires): " + "; ".join(фк) + ".") if фк else ""
    журнал["факты"] = фк
    т, вх, вых, _ = C.вызов(задача + подсказка + "\n\nSolve step by step, calculating carefully. Numbers may be written as words (three, twice, half) or be implied (every day of a week). On the last line write only the final answer as a number.", 1500)
    журнал["вызовов"] += 1; журнал["токены"] += вх + вых
    R = C.число_из_текста(т); журнал["R"] = R; журнал["R_текст"] = т
    промпт = задача + подсказка + "\n\n" + ЯЗЫК; последний_принятый = None
    for раунд in range(4):
        т, вх, вых, _ = C.вызов(промпт, 1500); журнал["вызовов"] += 1; журнал["токены"] += вх + вых
        план = re.sub(r"^```\w*|```$", "", т.strip(), flags=re.M).strip()
        try:
            P, исп, отм = исполнить(план, задача, "plan", журнал)
        except C.Отказ as e:
            журнал["события"].append(f"отказ: {str(e)[:160]}")
            промпт = задача + подсказка + "\n\n" + ЯЗЫК + "\n\nYour plan:\n" + план + f"\n\nThe executor refused: {e}. Fix the plan and return it in full."
            continue
        последний_принятый = P; журнал["P"] = P
        if R is not None and abs(P - R) < 1e-6:
            журнал["согласие"] = True; return P
        журнал["события"].append(f"расхождение: план {P}, рассуждение {R}")
        промпт = (задача + подсказка + "\n\n" + ЯЗЫК + "\n\nYour plan:\n" + план + f"\n\nThe executor computed this plan exactly and got {P}. A separate step-by-step solution got {R}. "
                  "They disagree, so at least one of them misreads the problem. Re-read the problem sentence by sentence, decide which quantity the question asks for, and return a corrected plan in full.")
    журнал["согласие"] = False
    подтверждённые = []
    if последний_принятый is not None: подтверждённые.append(round(последний_принятый, 6))
    тексты = [журнал.get("R_текст", "")]
    for k in range(2):
        т2, вх, вых, _ = C.вызов_т(задача + подсказка + "\n\nRead the problem carefully, sentence by sentence. Solve step by step, then check your answer against every sentence. On the last line write only the final answer as a number.", 1500, 0.7, 100 + k)
        журнал["вызовов"] += 1; журнал["токены"] += вх + вых; тексты.append(т2)
    for т2 in тексты:
        if not т2: continue
        r2 = C.число_из_текста(т2)
        if r2 is None: continue
        т3, вх, вых, _ = C.вызов(задача + подсказка + "\n\nHere is a step-by-step solution:\n" + т2[-2500:] + "\n\n" + ЯЗЫК + "\nTranslate exactly this solution into the plan, step by step.", 1500)
        журнал["вызовов"] += 1; журнал["токены"] += вх + вых
        план3 = re.sub(r"^```\w*|```$", "", т3.strip(), flags=re.M).strip()
        try:
            p3, _, _ = исполнить(план3, задача, "translate", журнал)
            if abs(p3 - r2) < 1e-6: подтверждённые.append(round(r2, 6))
        except C.Отказ:
            pass
    журнал["подтверждённые"] = подтверждённые
    if подтверждённые:
        c = Counter(подтверждённые).most_common(); лучшие = [v for v, k in c if k == c[0][1]]
        журнал["решение"] = "арбитр"
        if последний_принятый is not None and round(последний_принятый, 6) in лучшие: return последний_принятый
        return лучшие[0]
    журнал["решение"] = "рассуждение"
    return R

def выборка():
    return sorted(random.Random(20261025).sample(range(101, 701), 50))

if __name__ == "__main__":
    режим, машина = sys.argv[1], sys.argv[2]
    цель = {"vps": ext.VPS, "mac": ext.MAC}[машина]
    номера = выборка()[: (10 if режим == "sample10" else 50)]
    ФАКТЫ, ЯЗЫК, сверка = загрузить_платформу()
    print("сверка платформы:", сверка, flush=True)
    if not (сверка["факты_равны_C"] and сверка["язык_равен_C"]):
        sys.exit("знания на платформе не совпадают с v3.3, прогон не начат")
    строки = open(os.path.join(ЗДЕСЬ, "..", "data", "gsm8k_test.jsonl"), encoding="utf-8").read().splitlines()
    выход = os.path.join(ЗДЕСЬ, f"results_D_{режим}_{машина}.json")
    рез = []
    for k, i in enumerate(номера, 1):
        d = json.loads(строки[i - 1]); ид = f"test{i}"
        эталон = float(d["answer"].split("####")[-1].strip().replace(",", ""))
        ж = {"id": ид, "вызовов": 0, "токены": 0, "события": [], "согласие": None, "R": None, "P": None, "исполнений": [], "расхождения_с_C": []}
        t0 = time.time()
        ответ = решить(d["question"], ж, ФАКТЫ, ЯЗЫК, Исполнитель(цель, f"{машина}_{i}"))
        ж["секунд"] = round(time.time() - t0, 1)
        ж.pop("R_текст", None); ж["ответ"] = ответ; ж["эталон"] = эталон; ж["верно"] = ответ is not None and abs(ответ - эталон) < 1e-6
        ж["R_верно"] = ж["R"] is not None and abs(ж["R"] - эталон) < 1e-6
        рез.append(ж)
        print(k, ид, "верно" if ж["верно"] else "НЕВЕРНО", "| исполнений", len(ж["исполнений"]), "| расхождений с C", len(ж["расхождения_с_C"]), "|", ж["секунд"], "с", flush=True)
        json.dump(рез, open(выход, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    исп = [e for x in рез for e in x["исполнений"]]
    print("ИТОГ", режим, машина, "| задач", len(рез), "| верных", sum(x["верно"] for x in рез), "| согласие", sum(bool(x["согласие"]) for x in рез),
          "| исполнений на устройстве", len(исп), "| расхождений исполнителя с C", sum(len(x["расхождения_с_C"]) for x in рез),
          "| медиана исполнения, с", sorted(e["секунд"] for e in исп)[len(исп) // 2] if исп else None)
