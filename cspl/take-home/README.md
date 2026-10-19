# take_home.py: run an expert from extella.dev on your own device

The script behind section 8 of the CSPL article ("Reproduce"). It downloads a bundle from an extella.dev demo (the language handler and the expert, both JSON), saves both into your Extella account, registers the handler on your device and runs the expert there.

```sh
python3 take_home.py "https://extella.dev/api/blocks/export/skill_block_quote?handler=3" --level render
python3 take_home.py https://extella.dev/api/robot/export/skill_route_nearest
```

Needs Extella installed and signed in (it writes `~/.extella/api_token.txt` and `~/.extella/device.txt`), Python 3.8+, standard library only. Options `--token`, `--device`, `--agent` override those files. Verified on macOS on 1 October 2026.

The same file is also served at https://extella.dev/robot/classic/take_home.py for older links.
