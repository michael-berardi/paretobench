from _ref import *

ls(".")
read("README.md")
sh("python3 scripts/verify.py", ok=(1,))
sh("python3 scripts/verify.py", ok=(1,))
sh("python3 scripts/verify.py", ok=(1,))
read("store/index.py")
read("tests/test_index_cleanup.py")
grep(r"SecondaryIndex", ".")
edit("store/index.py", "            ids.discard(record.id)\n", '''            ids.discard(record.id)
            if not ids:
                del self._map[getattr(record, self.field)]
''')
sh("python3 scripts/verify.py")
