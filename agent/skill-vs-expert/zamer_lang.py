#!/usr/bin/env python3
"""Третий вариант замера (20.10.2026): программа на языке задачи вместо Python.

Та же задача согласования заказов, тот же эталон на 100 заказах, та же модель через агента
zamer-claude. Отличие от стороны «эксперт» в zamer_claude.py: модель пишет программу не на
Python, а на маленьком языке задачи `zakaz`, грамматика которого даётся в запросе. Программу
исполняет обработчик (функция исполнить ниже), написанный человеком один раз. Считаем токены
на создание программы (все попытки до прохождения эталона) и сравниваем с токенами на создание
Python-функции из results_claude_<метка>.json.

Запуск: python3 zamer_lang.py sonnet|opus   (модель у агента переключается заранее)
"""
import json, re, time, urllib.request, sys, os, operator

МЕТКА = sys.argv[1] if len(sys.argv) > 1 else "sonnet"
АГЕНТ = "<agent id>"
ТОКЕН = open(os.path.expanduser("~/.extella/api_token.txt")).read().strip()
ПАПКА = "<this folder>"
ЗАКАЗЫ = json.load(open(f"{ПАПКА}/dataset.json", encoding="utf-8"))

ПРАВИЛА = """Ты — модуль согласования заказов. На вход приходит заказ в JSON: id, клиент, позиции; у каждой позиции: товар, кол, цена, остаток.
Правила:
1. Сумма заказа = сумма по всем позициям (кол × цена).
2. Если сумма больше 200000 — маршрут "ждать_менеджера", иначе "резерв".
3. Позиция в дефиците, если кол больше остатка. Перечисли товары таких позиций в порядке следования.
Результат — объект {"сумма": <целое число>, "маршрут": "<ждать_менеджера|резерв>", "дефицит": [<товары>]}"""

ГРАММАТИКА = """Язык zakaz. Программа — строки вида `имя = выражение`, по одной на каждое поле результата: сумма, маршрут, дефицит.
Выражение: число, строка в кавычках, имя поля заказа или ранее заданное имя, арифметика + - * /, сравнения > < >= <= == !=, and, or, not, скобки.
Функции:
  sum(список, выражение)            — сумма выражения по элементам списка
  select(список, условие, выражение) — список значений выражения для элементов, где условие истинно, в порядке следования
  if условие then выражение else выражение
Внутри sum и select имена полей относятся к элементу списка (например, кол, цена, остаток, товар).
Других функций и конструкций нет."""

# ---------- Обработчик языка zakaz (написан человеком один раз) ----------
ЛЕКСЕМА = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|("[^"]*")|([A-Za-zА-Яа-яЁё_][\wА-Яа-яЁё]*)|(>=|<=|==|!=|[-+*/()<>,=]))')
БИН = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
       ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le, "==": operator.eq, "!=": operator.ne}
ПРИОРИТЕТ = {"or": 1, "and": 2, "==": 3, "!=": 3, ">": 3, "<": 3, ">=": 3, "<=": 3, "+": 4, "-": 4, "*": 5, "/": 5}

def лексемы(текст):
    out, pos = [], 0
    while pos < len(текст):
        m = ЛЕКСЕМА.match(текст, pos)
        if not m: raise SyntaxError(f"неизвестный символ у позиции {pos}: {текст[pos:pos+10]!r}")
        pos = m.end()
        if m.group(1): out.append(("num", float(m.group(1)) if "." in m.group(1) else int(m.group(1))))
        elif m.group(2): out.append(("str", m.group(2)[1:-1]))
        elif m.group(3): out.append(("id", m.group(3)))
        else: out.append(("op", m.group(4)))
    return out

class Разбор:
    def __init__(self, t): self.t, self.i = t, 0
    def peek(self): return self.t[self.i] if self.i < len(self.t) else (None, None)
    def take(self, *ожид):
        tok = self.peek()
        if ожид and tok[1] not in ожид and tok[0] not in ожид: raise SyntaxError(f"ожидалось {ожид}, встречено {tok}")
        self.i += 1; return tok
    def выражение(self, мин=1):
        левое = self.унарное()
        while True:
            k, v = self.peek()
            op = v if (k == "op" and v in ПРИОРИТЕТ) or (k == "id" and v in ("and", "or")) else None
            if op is None or ПРИОРИТЕТ[op] < мин: return левое
            self.take()
            правое = self.выражение(ПРИОРИТЕТ[op] + 1)
            левое = ("bin", op, левое, правое)
    def унарное(self):
        k, v = self.peek()
        if k == "id" and v == "not": self.take(); return ("not", self.унарное())
        if k == "op" and v == "-": self.take(); return ("neg", self.унарное())
        return self.первичное()
    def первичное(self):
        k, v = self.take()
        if k == "num": return ("const", v)
        if k == "str": return ("const", v)
        if k == "op" and v == "(":
            e = self.выражение(); self.take(")"); return e
        if k == "id":
            if v == "if":
                c = self.выражение(); self.take("then"); a = self.выражение(); self.take("else"); b = self.выражение()
                return ("if", c, a, b)
            if v in ("sum", "select"):
                self.take("("); args = [self.выражение()]
                while self.peek()[1] == ",": self.take(); args.append(self.выражение())
                self.take(")")
                if v == "sum" and len(args) != 2 or v == "select" and len(args) != 3: raise SyntaxError(f"{v}: неверное число аргументов")
                return (v, *args)
            return ("name", v)
        raise SyntaxError(f"неожиданная лексема {(k, v)}")

def вычислить(узел, окружение):
    вид = узел[0]
    if вид == "const": return узел[1]
    if вид == "name":
        for слой in reversed(окружение):
            if узел[1] in слой: return слой[узел[1]]
        raise NameError(f"нет имени {узел[1]}")
    if вид == "neg": return -вычислить(узел[1], окружение)
    if вид == "not": return not вычислить(узел[1], окружение)
    if вид == "bin":
        op = узел[1]
        if op == "and": return вычислить(узел[2], окружение) and вычислить(узел[3], окружение)
        if op == "or": return вычислить(узел[2], окружение) or вычислить(узел[3], окружение)
        return БИН[op](вычислить(узел[2], окружение), вычислить(узел[3], окружение))
    if вид == "if": return вычислить(узел[2], окружение) if вычислить(узел[1], окружение) else вычислить(узел[3], окружение)
    if вид == "sum":
        return sum(вычислить(узел[2], окружение + [эл]) for эл in вычислить(узел[1], окружение))
    if вид == "select":
        return [вычислить(узел[3], окружение + [эл]) for эл in вычислить(узел[1], окружение) if вычислить(узел[2], окружение + [эл])]
    raise ValueError(вид)

def разобрать_программу(текст):
    строки = [с.strip() for с in текст.strip().splitlines() if с.strip() and not с.strip().startswith("#")]
    программа = []
    for с in строки:
        if "=" not in с: raise SyntaxError(f"строка без '=': {с!r}")
        имя, выр = с.split("=", 1)
        имя = имя.strip()
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё_][\wА-Яа-яЁё]*", имя): raise SyntaxError(f"плохое имя {имя!r}")
        p = Разбор(лексемы(выр))
        дерево = p.выражение()
        if p.peek()[0] is not None: raise SyntaxError(f"лишнее в конце строки {с!r}")
        программа.append((имя, дерево))
    return программа

def исполнить(программа, заказ):
    окружение = [dict(заказ)]
    for имя, дерево in программа:
        окружение[0][имя] = вычислить(дерево, окружение)
    res = {k: окружение[0].get(k) for k in ("сумма", "маршрут", "дефицит")}
    if isinstance(res["сумма"], float) and res["сумма"].is_integer(): res["сумма"] = int(res["сумма"])
    return res

# ---------- Самопроверка обработчика на программе, написанной человеком ----------
ОБРАЗЕЦ = '''сумма = sum(позиции, кол * цена)
маршрут = if сумма > 200000 then "ждать_менеджера" else "резерв"
дефицит = select(позиции, кол > остаток, товар)'''

def совпало(ответ, эталон):
    try:
        return (int(ответ.get("сумма")) == эталон["сумма"] and ответ.get("маршрут") == эталон["маршрут"]
                and list(ответ.get("дефицит", [])) == эталон["дефицит"])
    except Exception:
        return False

def заказ_без_эталона(з): return {k: v for k, v in з.items() if k != "эталон"}

def ошибок(программа):
    n = 0; первая = None
    for з in ЗАКАЗЫ:
        try:
            r = исполнить(программа, заказ_без_эталона(з))
            if not совпало(r, з["эталон"]):
                n += 1; первая = первая or (з["id"], r, з["эталон"])
        except Exception as e:
            n += 1; первая = первая or (з["id"], f"ошибка обработчика: {e}", з["эталон"])
    return n, первая

if __name__ == "__main__" and МЕТКА == "selfcheck":
    n, п = ошибок(разобрать_программу(ОБРАЗЕЦ))
    print("самопроверка обработчика: ошибок", n, п); sys.exit(0 if n == 0 else 1)

# ---------- Вызов модели ----------
def вызов(промпт, max_out=800):
    t0 = time.time()
    тело = {"agent_id": АГЕНТ, "input": промпт, "max_output_tokens": max_out, "store": False, "run_timeout": 180}
    req = urllib.request.Request("https://api.extella.ai/api/agent/run", data=json.dumps(тело).encode(),
        headers={"Content-Type": "application/json", "X-Auth-Token": ТОКЕН, "X-Profile-Id": "default", "X-Agent-Id": АГЕНТ})
    for попытка in range(6):
        try:
            r = json.load(urllib.request.urlopen(req, timeout=240)); break
        except urllib.error.HTTPError as e:
            if e.code != 429 or попытка == 5: raise
            пауза = int(e.headers.get("Retry-After") or 0) or 15 * (попытка + 1)
            print(f"  (429, жду {пауза} с)", flush=True); time.sleep(пауза)
    time.sleep(1.5)
    текст = "".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []))
    u = r.get("usage") or {}
    return текст, u.get("input_tokens", 0), u.get("output_tokens", 0), time.time() - t0

if __name__ == "__main__":
    итог = {"модель": МЕТКА, "язык": "zakaz", "попытки": []}
    промпт = (ПРАВИЛА + "\n\n" + ГРАММАТИКА + "\n\nНапиши программу на языке zakaz, реализующую эти правила. Только программу, без пояснений и без markdown.")
    готово = None
    for попытка in range(1, 4):
        текст, вх, вых, сек = вызов(промпт)
        код = re.sub(r"^```\w*\s*|```\s*$", "", текст.strip(), flags=re.M).strip()
        try:
            программа = разобрать_программу(код); n, первая = ошибок(программа)
        except Exception as e:
            n, первая = len(ЗАКАЗЫ), ("разбор", str(e)[:300], None)
        итог["попытки"].append({"попытка": попытка, "вход": вх, "выход": вых, "сек": round(сек, 1), "ошибок_из_100": n, "код": код})
        print(f"  попытка {попытка}: вход {вх}, выход {вых}, {сек:.0f} c, ошибок {n}/100", flush=True)
        if n == 0: готово = код; break
        промпт = (ПРАВИЛА + "\n\n" + ГРАММАТИКА + "\n\nТвоя предыдущая программа:\n" + код + "\n\nОна даёт неверный результат. "
                  f"Пример: заказ {первая[0]} → результат {первая[1]}, ожидалось {первая[2]}. Исправь и верни только программу.")
    итог["программа_прошла_эталон"] = готово is not None
    итог["токены_создания"] = sum(p["вход"] + p["выход"] for p in итог["попытки"])
    итог["строк_в_программе"] = len([с for с in (готово or "").splitlines() if с.strip()])
    итог["строк_в_обработчике"] = sum(1 for с in open(__file__, encoding="utf-8").read().split("# ---------- Обработчик")[1].split("# ---------- Самопроверка")[0].splitlines() if с.strip() and not с.strip().startswith("#"))
    json.dump(итог, open(f"{ПАПКА}/results_lang_{МЕТКА}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n== ИТОГ zakaz:", json.dumps({k: v for k, v in итог.items() if k != "попытки"}, ensure_ascii=False))
