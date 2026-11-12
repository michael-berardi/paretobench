import random
import unittest

from paretobench import stats as ST


def row(task, rep, ok, i, o, sec, cr=0, cw=0, turns=2):
    return dict(task=task, rep=rep, ok=ok, i=i, cr=cr, cw=cw, o=o, sec=sec, turns=turns)


class TestWilson(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(ST.wilson(0, 0), (0.0, 1.0))

    def test_all_correct(self):
        lo, hi = ST.wilson(10, 10)
        self.assertEqual(hi, 1.0)
        self.assertGreater(lo, 0.6)

    def test_known_value(self):
        lo, hi = ST.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)

    def test_bounds(self):
        for ok in range(6):
            lo, hi = ST.wilson(ok, 5)
            self.assertGreaterEqual(lo, 0.0)
            self.assertLessEqual(hi, 1.0)
            self.assertLessEqual(lo, hi)


class TestSignTest(unittest.TestCase):
    def test_no_discordant(self):
        self.assertEqual(ST.sign_test(0, 0), 1.0)

    def test_all_one_side(self):
        self.assertAlmostEqual(ST.sign_test(5, 0), 0.0625)
        self.assertAlmostEqual(ST.sign_test(0, 5), 0.0625)
        self.assertAlmostEqual(ST.sign_test(10, 0), 2 / 1024)

    def test_balanced(self):
        self.assertEqual(ST.sign_test(3, 3), 1.0)

    def test_symmetry(self):
        for b in range(6):
            for c in range(6):
                self.assertAlmostEqual(ST.sign_test(b, c), ST.sign_test(c, b))


class TestBootstrap(unittest.TestCase):
    def pairs(self):
        a = [row("t1", 0, True, 100, 10, 5), row("t2", 0, True, 200, 20, 9),
             row("t1", 1, True, 150, 15, 7)]
        b = [row("t1", 0, True, 200, 20, 10), row("t2", 0, True, 400, 40, 18),
             row("t1", 1, True, 300, 30, 14)]
        return {("t1", 0): (a[0], b[0]), ("t2", 0): (a[1], b[1]), ("t1", 1): (a[2], b[2])}

    def test_determinism(self):
        f = lambda r: r["i"]
        p1 = ST.boot_ratio(self.pairs(), f, f, random.Random(1))
        p2 = ST.boot_ratio(self.pairs(), f, f, random.Random(1))
        self.assertEqual(p1, p2)
        self.assertAlmostEqual(p1[0], 0.5)

    def test_ci_brackets_point(self):
        f = lambda r: r["i"]
        p, lo, hi = ST.boot_ratio(self.pairs(), f, f, random.Random(1))
        self.assertLessEqual(lo, p)
        self.assertLessEqual(p, hi)

    def test_empty(self):
        self.assertEqual(ST.boot_ratio({}, lambda r: r["i"], lambda r: r["i"], random.Random(1)),
                         (None, None, None))

    def test_compare_determinism(self):
        rates = {"i": 1e-6, "cr": 0, "cw": 0, "o": 1e-5}
        ps = self.pairs()
        a = [v[0] for v in ps.values()]
        b = [v[1] for v in ps.values()]
        c1 = ST.compare(a, b, rates)
        c2 = ST.compare(a, b, rates)
        self.assertEqual(c1, c2)
        self.assertEqual(c1["pairs"], 3)
        self.assertEqual(c1["cost_wins"], 3)
        self.assertEqual(c1["verdict"], "better")
        self.assertAlmostEqual(c1["cost"]["ratio"], 0.5)


class TestFrontier(unittest.TestCase):
    def test_basic(self):
        pts = [(1.0, 2.0), (1.0, 1.0), (0.5, 0.5), (0.5, 3.0)]
        self.assertEqual(ST.frontier(pts), [False, True, True, False])

    def test_none_cost_is_infinite(self):
        self.assertEqual(ST.frontier([(0.0, None), (1.0, 5.0)]), [False, True])

    def test_all_zero_correct(self):
        # an entry that solved nothing is never on a frontier
        self.assertEqual(ST.frontier([(0.0, None), (0.0, None)]), [False, False])
        self.assertEqual(ST.frontier([(0.0, 0.0), (1.0, 5.0)]), [False, True])

    def test_single(self):
        self.assertEqual(ST.frontier([(0.7, 3.0)]), [True])


class TestVerdict(unittest.TestCase):
    def test_better(self):
        self.assertEqual(ST.verdict(5, 5, 0.7, 0.9, None), "better")
        self.assertEqual(ST.verdict(6, 5, 0.7, 0.9, 0.01), "better")

    def test_not_better_when_correct_lower(self):
        self.assertEqual(ST.verdict(4, 5, 0.7, 0.9, 0.5), "no clear difference")

    def test_worse_cost(self):
        self.assertEqual(ST.verdict(5, 5, 1.1, 1.4, None), "worse")

    def test_worse_correct_significant(self):
        self.assertEqual(ST.verdict(2, 5, 0.7, 0.9, 0.01), "worse")

    def test_no_clear_difference(self):
        self.assertEqual(ST.verdict(5, 5, 0.8, 1.2, None), "no clear difference")
        self.assertEqual(ST.verdict(5, 5, None, None, None), "no clear difference")

    def test_interval_touching_one_is_not_better(self):
        self.assertEqual(ST.verdict(5, 5, 0.8, 1.0, None), "no clear difference")
        self.assertEqual(ST.verdict(5, 5, 1.0, 1.2, None), "no clear difference")


class TestEntrySummary(unittest.TestCase):
    def test_weighted_when_free(self):
        rates = {"i": 0, "cr": 0, "cw": 0, "o": 0}
        rows = [row("t1", 0, True, 100, 10, 5, cr=10, cw=10)]
        s = ST.entry_summary(rows, rates)
        self.assertAlmostEqual(s["metric"], 100 * 1 + 10 * 0.1 + 10 * 1.25 + 10 * 4)
        self.assertEqual(s["correct"], 1)
        self.assertEqual(s["median_sec"], 5)

    def test_p90(self):
        self.assertEqual(ST.p90(list(range(1, 11))), 9)
        self.assertEqual(ST.p90([3]), 3)
        self.assertIsNone(ST.p90([]))

    def test_cost_per_correct_none_when_no_correct(self):
        rates = {"i": 1e-6, "cr": 0, "cw": 0, "o": 1e-5}
        s = ST.entry_summary([row("t1", 0, False, 100, 10, 5)], rates)
        self.assertIsNone(s["metric_per_correct"])


if __name__ == "__main__":
    unittest.main()


class TestReliability(unittest.TestCase):
    def rows(self):
        # tasks a, b, c with 3 repeats: a all correct, b one of three, c none; one timeout on c
        spec = {("a", 0): True, ("a", 1): True, ("a", 2): True,
                ("b", 0): False, ("b", 1): True, ("b", 2): False,
                ("c", 0): False, ("c", 1): False, ("c", 2): False}
        out = []
        for (t, rep), ok in spec.items():
            r = row(t, rep, ok, 10, 1, 1.0)
            r["err"] = "timeout after 600s" if (t, rep) == ("c", 1) else ""
            out.append(r)
        return out

    def test_pass_at_k(self):
        p = ST.pass_at_k(self.rows())
        self.assertEqual(p["k"], 3)
        self.assertAlmostEqual(p["pass_any"], 2 / 3)
        self.assertAlmostEqual(p["pass_all"], 1 / 3)

    def test_pass_at_k_empty(self):
        self.assertEqual(ST.pass_at_k([]), {"k": 0, "pass_any": 0.0, "pass_all": 0.0})

    def test_timeouts(self):
        self.assertEqual(ST.timeouts(self.rows()), 1)
        self.assertEqual(ST.timeouts([dict(row("a", 0, True, 1, 1, 1.0))]), 0)
        wrapped = dict(row("a", 0, False, 1, 1, 1.0), err="RunFail('timeout after 30s')")
        self.assertEqual(ST.timeouts([wrapped]), 1)  # the runner stores repr(err)

    def test_per_rep_correct(self):
        p = ST.per_rep_correct(self.rows())
        self.assertEqual(list(p), [0, 1, 2])
        self.assertAlmostEqual(p[0], 1 / 3)
        self.assertAlmostEqual(p[1], 2 / 3)
        self.assertAlmostEqual(p[2], 1 / 3)

    def test_entry_summary_carries_all_three(self):
        s = ST.entry_summary(self.rows(), {"i": 1, "cr": 0, "cw": 0, "o": 0})
        self.assertEqual(s["pass_at_k"]["k"], 3)
        self.assertEqual(s["timeouts"], 1)
        self.assertEqual(sorted(s["per_rep_correct"]), [0, 1, 2])
