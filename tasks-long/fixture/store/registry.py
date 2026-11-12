"""One Repository per entity, in memory or under a data directory."""
import os

from store.memory import Repository
from store.models import ENTITIES


class Registry:
    def __init__(self, root=None):
        self.root = root
        self._repos = {}

    def entities(self):
        return sorted(ENTITIES)

    def repo(self, entity):
        if entity not in ENTITIES:
            from core.errors import NotFound
            raise NotFound(f"unknown entity: {entity}")
        if entity not in self._repos:
            path = os.path.join(self.root, entity + ".json") if self.root else None
            self._repos[entity] = Repository(ENTITIES[entity], path)
        return self._repos[entity]

    def save_all(self):
        for repo in self._repos.values():
            repo.save()


def open_default():
    """The registry the command line uses: $FREIGHT_DATA or data/store."""
    return Registry(os.environ.get("FREIGHT_DATA", "data/store"))
