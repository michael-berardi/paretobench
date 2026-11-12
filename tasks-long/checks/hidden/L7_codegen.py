import io
import json
import random
import unittest

from cli.main import main
from store.registry import Registry


def ref_delays(attempts, base, factor, max_delay):
    return [min(max_delay, base * factor ** i) for i in range(attempts - 1)]


class RefBucket:
    def __init__(self, capacity, rate, clock):
        self.capacity, self.rate, self.clock = capacity, rate, clock
        self.tokens, self.last = float(capacity), clock()

    def _refill(self):
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + max(0.0, now - self.last) * self.rate)
        self.last = now

    def try_acquire(self, n=1):
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def wait_time(self, n=1):
        self._refill()
        return 0.0 if self.tokens >= n else (n - self.tokens) / self.rate


class Flaky:
    def __init__(self, failures, exc=RuntimeError):
        self.left, self.exc, self.calls = failures, exc, 0

    def __call__(self):
        self.calls += 1
        if self.left > 0:
            self.left -= 1
            raise self.exc(f"fail {self.calls}")
        return "done"


class TestRetry(unittest.TestCase):
    def test_backoff_delays_seeded(self):
        from core.retry import backoff_delays
        rng = random.Random(7)
        for _ in range(60):
            a = rng.randrange(1, 8)
            b, f, m = rng.choice([0.25, 0.5, 1.0]), rng.choice([1.0, 2.0, 3.0]), rng.choice([1.0, 2.0, 4.0, 8.0])
            got = backoff_delays(a, b, f, m)
            want = ref_delays(a, b, f, m)
            self.assertEqual(len(got), len(want))
            for x, y in zip(got, want):
                self.assertAlmostEqual(x, y, places=9)

    def test_backoff_rejects_zero_attempts(self):
        from core.retry import backoff_delays
        with self.assertRaises(ValueError):
            backoff_delays(0, 1.0, 2.0, 5.0)

    def test_retry_call_seeded(self):
        from core.retry import retry_call
        rng = random.Random(11)
        for _ in range(80):
            attempts = rng.randrange(1, 7)
            failures = rng.randrange(0, 9)
            b, f, m = rng.choice([0.25, 0.5, 1.0]), rng.choice([1.0, 2.0, 3.0]), rng.choice([1.0, 2.0, 4.0])
            fn, slept = Flaky(failures), []
            if failures < attempts:
                self.assertEqual(retry_call(fn, attempts, b, f, m, sleep=slept.append), "done")
                self.assertEqual(fn.calls, failures + 1)
                want = ref_delays(attempts, b, f, m)[:failures]
            else:
                with self.assertRaises(RuntimeError) as cm:
                    retry_call(fn, attempts, b, f, m, sleep=slept.append)
                self.assertEqual(str(cm.exception), f"fail {attempts}")  # the last error is re-raised
                self.assertEqual(fn.calls, attempts)
                want = ref_delays(attempts, b, f, m)
            self.assertEqual(len(slept), len(want))
            for x, y in zip(slept, want):
                self.assertAlmostEqual(x, y, places=9)

    def test_only_listed_exceptions_are_retried(self):
        from core.retry import retry_call
        fn, slept = Flaky(3, exc=KeyError), []
        with self.assertRaises(KeyError):
            retry_call(fn, 5, 0.5, 2.0, 5.0, retry_on=(ValueError,), sleep=slept.append)
        self.assertEqual((fn.calls, slept), (1, []))

    def test_default_attempts_come_from_config(self):
        from core import config
        from core.retry import retry_call
        fn = Flaky(99)
        with self.assertRaises(RuntimeError):
            retry_call(fn, sleep=lambda s: None)
        self.assertEqual(fn.calls, config.DEFAULT_RETRY_LIMIT)

    def test_bad_attempts(self):
        from core.retry import retry_call
        with self.assertRaises(ValueError):
            retry_call(lambda: 1, attempts=0)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class TestBucket(unittest.TestCase):
    def test_seeded_sequences_match_reference(self):
        from core.ratelimit import TokenBucket
        rng = random.Random(23)
        for _ in range(60):
            cap, rate = rng.randrange(1, 9), rng.choice([0.5, 1.0, 2.0, 4.0])
            c1, c2 = Clock(), Clock()
            a, b = TokenBucket(cap, rate, clock=c1), RefBucket(cap, rate, c2)
            for _ in range(50):
                step = rng.choice([0.0, 0.25, 0.5, 1.0, 2.0])
                c1.t += step
                c2.t += step
                n = rng.randrange(1, cap + 1)
                if rng.random() < 0.25:
                    self.assertAlmostEqual(a.wait_time(n), b.wait_time(n), places=9)
                else:
                    self.assertEqual(a.try_acquire(n), b.try_acquire(n))
                self.assertAlmostEqual(a.tokens, b.tokens, places=9)

    def test_starts_full_and_never_exceeds_capacity(self):
        from core.ratelimit import TokenBucket
        c = Clock()
        b = TokenBucket(3, 1.0, clock=c)
        self.assertEqual([b.try_acquire() for _ in range(4)], [True, True, True, False])
        c.t += 100
        self.assertAlmostEqual(b.tokens, 3.0)

    def test_failed_acquire_takes_nothing(self):
        from core.ratelimit import TokenBucket
        c = Clock()
        b = TokenBucket(4, 1.0, clock=c)
        self.assertTrue(b.try_acquire(3))
        self.assertFalse(b.try_acquire(2))
        self.assertAlmostEqual(b.tokens, 1.0)
        self.assertAlmostEqual(b.wait_time(2), 1.0)

    def test_clock_going_backwards_adds_nothing(self):
        from core.ratelimit import TokenBucket
        c = Clock()
        c.t = 10.0
        b = TokenBucket(2, 1.0, clock=c)
        b.try_acquire(2)
        c.t = 5.0
        self.assertFalse(b.try_acquire())

    def test_invalid_arguments(self):
        from core.ratelimit import TokenBucket
        for args in ((0, 1.0), (-1, 1.0), (2, 0), (2, -1.0)):
            with self.assertRaises(ValueError):
                TokenBucket(*args)
        b = TokenBucket(2, 1.0, clock=Clock())
        for n in (0, -1, 3):
            with self.assertRaises(ValueError):
                b.try_acquire(n)


class TestCli(unittest.TestCase):
    def run_cli(self, argv):
        out = io.StringIO()
        rc = main(argv, registry=Registry(), out=out)
        return rc, json.loads(out.getvalue())

    def test_simulate_limiter(self):
        rc, body = self.run_cli(["simulate-limiter", "--capacity", "2", "--rate", "1",
                                 "--times", "0,0,0,0.5,1,1,2.5"])
        self.assertEqual(rc, 0)
        clock = Clock()
        ref = RefBucket(2, 1.0, clock)
        want = []
        for t in (0, 0, 0, 0.5, 1, 1, 2.5):
            clock.t = float(t)
            want.append(ref.try_acquire())
        self.assertEqual(body, {"allowed": want})

    def test_retry_plan(self):
        rc, body = self.run_cli(["retry-plan", "--attempts", "5", "--base", "0.5", "--factor", "2",
                                 "--max-delay", "3"])
        self.assertEqual(rc, 0)
        self.assertEqual(body, {"delays": [0.5, 1.0, 2.0, 3.0]})
        rc, body = self.run_cli(["retry-plan", "--attempts", "3"])
        self.assertEqual(body, {"delays": [0.1, 0.2]})

    def test_cli_errors(self):
        rc, body = self.run_cli(["simulate-limiter", "--capacity", "0", "--rate", "1", "--times", "0"])
        self.assertEqual(rc, 1)
        self.assertIn("error", body)
        rc, body = self.run_cli(["retry-plan", "--attempts", "0"])
        self.assertEqual(rc, 1)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
