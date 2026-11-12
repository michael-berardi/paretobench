from _ref import *

hits = grep(r"def reconcile_manifest\(", ".")
read(hits[0][0])
grep(r"DEFAULT_RETRY_LIMIT", ".")
cfg = read("core/config.py")
limit = re.search(r"^DEFAULT_RETRY_LIMIT = (\d+)", cfg, re.M).group(1)
ls("logs")
read("core/text.py")
calls = [h for h in grep(r"legacy_checksum\(", ".")
         if not h[2].lstrip().startswith(("def ", "#", "NOTE", "from "))]
read(calls[0][0])
read(calls[1][0])
q4 = sh("awk '$3==\"/v2/orders\" && $4==503 && $1 ~ /^2025-03-02/ {n++} END {print n+0}' logs/access.log").stdout.strip()
q5 = sh("awk '$3==\"/v2/export\" && $4==200 {s+=$5} END {print s+0}' logs/access.log").stdout.strip()
sh("head -3 logs/access.log")
sh("wc -l logs/access.log")
say(f"Q1: {hits[0][0]}\nQ2: {limit}\nQ3: " + ", ".join(f"{f}:{n}" for f, n, _ in calls) + f"\nQ4: {q4}\nQ5: {q5}\n")
