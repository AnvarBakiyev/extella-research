# The tally example (article, section 4)

A language of two statements (`add N`, `sub N`), its handler, a registrar and a program.

- `handler.py`: the handler. Changed on 16 October 2026: the number check accepts only the digits 0 to 9, at most nine of them.
- `handler_c.py`: a sixteen-line handler that compiles C with the device's compiler and runs the binary.
- `run_tiny.py`: builds the registrar, saves both experts and runs them. Needs Extella installed and signed in; Python 3.8+.
- `verify_all.py`: repeats the eight runs of 1 October in order.
- `runs-2026-10-01.json`: raw answers of 1 October (handler version of 918 bytes).
- `runs-2026-10-16.json`: raw answers of 16 October with the fixed handler (991 bytes).
