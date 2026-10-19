def tally(code = "", filtered_source_code = "", func_name = "", **extra):
    # Handler of the language "tally": a program is lines "add N" or "sub N", N up to nine digits 0-9.
    # The whole program is checked first; if any line is not a tally statement, nothing is executed.
    import platform, socket
    lines = [line.split() for line in (code or filtered_source_code or "").splitlines() if line.split()]
    for n, parts in enumerate(lines, 1):
        if len(parts) != 2 or parts[0] not in ("add", "sub") or not (parts[1].isascii() and parts[1].isdigit() and len(parts[1]) <= 9):
            return {"status": "rejected", "reason": "statement %d is not a tally statement: %s" % (n, " ".join(parts)[:40])}
    total = 0
    for op, number in lines:
        total += int(number) if op == "add" else -int(number)
    return {"status": "success", "language": "tally", "expert": func_name, "total": total, "host": socket.gethostname(), "os": platform.system() + " " + platform.machine()}
