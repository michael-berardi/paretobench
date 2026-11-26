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
