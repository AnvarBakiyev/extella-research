# Задания не хранятся в репозитории

`en.jsonl` это чужие данные (репозиторий manuelgscom/rumor-village, лицензия MIT).
В наш репозиторий они не кладутся, чтобы не тащить 1,7 МБ чужого текста.

Как получить:

```bash
curl -sSL -o en.jsonl https://raw.githubusercontent.com/manuelgscom/rumor-village/main/training/testset/decision/en.jsonl
shasum -a 256 en.jsonl
# должно быть e5acda14cceb3dd24b316a8219de48d2c42c54ca0c11f4c8ae624057a5a03a0d
```

1200 строк: 1000 задач `decide` и 200 задач `extract`.
