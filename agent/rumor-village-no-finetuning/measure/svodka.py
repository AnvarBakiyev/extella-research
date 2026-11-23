"""Сводка замера Rumor Village. Запуск: python3 -I svodka.py"""
import collections, json, os, sys

ZDES = os.path.dirname(os.path.abspath(__file__))
IMENA = {"A": "Qwen 3.5 9B через язык village", "B": "Qwen 3.5 9B свободным JSON",
         "C": "DeepSeek-V4-Flash через язык village", "D": "DeepSeek-V4-Flash свободным JSON"}


def main():
    print("| условие | карточек | ответ принят | выдуманных воспоминаний | отклонённых действий | бессвязных | секунд на решение | токенов в запросе |")
    print("|---|---|---|---|---|---|---|---|")
    prichiny = {}
    for u in "ABCD":
        p = os.path.join(ZDES, "zamer_%s.json" % u)
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        n = len(d)
        prin = sum(1 for v in d.values() if v["prinyato"])
        vyd = sum(len((v.get("bedy") or {}).get("vydumannoe", [])) for v in d.values())
        otk = sum(len((v.get("bedy") or {}).get("otklonennoe", [])) for v in d.values())
        bes = sum(len((v.get("bedy") or {}).get("bessvyaznoe", [])) for v in d.values())
        vydk = sum(1 for v in d.values() if (v.get("bedy") or {}).get("vydumannoe"))
        otkk = sum(1 for v in d.values() if (v.get("bedy") or {}).get("otklonennoe"))
        besk = sum(1 for v in d.values() if (v.get("bedy") or {}).get("bessvyaznoe"))
        sek = sum(v["sek"] for v in d.values()) / max(n, 1)
        tin = [v["tok_in"] for v in d.values() if v["tok_in"]]
        print("| %s | %d | %d (%.0f %%) | %d на %d карточках | %d на %d | %d на %d | %.1f | %s |"
              % (IMENA[u], n, prin, 100.0 * prin / max(n, 1), vyd, vydk, otk, otkk, bes, besk,
                 sek, (sum(tin) // len(tin)) if tin else "не считались"))
        c = collections.Counter()
        for v in d.values():
            if not v["prinyato"] and v.get("otkaz"):
                c[v["otkaz"].split(":")[0][:60]] += 1
            for vid in ("vydumannoe", "otklonennoe", "bessvyaznoe"):
                for t in (v.get("bedy") or {}).get(vid, []):
                    c[vid + ": " + t.split(",")[0][:60]] += 1
        prichiny[u] = c
    print()
    for u, c in prichiny.items():
        if not c:
            continue
        print("### %s" % IMENA[u])
        for k, v in c.most_common(12):
            print("- %d × %s" % (v, k))
        print()


if __name__ == "__main__":
    main()
