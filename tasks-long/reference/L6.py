from _ref import *

sh("head -3 data/q3_ledger_report.txt")
P = ("import sys\\nrows=[dict(kv.split('=',1) for kv in l.split()[1:])|{'date':l.split()[0]} "
     "for l in open('data/q3_ledger_report.txt')]\\n")
f1 = sh("python3 -c \"" + P.replace("\\n", "; ").replace("import sys; ", "") +
        "print(sum(int(r['amount']) for r in rows if r['region']=='EU' and r['kind']=='invoice' "
        "and r['status']=='posted' and r['date'].startswith('2025-08')))\"").stdout.strip()
f2 = sh("python3 -c \"" + P.replace("\\n", "; ").replace("import sys; ", "") +
        "print(len({r['acct'] for r in rows if r['kind']=='refund' and r['status']=='posted'}))\"").stdout.strip()
f3 = sh("python3 -c \"" + P.replace("\\n", "; ").replace("import sys; ", "") +
        "print(max(int(r['amount']) for r in rows if r['kind']=='credit' and r['region']=='APAC'))\"").stdout.strip()
f4 = sh("grep -c 'status=disputed' data/q3_ledger_report.txt").stdout.strip()
f5 = sh("python3 -c \"" + P.replace("\\n", "; ").replace("import sys; ", "") +
        "t={}; [t.__setitem__(r['acct'], t.get(r['acct'],0)+int(r['amount'])) for r in rows "
        "if r['region']=='NA' and r['kind']=='invoice' and r['status']=='posted']; "
        "print(sorted(t.items(), key=lambda kv: (-kv[1], kv[0]))[0][0])\"").stdout.strip()
sh("rm data/q3_ledger_report.txt")
hits = grep(r"\.put_legacy\(", ".")
files = sorted({f for f, _, line in hits if line.strip().startswith("repo.put_legacy(")})
assert len(files) == 40, len(files)
for rel in files:
    edit_re(rel, r"\.put_legacy\(((?:[^()]|\([^()]*\))*)\)", r".put(\1, validate=True)")
sh("python3 -B -m unittest discover -s tests -t .")
grep(r"\.put_legacy\(", ".")
say(f"F1={f1}\nF2={f2}\nF3={f3}\nF4={f4}\nF5={f5}\n")
