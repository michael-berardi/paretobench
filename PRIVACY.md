# Privacy

ParetoBench has no telemetry, accounts, identifiers or usage reporting.

## Network requests

- **Benchmarks** call the models and harnesses you configure, with your keys, as described
  in the README. Nothing is sent to the project.
- **Update check.** Once a day at most, an interactive command sends one anonymous `GET` to
  `https://api.github.com/repos/michael-berardi/paretobench/releases/latest`. It carries only the
  fixed User-Agent `paretobench-update-check`: no version, configuration, model names,
  results, usage or machine data. GitHub sees the request's IP address, as with any web
  request. It times out after four seconds and is never retried in a loop.
- **Install.** `paretobench update` (or an automatic install you turned on) downloads the
  release's `paretobench.tar.gz` and `SHA256SUMS` from GitHub, or runs your package manager
  against the release tag.

The check is off when output is not a terminal, in CI, in agent shells, with
`PARETOBENCH_NO_UPDATE_CHECK=1`, or with `"check_automatically": false` in
`~/.config/paretobench/settings.json`. Details: [docs/updates.md](docs/updates.md).

## Local files

- `~/.config/paretobench/`: your models config, optional `env` file and update `settings.json`.
- The update cache (`updates.json`, mode 0600) holds the check time, latest version, skipped
  version, last notice and the cause of a failed check or automatic install.
- Benchmark rows and raw logs go only to the directories you pass (`--out`, `PB_LOG_DIR`);
  keys are scrubbed from raw logs.
- Result directories a run creates are 0700; rows, summaries and raw logs are 0600. Raw logs are
  kept until you delete them; set `PB_LOG_KEEP=<n>` to keep only the newest n `.jsonl` files in
  `PB_LOG_DIR`. Per-run work directories under the system temp folder are 0700 and removed on exit.
- Processes ParetoBench starts get `DO_NOT_TRACK=1` and `HF_HUB_DISABLE_TELEMETRY=1`; DeepSeek
  Harness also gets `DSH_TELEMETRY_MODE=DISABLED`. The installers set the same switches and create
  the config file 0600 in a 0700 folder (current-user ACLs on Windows).

## Deleting it all

Remove your result directories, `PB_LOG_DIR`, `~/.config/paretobench/`, the update cache folder
(`~/Library/Caches/paretobench` on macOS, `$XDG_CACHE_HOME/paretobench` or `~/.cache/paretobench` on
Linux, `%LOCALAPPDATA%\paretobench\Cache` on Windows) and the bundle in `~/.paretobench` (Windows: `%LOCALAPPDATA%\ParetoBench`).
