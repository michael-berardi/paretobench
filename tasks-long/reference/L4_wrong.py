# a read-only task answered correctly but with a scratch file left in the repository
import runpy
import os

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "L4.py"))
open("scratch_notes.txt", "w").write("temporary\n")
