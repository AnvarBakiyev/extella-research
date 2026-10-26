"""steps: plan language of the GSM8K series (port of the executor of ustroystvo33.py v3.3, logic unchanged).

A program is a plan: lines  name = expression  or  name [unit] = expression,  comment lines '# unused N: reason',
last line  answer = ... . The upper part parses lines, the lower part executes each operation with checks
(names defined, division by zero, units in + and -). Laws of the handler (mode "plan") check the answer
against the problem text: finite, whole and non-negative for 'how many', non-negative, every number of the
problem used or marked unused. Mode "translate" executes only, without the laws (used by the arbiter).

Run parameters: problem (text), mode ("plan" | "translate").
Returns {"status": "success", "answer": float, "used": [...], "marked": [...]}
     or {"status": "refused", "reason": "..."}.
"""
import ast, json, math, re

class Refusal(Exception):
    pass

def lower(op, a, b=None, where=""):
    (va, ua) = a; (vb, ub) = b if b is not None else (None, None)
    if op in ("+", "-"):
        if ua and ub and ua != ub:
            raise Refusal(f"{where}: cannot {'add' if op=='+' else 'subtract'} {ub} {'to' if op=='+' else 'from'} {ua}; convert to the same unit first")
        return (va + vb if op == "+" else va - vb, ua or ub)
    if op == "*": return (va * vb, ua or ub if not (ua and ub) else "")
    if op == "/":
        if vb == 0: raise Refusal(f"{where}: division by zero")
        return (va / vb, "" if (ua and ub and ua == ub) else (ua or ""))
    if op == "**":
        if abs(vb) > 64: raise Refusal(f"{where}: exponent too large")
        return (va ** vb, ua)
    if op in ("//", "%"):
        if vb == 0: raise Refusal(f"{where}: division by zero")
        return (va // vb if op == "//" else va % vb, ua)
    raise Refusal(f"{where}: unknown operation {op}")

FUNCS = {"max": max, "min": min, "round": lambda x, n=0: round(x, int(n)) if n else math.floor(x + 0.5), "floor": math.floor, "ceil": math.ceil, "abs": abs, "sqrt": math.sqrt, "log": math.log, "sum": lambda *a: sum(a)}
OPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Pow: "**", ast.FloorDiv: "//", ast.Mod: "%"}
CMP = {ast.Gt: lambda a, b: a > b, ast.Lt: lambda a, b: a < b, ast.GtE: lambda a, b: a >= b, ast.LtE: lambda a, b: a <= b, ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b}

def evaluate(n, names, where):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool): return (n.value, "")
    if isinstance(n, ast.Name):
        if n.id not in names: raise Refusal(f"{where}: name '{n.id}' is not defined above")
        return names[n.id]
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
        v, u = evaluate(n.operand, names, where); return (-v, u)
    if isinstance(n, ast.BinOp) and type(n.op) in OPS:
        return lower(OPS[type(n.op)], evaluate(n.left, names, where), evaluate(n.right, names, where), where)
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS:
        args = [evaluate(x, names, where) for x in n.args]
        if not args: raise Refusal(f"{where}: {n.func.id}() needs arguments")
        v = FUNCS[n.func.id](*[a[0] for a in args]); return (v, args[0][1])
    if isinstance(n, ast.Compare) and len(n.ops) == 1 and type(n.ops[0]) in CMP:
        return (1 if CMP[type(n.ops[0])](evaluate(n.left, names, where)[0], evaluate(n.comparators[0], names, where)[0]) else 0, "")
    if isinstance(n, ast.IfExp):
        c = n.test
        if isinstance(c, ast.Compare) and len(c.ops) == 1 and type(c.ops[0]) in CMP:
            ok = CMP[type(c.ops[0])](evaluate(c.left, names, where)[0], evaluate(c.comparators[0], names, where)[0])
            return evaluate(n.body if ok else n.orelse, names, where)
        raise Refusal(f"{where}: the condition must be one comparison like a > b")
    raise Refusal(f"{where}: allowed are numbers, names, + - * / ** // %, parentheses, max min round floor ceil abs sqrt log sum, comparisons, and 'x if a > b else y'. There are no unknowns, loops or equations: compute each value directly from known ones")

LINE = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\[\s*([^\]]+?)\s*\])?\s*=\s*(.+?)\s*$")

def upper(plan):
    names = {}; marked = set(); used = []
    for k, s in enumerate([s for s in plan.strip().splitlines() if s.strip()], 1):
        s = s.strip()
        if re.match(r"#?\s*unused", s, re.I) or (s.startswith("#") and "unused" in s.lower()):
            for x in re.findall(r"\d[\d,]*(?:\.\d+)?", s.split(":")[0]): marked.add(float(x.replace(",", "")))
            continue
        if s.startswith("#"): continue
        s = s.split("#")[0].replace("×", "*").replace("−", "-").replace("÷", "/").replace("$", "")
        m = LINE.match(s)
        if not m: raise Refusal(f"line {k} '{s}': use the form name = expression  or  name [unit] = expression")
        name, unit, expr = m.group(1), (m.group(2) or "").strip().lower().rstrip("s"), m.group(3)
        if "/" in unit or " per " in unit: unit = ""
        expr = re.sub(r"\s*\[[^\]]*\]\s*$", "", expr)
        expr = re.sub(r"(?<=\d),(?=\d{3}\b)", "", expr)
        expr = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"(\1/100)", expr)
        for x in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", expr): used.append(float(x))
        try: tree = ast.parse(expr, mode="eval").body
        except SyntaxError: raise Refusal(f"line {k} '{s.strip()}': cannot parse the expression")
        v, u = evaluate(tree, names, f"line {k} '{s.strip()}'")
        names[name] = (v, unit or u)
    if "answer" not in names: raise Refusal("no line 'answer = ...'")
    return names["answer"][0], used, marked

HOW_MANY = re.compile(r"\bhow many\b", re.I)
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
                "twice": 2, "double": 2, "triple": 3, "half": 0.5, "third": 3, "quarter": 4}

def words_numbers(text):
    return [NUMBER_WORDS[w] for w in re.findall(r"[A-Za-z]+", text.lower()) if w in NUMBER_WORDS]

def problem_numbers(text):
    out = []
    for x in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", text):
        try: out.append(float(x.replace(",", "")))
        except ValueError: pass
    return out

def laws(problem, res, used, marked):
    if not math.isfinite(res): raise Refusal("the answer is not a finite number")
    question = problem.split("?")[-2] if "?" in problem else problem
    if HOW_MANY.search(question) and (res < 0 or abs(res - round(res)) > 1e-9):
        raise Refusal(f"the question asks 'how many', so the answer must be a whole non-negative number, but the plan gives {res}")
    if res < 0: raise Refusal(f"the answer {res} is negative; check the plan")
    used_set = set(used)
    missing = [x for x in problem_numbers(problem) if x not in used_set and x not in marked]
    for x in set(words_numbers(problem)):
        if x not in used_set and x not in marked and not (x == 0.5 and 2.0 in used_set) and not (x in (3, 4) and x in used_set):
            if x in (2, 3, 4) and (1/x) in used_set: continue
            missing.append(float(x))
    if missing:
        p = ", ".join(str(int(x)) if x == int(x) else str(x) for x in sorted(set(missing)))
        raise Refusal(f"these numbers from the problem are not used in the plan: {p}. Use each one, or add a line '# unused N: reason' if it is really not needed")

def run_plan(plan, problem="", mode="plan"):
    try:
        answer, used, marked = upper(plan)
        if mode == "plan":
            laws(problem, answer, used, marked)
        return {"status": "success", "answer": answer, "used": used, "marked": sorted(marked)}
    except Refusal as e:
        return {"status": "refused", "reason": str(e)}

HANDLER_VERSION = "steps 1 (port of v3.3)"

def steps(code="", filtered_source_code="", func_name="", **extra):
    import platform, socket
    source = code or filtered_source_code or ""
    params = dict(extra)
    inner = extra.get("kwargs")
    if isinstance(inner, dict):
        params.update(inner)
    out = run_plan(source, str(params.get("problem") or ""), str(params.get("mode") or "plan"))
    out.update({"language": "steps", "expert": func_name, "handler_version": HANDLER_VERSION, "model_calls": 0,
                "host": socket.gethostname(), "os": platform.system()})
    return out
