# Contributing

ParetoBench is one maintained benchmark. Changes to tasks, checkers, runner or statistics change what the
numbers mean, so they go through review with the method in mind. Read docs/METHODOLOGY.md first.

## Rules

- Python 3.11+ standard library only. No runtime dependencies.
- No machine-specific paths, person names, client names, keys or tokens in the repo. Machine config lives
  in `~/.config/paretobench/`.
- Never print, log or store a key. Adapters never see keys; the runner passes them via child env only.
- Errors must name their cause (`PBError` with a short name).
- Keep the runner's cleanup behaviour exact: fresh fixture per run, private work dir removed on exit,
  stop flag, child process-group kill, hard timeout, balanced order, warm-up abort, resume, retries.

## Adding a task

1. Write the prompt with every requirement stated. The checker may not demand anything unstated.
2. Write the deterministic hidden checker in `tasks/checks/check.py`.
3. Write the reference solution in `tasks/reference/<id>.py`. If an obvious wrong fix exists, add
   `<id>_wrong.py` and make the checker fail on it.
4. `./pb selftest` must pass for every task. `./pb validate` must pass.
5. A changed task set gets a new hash and starts a new results series. Do not edit a task set under
   published results.

## Adding a harness adapter

1. Create `paretobench/harnesses/<name>.py` implementing validate, version, setup_lane, build_command,
   parse, after_run (see the package docstring in `harnesses/__init__.py`).
2. Register it in `harnesses/__init__.py` and add it to the doctor list in `cli.py`.
3. Add command construction tests with fake executables: assert argv, and assert no key ever appears in
   argv or adapter env.
4. Document the exact command in docs/METHODOLOGY.md.

## Adding a model

Add an entry to your local models config (see configs/models.example.json): `harnesses` list, per-harness
settings, one `rates` table. Then `./pb validate` and `./pb doctor --model KEY`.

## Checks before a pull request

```sh
python3 -m unittest discover -s tests
./pb selftest
./pb validate
```

Write the gate before running comparisons, and record any gate change before the extra runs that use it.
