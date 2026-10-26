#!/bin/sh
# Исполнитель на Mac: RQ-воркер очереди mac через туннель
cd "$(dirname "$0")"; exec .venv/bin/rq worker mac --url redis://127.0.0.1:16379 --path "$PWD"
