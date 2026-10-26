"""rulebook: правила скидок таблицей; обработчик переводит их в план steps и отдаёт его обработчику steps.
  rate when <усл> [and <усл>]: <процент>     (усл: поле  или  поле >= N / > N / <= N / < N)
  take: max | sum                              (как сочетать ставки rate, по умолчанию max)
  extra when <усл>: <процент>                  (добавка сверху)
Выход: для каждой строки поле rate. Логика steps здесь не копируется: исполнение плана делает steps."""
import re
COND = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:(>=|<=|>|<)\s*(\d+(?:\.\d+)?))?\s*$")

def translate(src):
    lines, rates, extras, take = [], [], [], "max"
    for n, raw in enumerate([l.strip() for l in src.splitlines() if l.strip() and not l.strip().startswith("#")], 1):
        m = re.match(r"^take\s*:\s*(max|sum)$", raw)
        if m: take = m.group(1); continue
        m = re.match(r"^(rate|extra)\s+when\s+(.+?)\s*:\s*(\d+(?:\.\d+)?)\s*%?$", raw)
        if not m: raise ValueError(f"line {n}: expected 'rate when <condition>: <percent>' or 'extra when ...' or 'take: max|sum'")
        kind, conds, val = m.group(1), [c for c in re.split(r"\s+and\s+", m.group(2))], m.group(3)
        inds = []
        for j, c in enumerate(conds, 1):
            cm = COND.match(c)
            if not cm: raise ValueError(f"line {n}: cannot read condition '{c}'")
            name = f"c{n}_{j}"
            lines.append(f"{name} = 1 if {cm.group(1)} {cm.group(2)} {cm.group(3)} else 0" if cm.group(2) else f"{name} = 1 if {cm.group(1)} > 0 else 0")
            inds.append(name)
        v = f"r{n}"; lines.append(f"{v} = {val} * " + " * ".join(inds))
        (rates if kind == "rate" else extras).append(v)
    if not rates and not extras: raise ValueError("no rules")
    base = (rates[0] if len(rates) == 1 else "max(" + ", ".join(rates) + ")" if take == "max" else " + ".join(rates)) if rates else "0"
    lines.append("rate = " + base + "".join(" + " + e for e in extras))
    return "\n".join(lines)

def run(src, rows, call_steps):
    """call_steps(plan, rows, outputs) -> ответ steps в режиме map. Способ вызова задаёт сторона."""
    try: plan = translate(src)
    except ValueError as e: return {"status": "refused", "reason": str(e)}
    r = call_steps(plan, rows, ["rate"])
    if r.get("status") != "success": return {"status": r.get("status", "error"), "reason": "steps: " + str(r.get("reason"))}
    return {"status": "success", "rows": r["rows"], "plan": plan}
