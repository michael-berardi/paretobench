"""Base class for entity records."""
from core.errors import ValidationError
from core.ids import check_id


class Record:
    """A record has a string id and a few typed fields. Subclasses set kind, prefix and fields."""

    kind = "record"
    prefix = "rec"
    fields = ()          # ((name, type-name), ...)
    required = ()

    def __init__(self, id, **values):
        self.id = id
        known = {name for name, _ in self.fields}
        extra = set(values) - known
        if extra:
            raise ValidationError(f"{self.kind}: unknown fields {sorted(extra)}")
        for name, _kind in self.fields:
            setattr(self, name, values.get(name))

    def to_dict(self):
        out = {"id": self.id}
        for name, _kind in self.fields:
            out[name] = getattr(self, name)
        return out

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        rid = data.pop("id", None)
        return cls(rid, **data)

    def validate(self):
        check_id(self.id, self.prefix)
        for name in self.required:
            if getattr(self, name) in (None, ""):
                raise ValidationError(f"{self.kind}: {name} is required")
        return self

    def __eq__(self, other):
        return isinstance(other, Record) and self.kind == other.kind and self.to_dict() == other.to_dict()

    def __repr__(self):
        return f"<{self.kind} {self.id}>"
