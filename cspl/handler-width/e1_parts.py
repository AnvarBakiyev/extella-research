"""Opyt 22, area 1: plates, holes, bolts, load. Three ways (A one shot Python, B Python + checks fed back, C own language
with the checks inside the handler on the device via Extella). Writes e1_result.json."""
import json, math, os, re, subprocess, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import TAG, ask_model, save_expert, run_expert, register

# ---- the rules, one text used by the handler on the device and by the local checker (B and the grader) ----
CHECK = '''
import math
CLEAR = {"M3": 3.4, "M4": 4.5, "M5": 5.5, "M6": 6.6}
STD_T = [2, 3, 4, 5, 6, 8, 10, 12]
SIGMA = 80.0
def check_part(plate, holes, spec):
    errs = []
    W, H, T = plate
    if T not in STD_T: errs.append("thickness %s is not a standard sheet; use one of %s" % (T, STD_T))
    if W > spec["max_w"] or H > spec["max_h"]: errs.append("plate %sx%s exceeds the allowed %sx%s" % (W, H, spec["max_w"], spec["max_h"]))
    need_d = CLEAR[spec["bolt"]]
    for i, (x, y, d) in enumerate(holes, 1):
        if abs(d - need_d) > 0.05: errs.append("hole %d diameter %s; %s bolt needs clearance %s" % (i, d, spec["bolt"], need_d))
        m = min(x, y, W - x, H - y)
        if m < 1.5 * d: errs.append("hole %d centre is %.1f mm from the edge; needs at least %.1f (1.5 x d)" % (i, m, 1.5 * d))
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            dist = math.hypot(holes[i][0] - holes[j][0], holes[i][1] - holes[j][1])
            if dist < 2.5 * holes[i][2]: errs.append("holes %d and %d are %.1f mm apart; need at least %.1f (2.5 x d)" % (i + 1, j + 1, dist, 2.5 * holes[i][2]))
    for k, (mx, my) in enumerate(spec["mate"], 1):
        if not any(abs(x - mx) <= 0.1 and abs(y - my) <= 0.1 for x, y, d in holes):
            errs.append("no hole at mating point %d (%s, %s)" % (k, mx, my))
    if len(holes) != len(spec["mate"]): errs.append("%d holes; the mating part has %d" % (len(holes), len(spec["mate"])))
    if T > 0 and W > 0:
        stress = 6.0 * spec["load"] * spec["arm"] / (W * T * T)
        if stress > SIGMA: errs.append("bending stress %.0f MPa exceeds %.0f MPa allowed: make the plate thicker or wider" % (stress, SIGMA))
    return errs
'''
ns = {}; exec(CHECK, ns); check_part = ns["check_part"]

RULES_TEXT = ("Engineering rules: hole diameter must equal the bolt clearance (M3 3.4, M4 4.5, M5 5.5, M6 6.6 mm); "
              "every hole centre at least 1.5 x d from every plate edge; hole centres at least 2.5 x d apart; "
              "plate thickness only from standard sheets 2, 3, 4, 5, 6, 8, 10, 12 mm; one hole exactly at each mating point and no other holes; "
              "bending stress 6 x load x arm / (W x T^2) must not exceed 80 MPa (load in N, arm and sizes in mm); plate within the allowed size.")

TASKS = [
 {"id": "p1", "bolt": "M4", "mate": [[10, 10], [50, 10]], "load": 120, "arm": 60, "max_w": 80, "max_h": 40},
 {"id": "p2", "bolt": "M6", "mate": [[12, 15], [62, 15], [37, 45]], "load": 300, "arm": 90, "max_w": 90, "max_h": 70},
 {"id": "p3", "bolt": "M3", "mate": [[6, 6], [36, 6], [6, 26], [36, 26]], "load": 40, "arm": 30, "max_w": 50, "max_h": 40},
 {"id": "p4", "bolt": "M5", "mate": [[9, 20], [49, 20]], "load": 250, "arm": 120, "max_w": 70, "max_h": 40},
 {"id": "p5", "bolt": "M4", "mate": [[8, 8], [28, 8], [48, 8]], "load": 90, "arm": 45, "max_w": 60, "max_h": 30},
 {"id": "p6", "bolt": "M6", "mate": [[11, 11], [71, 11], [11, 51], [71, 51]], "load": 400, "arm": 100, "max_w": 100, "max_h": 70},
 {"id": "p7", "bolt": "M5", "mate": [[10, 10], [40, 25]], "load": 150, "arm": 80, "max_w": 60, "max_h": 45},
 {"id": "p8", "bolt": "M3", "mate": [[6, 8], [26, 8]], "load": 60, "arm": 50, "max_w": 35, "max_h": 20},
]

def task_text(t):
    pts = ", ".join("(%s, %s)" % tuple(p) for p in t["mate"])
    return ("Design a flat aluminium mounting plate. Coordinates in mm, plate origin at its lower-left corner. "
            "It bolts with %s bolts to a mating part whose holes are at %s. A load of %s N acts at a lever arm of %s mm. "
            "The plate must fit within %s x %s mm." % (t["bolt"], pts, t["load"], t["arm"], t["max_w"], t["max_h"]))

# ---- the own language: three statement kinds ----
LANG = "plate22"
LANG_TEXT = ('Language "plate22", one statement per line: "plate W H T" (width, height, thickness in mm), '
             '"bolt M4" (bolt size), "hole X Y" (hole centre; the diameter comes from the bolt). Numbers may be decimals.')
HANDLER = ('def plate22(code = "", filtered_source_code = "", func_name = "", **extra):\n'
           '    import json, math\n' + "\n".join("    " + l for l in CHECK.strip("\n").splitlines()) + '\n'
           '    spec = extra.get("spec") or (extra.get("kwargs") or {}).get("spec")\n    if isinstance(spec, str): spec = json.loads(spec)\n'
           '    plate, bolt, holes = None, None, []\n'
           '    for n, line in enumerate((code or filtered_source_code or "").splitlines(), 1):\n'
           '        p = line.split()\n'
           '        if not p: continue\n'
           '        try:\n'
           '            if p[0] == "plate" and len(p) == 4: plate = [float(p[1]), float(p[2]), float(p[3])]\n'
           '            elif p[0] == "bolt" and len(p) == 2 and p[1] in CLEAR: bolt = p[1]\n'
           '            elif p[0] == "hole" and len(p) == 3: holes.append([float(p[1]), float(p[2])])\n'
           '            else: return {"status": "rejected", "errors": ["line %d is not a plate22 statement: %s" % (n, line.strip()[:60])]}\n'
           '        except ValueError: return {"status": "rejected", "errors": ["line %d has a number that is not a number" % n]}\n'
           '    if plate is None or bolt is None: return {"status": "rejected", "errors": ["a program needs one plate line and one bolt line"]}\n'
           '    if plate[2] == int(plate[2]): plate[2] = int(plate[2])\n'
           '    full = [[x, y, CLEAR[bolt]] for x, y in holes]\n'
           '    if not spec: return {"status": "success", "plate": plate, "holes": full}\n'
           '    if bolt != spec["bolt"]: return {"status": "rejected", "errors": ["bolt %s; the mating part uses %s" % (bolt, spec["bolt"])]}\n'
           '    errs = check_part(plate, full, spec)\n'
           '    return {"status": "rejected" if errs else "success", "errors": errs, "plate": plate, "holes": full}\n')

def grade(plate, holes, t):
    try: return check_part(plate, holes, t) == []
    except Exception: return False

def run_python(code):
    code = re.sub(r"^```\w*\n|```$", "", code.strip(), flags=re.M)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.py"); open(p, "w").write(code)
        try: r = subprocess.run([sys.executable, "-I", p], capture_output=True, text=True, timeout=10, cwd=d)
        except subprocess.TimeoutExpired: return None, "timeout"
    try:
        j = json.loads(r.stdout.strip().splitlines()[-1])
        return ([float(v) for v in j["plate"]], [[float(v) for v in h] for h in j["holes"]]), None
    except Exception as e:
        return None, (r.stderr.strip()[-300:] or "output is not the JSON asked for: %s" % e)

PY_FORMAT = ('Write a Python program that prints one JSON line: {"plate": [W, H, T], "holes": [[x, y, d], ...]}. '
             'Only the standard library. Reply with the code only.')

def tok(u): return (u or {}).get("total_tokens", 0)

def way_a(t):
    prompt = task_text(t) + " " + RULES_TEXT + " " + PY_FORMAT
    text, sec, u, _ = ask_model(prompt)
    res, err = run_python(text)
    ok = res is not None and grade(res[0], res[1], t)
    return {"ok": ok, "calls": 1, "tokens": tok(u), "chars": len(text), "seconds": sec, "last_error": err}

def way_b(t, tries=3):
    prompt = task_text(t) + " " + RULES_TEXT + " " + PY_FORMAT
    calls = toks = chars = 0; secs = 0.0; ok = False; feedback = ""
    for i in range(tries):
        text, sec, u, _ = ask_model(prompt + feedback)
        calls += 1; toks += tok(u); chars += len(text); secs += sec
        res, err = run_python(text)
        errs = [err] if res is None else check_part(res[0], res[1], t)
        if res is not None and not errs: ok = grade(res[0], res[1], t); break
        feedback = "\n\nYour previous program:\n" + text + "\n\nThe check reported: " + "; ".join(errs) + ". Fix it and reply with the full corrected code only."
    return {"ok": ok, "calls": calls, "tokens": toks, "chars": chars, "seconds": round(secs, 1)}

def way_c(t, tries=3):
    prompt = task_text(t) + " " + LANG_TEXT + " Reply with the program only."
    calls = toks = chars = 0; secs = 0.0; ok = False; feedback = ""; name = "opyt22_" + TAG + t["id"]; runs = []
    for i in range(tries):
        text, sec, u, _ = ask_model(prompt + feedback)
        calls += 1; toks += tok(u); chars += len(text); secs += sec
        text = re.sub(r"^```\w*\n|```$", "", text.strip(), flags=re.M)
        save_expert(name, text, LANG)
        r, rs = run_expert(name, {"spec": json.dumps(t)}); secs += rs; runs.append(rs)
        if isinstance(r, dict) and r.get("status") == "success":
            ok = grade(r["plate"], r["holes"], t); break
        errs = r.get("errors") if isinstance(r, dict) else [str(r)[:300]]
        feedback = "\n\nYour previous program:\n" + text + "\n\nRunning it returned: " + "; ".join(errs or ["unknown error"]) + ". Reply with the full corrected program only."
    return {"ok": ok, "calls": calls, "tokens": toks, "chars": chars, "seconds": round(secs, 1), "device_runs_s": runs}

if __name__ == "__main__":
    out = {"area": "plates", "model_agent": "platform Qwen via agent", "handler_lines": HANDLER.count("\n"), "tasks": {}}
    print("register:", register(LANG, HANDLER))
    for t in TASKS:
        row = {}
        for k, f in (("A", way_a), ("B", way_b), ("C", way_c)):
            try: row[k] = f(t)
            except Exception as e: row[k] = {"ok": False, "crash": str(e)[:200]}
            print(t["id"], k, row[k], flush=True)
        out["tasks"][t["id"]] = row
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "e1_result" + (("_" + TAG) if TAG else "") + ".json"), "w"), indent=1, ensure_ascii=False)
