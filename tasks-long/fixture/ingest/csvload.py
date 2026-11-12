"""Load the shipment CSV: id,customer,carrier,weight_g,zone,status,cost_cents."""
import csv

from core.errors import ValidationError

COLUMNS = ["id", "customer", "carrier", "weight_g", "zone", "status", "cost_cents"]


def read_shipments(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValidationError(f"unexpected columns: {reader.fieldnames}")
        for row in reader:
            row["weight_g"] = int(row["weight_g"])
            row["cost_cents"] = int(row["cost_cents"])
            yield row
