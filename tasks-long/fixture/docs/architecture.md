# Architecture

Requests enter through `api.router.handle(request, registry)`. A request is a dict with an `op` key.
The router validates it, finds the entity handler in `api.handlers`, and the handler reads or writes through
the `store.registry.Registry` that owns one `Repository` per entity.

Repositories keep records by string id. A registry built with a root directory persists each entity to
`<root>/<entity>.json`; without a root it stays in memory (the tests use this).

Money is integer cents everywhere. `core.pricing` holds the only price rules: tiers, tax, shipping, coupon cap.

Plugins (`plugins/plugin_NN.py`) register themselves with `plugins.registry` when imported. The chain runs in
priority order and each plugin may rewrite an event.

`ingest` parses the access log (`logs/access.log`) and the shipment CSV (`data/shipments.csv`) and builds the
summaries in `ingest.reports`.
