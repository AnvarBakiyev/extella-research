#!/bin/sh
# K4 на Python: одна команда — кандидат steps проверяется на 100 программах на каждой машине и ставится только при чистой проверке.
set -e; cd "$(dirname "$0")/.."; C="$1"; K="-i $HOME/.ssh/<ssh-key>"; S=ubuntu@<server-2-ip>
CHECK='import importlib.util,json,os,sqlite3,sys,shutil; sys.path.insert(0,sys.argv[3]); import check
s=importlib.util.spec_from_file_location("c",sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
rows=[dict(zip(("is_wholesale","is_vip","qty","price_cents","coupon"),r)) for r in sqlite3.connect(os.path.expanduser("~/kompoziciya/orders.db")).execute("SELECT is_wholesale,is_vip,qty,price_cents,coupon FROM orders ORDER BY id")]
bad=check.check(m,json.load(open(sys.argv[2])),rows)
if bad: print("отказ:",len(bad),"недопустимых изменений на",os.uname().nodename); sys.exit(1)
shutil.copy(sys.argv[1],os.path.expanduser("~/kompoziciya/py/langs/steps.py")); print("установлено на",os.uname().nodename)'
python3 -c "$CHECK" "$C" k4/cases.json k4
scp -q $K "$C" k4/cases.json k4/check.py $S:kompoziciya/incoming/
ssh -n $K -o BatchMode=yes $S "cd ~/kompoziciya/incoming && python3 -c '$(echo "$CHECK" | sed "s/'/'\\\\''/g")' ./$(basename "$C") ./cases.json ."
