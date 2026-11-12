"""A secondary index: field value -> set of record ids."""


class SecondaryIndex:
    def __init__(self, field):
        self.field = field
        self._map = {}

    def add(self, record):
        self._map.setdefault(getattr(record, self.field), set()).add(record.id)

    def remove(self, record):
        ids = self._map.get(getattr(record, self.field))
        if ids:
            ids.discard(record.id)
            if not ids:
                del self._map[getattr(record, self.field)]

    def lookup(self, value):
        return sorted(self._map.get(value, ()))

    def rebuild(self, records):
        self._map.clear()
        for r in records:
            self.add(r)
        return len(self._map)

    def keys(self):
        return sorted(self._map, key=str)
