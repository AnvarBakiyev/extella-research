#!/usr/bin/env python3
"""Точность как проверяемость (20.10.2026): порченые программы на Python и на языке задачи.

Берём правильные программы с 12 правилами, написанные одной моделью (results_long_<модель>_12.json),
и портим каждую одинаковыми операторами по одному месту за раз:
  DEL — убрать одну строку;  CMP — перевернуть одно сравнение;  NUM — изменить одну числовую константу;
  STR — подменить одну строковую константу другой из программы;  ID — подменить одно имя другим именем программы.
Для каждой порченой версии смотрим, кто её ловит:
  статика — до запуска: у zakaz2 проверка обработчика (разбор, все поля заданы, имена определены,
            типы полей, значения строковых полей из закрытого списка); у Python — компиляция и pyflakes
            (синтаксис, неопределённые имена); проверки типов у Python нет, об этом сказано в отчёте;
  тест    — прогон на 100 заказах против эталона (для Python ловит и исключения);
  тихо    — не поймал никто (поведение не изменилось или изменилось вне 100 заказов).
Запуск: python3 zamer_mutacii.py sonnet|opus
"""
import json, re, sys, io, copy

МЕТКА = sys.argv[1] if len(sys.argv) > 1 else "sonnet"
ПАПКА = "<this folder>"

# обработчик zakaz2, эталон и заказы — из zamer_long.py при 12 правилах, без запуска модели
sys.argv = ["zamer_long.py", "x", "12"]
_src = open(f"{ПАПКА}/zamer_long.py", encoding="utf-8").read().split('if МЕТКА == "selfcheck"')[0]
_метка = МЕТКА
exec(_src, globals())
МЕТКА = _метка

ТИПЫ_ПОЛЕЙ = {"сумма": "num", "скидка": "num", "сумма_со_скидкой": "num", "маршрут": "str", "дефицит": "list", "частичная": "bool",
              "доставка_стоимость": "num", "позиций": "num", "крупный": "bool", "макс_позиция": "num", "приоритет": "str",
              "итого": "num", "предоплата": "num"}
ЗАКРЫТЫЕ = {"маршрут": {"ждать_менеджера", "резерв", "проверка"}, "приоритет": {"высокий", "средний", "обычный"}}
ПОЛЯ_ЗАКАЗА = {"id": "str", "клиент": "str", "доставка": "str", "позиции": "list"}
ПОЛЯ_ЭЛЕМЕНТА = {"товар": "str", "кол": "num", "цена": "num", "остаток": "num"}

# ---------- Статическая проверка zakaz2: имена, типы, закрытые списки ----------
class Отказ(Exception): pass

def тип(узел, окр):
    в = узел[0]
    if в == "const":
        x = узел[1]; return "bool" if isinstance(x, bool) else "num" if isinstance(x, (int, float)) else "str"
    if в == "list":
        for e in узел[1]: тип(e, окр)
        return "list"
    if в == "name":
        for слой in reversed(окр):
            if узел[1] in слой: return слой[узел[1]]
        raise Отказ(f"неизвестное имя {узел[1]}")
    if в == "neg":
        if тип(узел[1], окр) != "num": raise Отказ("минус не от числа")
        return "num"
    if в == "not":
        if тип(узел[1], окр) != "bool": raise Отказ("not не от условия")
        return "bool"
    if в == "bin":
        op, a, b = узел[1], тип(узел[2], окр), тип(узел[3], окр)
        if op in ("+", "-", "*", "/"):
            if a != "num" or b != "num": raise Отказ(f"арифметика над {a} и {b}")
            return "num"
        if op in (">", "<", ">=", "<="):
            if a != "num" or b != "num": raise Отказ(f"сравнение {op} над {a} и {b}")
            return "bool"
        if op in ("==", "!="):
            if a != b: raise Отказ(f"равенство между {a} и {b}")
            return "bool"
        if op in ("and", "or"):
            if a != "bool" or b != "bool": raise Отказ(f"{op} над {a} и {b}")
            return "bool"
        if op == "in":
            if b != "list": raise Отказ("in не над списком")
            return "bool"
    if в == "if":
        if тип(узел[1], окр) != "bool": raise Отказ("условие if не условие")
        a, b = тип(узел[2], окр), тип(узел[3], окр)
        if a != b: raise Отказ(f"ветви if разных типов: {a} и {b}")
        return a
    if в in ("sum", "max", "any", "select", "count"):
        if тип(узел[1], окр) != "list": raise Отказ(f"{в} не над списком")
        внутр = окр + [dict(ПОЛЯ_ЭЛЕМЕНТА)]
        if в == "count": return "num"
        if в in ("sum", "max"):
            if тип(узел[2], внутр) != "num": raise Отказ(f"{в} не числа")
            return "num"
        if в == "any":
            if тип(узел[2], внутр) != "bool": raise Отказ("any не условия")
            return "bool"
        if тип(узел[2], внутр) != "bool": raise Отказ("select: условие не условие")
        тип(узел[3], внутр); return "list"
    if в == "round":
        if тип(узел[1], окр) != "num": raise Отказ("round не от числа")
        return "num"
    raise Отказ(f"узел {в}")

def строки_в(узел):
    в = узел[0]
    if в == "const": return {узел[1]} if isinstance(узел[1], str) else set()
    if в == "if": return строки_в(узел[2]) | строки_в(узел[3])
    if в == "name": return set()
    out = set()
    for ч in узел[1:]:
        if isinstance(ч, tuple): out |= строки_в(ч)
    return out

def статика_zakaz(код):
    """Возвращает None, если проверка прошла, иначе текст отказа."""
    try:
        программа = разобрать_программу(код)
    except Exception as e:
        return f"разбор: {e}"
    окр = [dict(ПОЛЯ_ЗАКАЗА)]
    try:
        for имя, дерево in программа:
            t = тип(дерево, окр)
            if имя in ТИПЫ_ПОЛЕЙ and t != ТИПЫ_ПОЛЕЙ[имя]: raise Отказ(f"поле {имя} типа {t}, ожидался {ТИПЫ_ПОЛЕЙ[имя]}")
            if имя in ЗАКРЫТЫЕ and not строки_в(дерево) <= ЗАКРЫТЫЕ[имя]: raise Отказ(f"поле {имя}: значение вне списка {строки_в(дерево) - ЗАКРЫТЫЕ[имя]}")
            окр[0][имя] = t
    except Отказ as e:
        return str(e)
    не_заданы = [п for п in ТИПЫ_ПОЛЕЙ if п not in окр[0]]
    if не_заданы: return f"не заданы поля {не_заданы}"
    return None

# ---------- Статическая проверка Python: компиляция и pyflakes ----------
def статика_python(код):
    try:
        compile(код, "<mutant>", "exec")
    except SyntaxError as e:
        return f"синтаксис: {e.msg}"
    from pyflakes.api import check
    from pyflakes.reporter import Reporter
    out = io.StringIO()
    check(код, "<mutant>", Reporter(out, out))
    ошибки = [с for с in out.getvalue().splitlines() if "undefined name" in с or "invalid syntax" in с]
    return "pyflakes: " + ошибки[0] if ошибки else None

# ---------- Динамическая проверка: 100 заказов ----------
def тест_zakaz(код):
    try:
        n, _ = ошибок_zakaz(разобрать_программу(код)); return n
    except Exception:
        return len(ЗАКАЗЫ)

def тест_python(код):
    n, _ = ошибок_python(код); return n

# ---------- Операторы порчи (одинаковые для обоих языков) ----------
СРАВНЕНИЯ = {">=": "<=", "<=": ">=", "==": "!=", "!=": "==", ">": "<", "<": ">"}
ЧИСЛО = re.compile(r'(?<![\w."])(\d+(?:\.\d+)?)(?![\w"])')
СТРОКА = re.compile(r'"([^"]*)"')
ИМЯ = re.compile(r"[A-Za-zА-Яа-яЁё_][\wА-Яа-яЁё]*")

def мутанты(код, служебные):
    out = []
    строки = код.split("\n")
    # DEL: убрать одну непустую строку
    for i, с in enumerate(строки):
        if с.strip() and not с.strip().startswith("#") and not с.strip().startswith("def "):
            out.append(("DEL", i, "\n".join(строки[:i] + строки[i + 1:])))
    # CMP: перевернуть одно сравнение (без = в присваивании)
    for m in re.finditer(r">=|<=|==|!=|(?<![<>=!])>(?!=)|(?<![<>=!])<(?!=)", код):
        op = m.group(0)
        out.append(("CMP", m.start(), код[:m.start()] + СРАВНЕНИЯ[op] + код[m.end():]))
    # NUM: изменить одну константу
    for m in ЧИСЛО.finditer(код):
        x = m.group(1); новое = "1" if x == "0" else (str(float(x) * 10) if "." in x else str(int(x) * 10))
        out.append(("NUM", m.start(), код[:m.start()] + новое + код[m.end():]))
    # STR: подменить одну строку другой из программы
    все_строки = []
    for m in СТРОКА.finditer(код):
        if m.group(1) not in все_строки: все_строки.append(m.group(1))
    for m in СТРОКА.finditer(код):
        другие = [s for s in все_строки if s != m.group(1)]
        if другие:
            out.append(("STR", m.start(), код[:m.start()] + '"' + другие[0] + '"' + код[m.end():]))
    # ID: подменить одно имя другим именем программы
    имена = []
    for m in ИМЯ.finditer(код):
        w = m.group(0)
        if w not in служебные and not w.isdigit() and w not in имена: имена.append(w)
    for m in ИМЯ.finditer(код):
        w = m.group(0)
        if w in имена and код[m.end():m.end() + 1] != '"' and код[m.start() - 1:m.start()] != '"':
            другое = имена[(имена.index(w) + 1) % len(имена)]
            out.append(("ID", m.start(), код[:m.start()] + другое + код[m.end():]))
    return out

СЛУЖЕБНЫЕ_Z = {"if", "then", "else", "and", "or", "not", "in", "true", "false", "sum", "max", "count", "any", "select", "round"}
СЛУЖЕБНЫЕ_P = {"def", "return", "if", "elif", "else", "for", "in", "and", "or", "not", "dict", "int", "round", "sum", "max", "len",
               "get", "True", "False", "None", "list", "str", "float", "bool", "any", "all", "append"}

def оценить(вариант, код, статика, тест, служебные):
    итог = {"всего": 0, "статика": 0, "тест": 0, "тихо": 0, "по_операторам": {}, "примеры_тихих": []}
    for оп, поз, м in мутанты(код, служебные):
        if м.strip() == код.strip(): continue
        итог["всего"] += 1
        о = итог["по_операторам"].setdefault(оп, {"всего": 0, "статика": 0, "тест": 0, "тихо": 0})
        о["всего"] += 1
        причина = статика(м)
        if причина is not None:
            итог["статика"] += 1; о["статика"] += 1; continue
        n = тест(м)
        if n > 0:
            итог["тест"] += 1; о["тест"] += 1
        else:
            итог["тихо"] += 1; о["тихо"] += 1
            if len(итог["примеры_тихих"]) < 8:
                diff = next((f"{a!r} -> {b!r}" for a, b in zip(код.split("\n"), м.split("\n")) if a != b), f"строка {поз}")
                итог["примеры_тихих"].append(f"{оп}: {diff[:160]}")
    return итог

if __name__ == "__main__":
    d = json.load(open(f"{ПАПКА}/results_long_{МЕТКА}_12.json", encoding="utf-8"))
    код_z = d["zakaz2"]["попытки"][-1]["код"]; код_p = d["python"]["попытки"][-1]["код"]
    assert статика_zakaz(код_z) is None and тест_zakaz(код_z) == 0, "исходная программа zakaz2 должна проходить всё"
    assert статика_python(код_p) is None and тест_python(код_p) == 0, "исходная функция Python должна проходить всё"
    итог = {"модель": МЕТКА, "правил": 12,
            "zakaz2": оценить("zakaz2", код_z, статика_zakaz, тест_zakaz, СЛУЖЕБНЫЕ_Z),
            "python": оценить("python", код_p, статика_python, тест_python, СЛУЖЕБНЫЕ_P)}
    json.dump(итог, open(f"{ПАПКА}/results_mutacii_{МЕТКА}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for v in ("zakaz2", "python"):
        r = итог[v]
        print(f"{v}: мутантов {r['всего']}, статика {r['статика']}, тест {r['тест']}, тихо {r['тихо']}")
        for оп, о in r["по_операторам"].items(): print(f"   {оп}: {о}")
        for s in r["примеры_тихих"]: print("   тихо:", s)
