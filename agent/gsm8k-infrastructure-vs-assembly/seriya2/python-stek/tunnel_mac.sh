#!/bin/sh
# Исходящий ssh-туннель Mac -> сервер: локальный 16379 ведёт в Redis сервера (127.0.0.1:6379). Входящих портов не нужно.
exec ssh -i ~/.ssh/<ssh-key> -o BatchMode=yes -o ServerAliveInterval=15 -o ExitOnForwardFailure=yes -N -L 16379:127.0.0.1:6379 ubuntu@<server-2-ip>
