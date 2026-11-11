# Security

## Keys

API keys are read at run time from the Pi agent auth store (`PB_PI_AGENT_DIR`, default `~/.pi/agent`).
They are passed to harness children only through the environment. They are never printed, never written
to result rows, never passed on a command line, and are scrubbed from raw event logs kept via `PB_LOG_DIR`.
The per-process work dir (which holds copies of the auth store for the pi-family lanes) is mode 0700 and
removed on exit, including on SIGTERM and SIGINT.

Keep `~/.config/paretobench/models.json` and `~/.config/paretobench/env` at mode 0600. Do not commit them.
Do not paste keys into issues, logs or result files.

## Running harnesses

The benchmark runs coding agents with write access to a fresh fixture copy in a private temp dir, with a
hard timeout and process-group kill. Run it only with models and harnesses you trust, on a machine where
an agent editing a temp directory is acceptable. The fixture contains no secrets.

## Reporting a vulnerability

Open a private security advisory on the repository, or contact the maintainers through the repository's
listed contact. Do not open public issues for key exposure or runner escape problems. Include the
paretobench version (`paretobench --version`) and the smallest reproduction you can share without secrets.
