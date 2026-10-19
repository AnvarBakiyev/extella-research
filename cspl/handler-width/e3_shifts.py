"""Opyt 22, area 3: shift schedules under labour rules. Same three ways as area 1. Writes e3_result.json."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TAG, ask_model, save_expert, run_expert, register
from e1_parts import run_python as _unused, tok

CHECK = '''
def mins(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)
def check_shifts(shifts, spec):
    errs = []
    people = spec["people"]
    spans = []
    for i, (who, day, start, end) in enumerate(shifts, 1):
        if who not in people: errs.append("shift %d: %s is not on the roster %s" % (i, who, people)); continue
        if day < 1 or day > 7: errs.append("shift %d: day %s is not 1..7" % (i, day)); continue
        a = (day - 1) * 1440 + mins(start)
        b = (day - 1) * 1440 + mins(end)
        if b <= a: b += 1440
        length = (b - a) / 60.0
        if length < 4 or length > 12: errs.append("shift %d (%s day %s): %.1f h; a shift must be 4 to 12 hours" % (i, who, day, length))
        spans.append((who, a, b, i))
    for who in people:
        own = sorted(s for s in spans if s[0] == who)
        total = sum(b - a for _, a, b, _ in own) / 60.0
        if total > spec["max_week"]: errs.append("%s works %.1f h in the week; the limit is %s h" % (who, total, spec["max_week"]))
        for (w1, a1, b1, i1), (w2, a2, b2, i2) in zip(own, own[1:]):
            if a2 < b1: errs.append("%s: shifts %d and %d overlap" % (who, i1, i2))
            elif (a2 - b1) / 60.0 < 11: errs.append("%s: only %.1f h rest between shifts %d and %d; at least 11 h required" % (who, (a2 - b1) / 60.0, i1, i2))
    for day, start, end, need in spec["cover"]:
        a = (day - 1) * 1440 + mins(start)
        b = (day - 1) * 1440 + mins(end)
        if b <= a: b += 1440
        # the number on duty changes only at shift edges, so checking the window start and every edge inside it is exact
        points = sorted(set([a] + [x for _, x, y, _ in spans if a < x < b] + [y for _, x, y, _ in spans if a < y < b]))
        for t in points:
            on = len(set(w for w, x, y, _ in spans if x <= t < y))
            if on < need:
                errs.append("day %s at %02d:%02d only %d on duty; %d needed" % (day, (t % 1440) // 60, t % 60, on, need)); break
    return errs
'''
ns = {}; exec(CHECK, ns); check_shifts = ns["check_shifts"]

RULES_TEXT = ("Labour rules: every shift is 4 to 12 hours long; at least 11 hours of rest between two shifts of the same person; "
              "no person works more than the weekly limit; only people on the roster; days are numbered 1 (Monday) to 7 (Sunday); "
              "a shift may end after midnight; at every moment of each coverage window at least the required number of people are on duty.")

TASKS = [
 {"id": "s1", "people": ["Ana", "Bek", "Cara"], "max_week": 40, "cover": [[d, "08:00", "20:00", 1] for d in range(1, 8)]},
 {"id": "s2", "people": ["Ana", "Bek", "Cara", "Dana"], "max_week": 40, "cover": [[d, "09:00", "21:00", 2] for d in range(1, 6)]},
 {"id": "s3", "people": ["Ana", "Bek", "Cara", "Dana", "Erik"], "max_week": 40, "cover": [[d, "07:00", "23:00", 1] for d in range(1, 8)]},
 {"id": "s4", "people": ["Ana", "Bek", "Cara", "Dana"], "max_week": 36, "cover": [[d, "10:00", "22:00", 1] for d in range(1, 8)] + [[6, "12:00", "20:00", 2], [7, "12:00", "20:00", 2]]},
 {"id": "s5", "people": ["Ana", "Bek", "Cara", "Dana", "Erik", "Fara"], "max_week": 40, "cover": [[d, "22:00", "06:00", 1] for d in range(1, 8)] + [[d, "06:00", "22:00", 1] for d in range(1, 8)]},
 {"id": "s6", "people": ["Ana", "Bek", "Cara"], "max_week": 30, "cover": [[d, "09:00", "17:00", 1] for d in range(1, 6)] + [[3, "09:00", "13:00", 2]]},
]

def task_text(t):
    cov = "; ".join("day %s %s-%s at least %s" % tuple(c) for c in t["cover"])
    return ("Make a one-week shift schedule. Roster: %s. Weekly limit per person: %s hours. Coverage needed: %s."
            % (", ".join(t["people"]), t["max_week"], cov))

LANG = "shift22"
LANG_TEXT = ('Language "shift22", one line per shift: "shift NAME DAY HH:MM HH:MM" (person, day 1-7, start, end; end may be after midnight).')
HANDLER = ('def shift22(code = "", filtered_source_code = "", func_name = "", **extra):\n'
           '    import json\n' + "\n".join("    " + l for l in CHECK.strip("\n").splitlines()) + '\n'
           '    spec = extra.get("spec") or (extra.get("kwargs") or {}).get("spec")\n'
           '    if isinstance(spec, str): spec = json.loads(spec)\n'
           '    shifts = []\n'
           '    for n, line in enumerate((code or filtered_source_code or "").splitlines(), 1):\n'
           '        p = line.split()\n'
           '        if not p: continue\n'
           '        ok = len(p) == 5 and p[0] == "shift" and p[2].isdigit() and ":" in p[3] and ":" in p[4]\n'
           '        if ok:\n'
           '            try: mins(p[3]); mins(p[4])\n'
           '            except Exception: ok = False\n'
           '        if not ok: return {"status": "rejected", "errors": ["line %d is not a shift22 statement: %s" % (n, line.strip()[:60])]}\n'
           '        shifts.append([p[1], int(p[2]), p[3], p[4]])\n'
           '    if not spec: return {"status": "success", "shifts": shifts}\n'
           '    errs = check_shifts(shifts, spec)\n'
           '    return {"status": "rejected" if errs else "success", "errors": errs[:12], "shifts": shifts}\n')

PY_FORMAT = ('Write a Python program that prints one JSON line: {"shifts": [["NAME", DAY, "HH:MM", "HH:MM"], ...]}. '
             'Only the standard library. Reply with the code only.')

import subprocess, tempfile
def run_python(code):
    code = re.sub(r"^```\w*\n|```$", "", code.strip(), flags=re.M)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.py"); open(p, "w").write(code)
        try: r = subprocess.run([sys.executable, "-I", p], capture_output=True, text=True, timeout=20, cwd=d)
        except subprocess.TimeoutExpired: return None, "timeout"
    try:
        j = json.loads(r.stdout.strip().splitlines()[-1])
        return [[s[0], int(s[1]), s[2], s[3]] for s in j["shifts"]], None
    except Exception as e:
        return None, (r.stderr.strip()[-300:] or "output is not the JSON asked for: %s" % e)

def grade(shifts, t):
    try: return check_shifts(shifts, t) == []
    except Exception: return False

def way_a(t):
    text, sec, u, _ = ask_model(task_text(t) + " " + RULES_TEXT + " " + PY_FORMAT)
    res, err = run_python(text)
    return {"ok": res is not None and grade(res, t), "calls": 1, "tokens": tok(u), "chars": len(text), "seconds": sec,
            "errors": (check_shifts(res, t)[:3] if res is not None else [err])}

def way_b(t, tries=3):
    prompt = task_text(t) + " " + RULES_TEXT + " " + PY_FORMAT
    calls = toks = chars = 0; secs = 0.0; ok = False; feedback = ""; last = []
    for i in range(tries):
        text, sec, u, _ = ask_model(prompt + feedback)
        calls += 1; toks += tok(u); chars += len(text); secs += sec
        res, err = run_python(text)
        errs = [err] if res is None else check_shifts(res, t)
        last = errs[:3]
        if res is not None and not errs: ok = True; break
        feedback = "\n\nYour previous program:\n" + text + "\n\nThe check reported: " + "; ".join(errs[:12]) + ". Fix it and reply with the full corrected program only."
    return {"ok": ok, "calls": calls, "tokens": toks, "chars": chars, "seconds": round(secs, 1), "errors": last}

def way_c(t, tries=3):
    prompt = task_text(t) + " " + RULES_TEXT + " " + LANG_TEXT + " Reply with the program only."
    calls = toks = chars = 0; secs = 0.0; ok = False; feedback = ""; name = "opyt22_" + TAG + t["id"]; last = []
    for i in range(tries):
        text, sec, u, _ = ask_model(prompt + feedback)
        calls += 1; toks += tok(u); chars += len(text); secs += sec
        text = re.sub(r"^```\w*\n|```$", "", text.strip(), flags=re.M)
        save_expert(name, text, LANG)
        r, rs = run_expert(name, {"spec": json.dumps(t)}); secs += rs
        if isinstance(r, dict) and r.get("status") == "success":
            ok = grade(r["shifts"], t); break
        errs = r.get("errors") if isinstance(r, dict) else [str(r)[:300]]
        last = (errs or [])[:3]
        feedback = "\n\nYour previous program:\n" + text + "\n\nThe check reported: " + "; ".join(errs or ["unknown error"]) + ". Fix it and reply with the full corrected program only."
    return {"ok": ok, "calls": calls, "tokens": toks, "chars": chars, "seconds": round(secs, 1), "errors": last}

if __name__ == "__main__":
    out = {"area": "shifts", "handler_lines": HANDLER.count("\n"), "tasks": {}}
    print("register:", register(LANG, HANDLER))
    for t in TASKS:
        row = {}
        for k, f in (("A", way_a), ("B", way_b), ("C", way_c)):
            try: row[k] = f(t)
            except Exception as e: row[k] = {"ok": False, "crash": str(e)[:200]}
            print(t["id"], k, row[k], flush=True)
        out["tasks"][t["id"]] = row
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e3v2_result" + (("_" + TAG) if TAG else "") + ".json"), "w"), indent=1, ensure_ascii=False)
