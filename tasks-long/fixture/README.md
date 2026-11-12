# freightdesk

A small freight-desk back office: records for customers, shipments, invoices and a dozen other things,
a request router, a command line, log and CSV ingestion, and a plugin chain that post-processes events.

Layout:

- `core/`     money, pricing, errors, config defaults, small text helpers
- `store/`    records, repositories (in memory or JSON files), queries, indexes, one model per entity
- `api/`      the request router and one handler module per entity
- `cli/`      the command line (`python -m cli --help`)
- `ingest/`   access-log and CSV parsing, reports
- `plugins/`  the event plugin chain
- `tests/`    the unittest suite: `python3 -m unittest discover -s tests -t .`
- `docs/`     API notes and architecture
- `logs/`, `data/`   sample logs, CSV and seeded store files

Everything is Python standard library only. Amounts are integer cents. See `docs/architecture.md`.
