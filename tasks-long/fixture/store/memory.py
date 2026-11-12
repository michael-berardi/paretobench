"""Repository: records by id, in memory, optionally mirrored to a JSON file."""
import json
import os

from core.errors import ConflictError, NotFound, ValidationError


class Repository:
    def __init__(self, record_cls, path=None):
        self.record_cls = record_cls
        self.path = path
        self._items = {}
        if path and os.path.isfile(path):
            self._load()

    # -- persistence ------------------------------------------------------
    def _load(self):
        with open(self.path) as f:
            doc = json.load(f)
        for data in doc["items"]:
            rec = self.record_cls.from_dict(data)
            self._items[rec.id] = rec

    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        doc = {"version": 3, "items": [self._items[k].to_dict() for k in sorted(self._items)]}
        with open(self.path, "w") as f:
            json.dump(doc, f, indent=1, sort_keys=True)
            f.write("\n")

    # -- access -----------------------------------------------------------
    def put(self, record, validate=False, overwrite=True):
        if validate:
            record.validate()
        if not overwrite and record.id in self._items:
            raise ConflictError(f"{record.kind} {record.id} already exists")
        if not isinstance(record, self.record_cls):
            raise ValidationError(f"expected {self.record_cls.__name__}, got {type(record).__name__}")
        self._items[record.id] = record
        return record

    def put_legacy(self, record):
        """Deprecated: store without validation. Use put(record, validate=True)."""
        return self.put(record)

    def get(self, rid):
        try:
            return self._items[rid]
        except KeyError:
            raise NotFound(f"{self.record_cls.kind} {rid} not found")

    def delete(self, rid):
        if rid not in self._items:
            raise NotFound(f"{self.record_cls.kind} {rid} not found")
        del self._items[rid]

    def all(self):
        """Records sorted by id."""
        return [self._items[k] for k in sorted(self._items)]

    def __len__(self):
        return len(self._items)

    def __contains__(self, rid):
        return rid in self._items
