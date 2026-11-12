# API notes

`api.router.handle(request, registry)` returns `{"status": <int>, "body": <dict>}`.

| op | request keys | success body |
|---|---|---|
| `get` | `entity`, `id` | the record dict |
| `put` | `entity`, `record` | the stored record dict |
| `delete` | `entity`, `id` | `{"deleted": id}` |
| `list` | `entity` | `{"items": [records sorted by id]}` |
| `order_total` | `lines`, `zone`, `weight_g`, optional `rate_bp`, `coupon_cents` | the price breakdown |
| `health` | none | `{"ok": true}` |

Errors are `{"status": 400|404|409, "body": {"error": "<message>"}}`.

## Command line

`python -m cli list <entity>` prints the records as one JSON document. `python -m cli get <entity> <id>`,
`put <entity> <json>` and `delete <entity> <id>` work the same way. The data directory is `$FREIGHT_DATA`
(default `data/store`).
