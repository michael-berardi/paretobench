from _ref import *

sh("python3 -B -m unittest tests.test_order_totals", ok=(1,))
read("tests/test_order_totals.py")
read("api/router.py")
read("api/handlers/orders.py")
read("store/orders.py")
grep(r"tier", ".")
read("core/pricing.py")
edit("core/pricing.py", "        if qty > min_qty:", "        if qty >= min_qty:")
sh("python3 -B -m unittest tests.test_order_totals")
sh("python3 -B -m unittest discover -s tests -t .")
