# eleven of the twelve edits
import os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "L9.py")).read()
src = src.replace('    ("cli/main.py", \'description="freightdesk command line"\', \'description="freightdesk back office command line"\'),\n', "")
exec(compile(src, "L9.py", "exec"))
