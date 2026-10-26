#!/bin/sh
# publish.sh <новый steps_handler.py>: одна команда — проверка и установка на Mac и на сервере
set -e; cd "$(dirname "$0")"; K="-i $HOME/.ssh/<ssh-key>"; S=ubuntu@<server-2-ip>
PY=.venv/bin/python ./deploy.sh "$1" ../s2/cases.json
scp -q $K "$1" ../s2/cases.json deploy.sh ../s2/check_release.py $S:pystek/incoming/
ssh $K -o BatchMode=yes $S 'cd ~/pystek/incoming && PY=python3 sh ./deploy.sh ./'"$(basename "$1")"' ./cases.json'
