"""Plugin registry. Plugins register themselves when their module is imported."""
import importlib
import pkgutil

PLUGINS = {}


class Plugin:
    name = "plugin"
    priority = 500
    kinds = ()
    enabled = True

    def handles(self, event):
        return event.get("kind") in self.kinds

    def process(self, event):
        return event


def register(cls):
    PLUGINS[cls.name] = cls()
    return cls


def load_all():
    import plugins
    for info in pkgutil.iter_modules(plugins.__path__):
        if info.name.startswith("plugin_"):
            importlib.import_module("plugins." + info.name)
    return len(PLUGINS)


def enabled():
    return sorted((p for p in PLUGINS.values() if p.enabled), key=lambda p: (p.priority, p.name))


def run_chain(event):
    for p in enabled():
        if p.handles(event):
            event = p.process(dict(event))
    return event
