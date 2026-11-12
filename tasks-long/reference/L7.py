from _ref import *

ls(".")
read("core/config.py")
read("cli/main.py")
read("tests/test_cli.py")
read("core/errors.py")
write("core/retry.py", '''"""Retry with exponential backoff."""
import time

from core import config


def backoff_delays(attempts, base, factor, max_delay):
    """The sleeps between attempts: min(max_delay, base * factor ** i) for i in 0 .. attempts-2."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    return [min(max_delay, base * factor ** i) for i in range(attempts - 1)]


def retry_call(fn, attempts=config.DEFAULT_RETRY_LIMIT, base=0.1, factor=2.0, max_delay=5.0,
               retry_on=(Exception,), sleep=time.sleep):
    """Call fn() until it returns; retry on the listed exceptions with backoff; re-raise the last one."""
    delays = backoff_delays(attempts, base, factor, max_delay)
    for i in range(attempts):
        try:
            return fn()
        except retry_on:
            if i == attempts - 1:
                raise
            sleep(delays[i])
''')
write("core/ratelimit.py", '''"""A token-bucket rate limiter driven by an injectable clock."""
import time


class TokenBucket:
    def __init__(self, capacity, refill_per_sec, clock=time.monotonic):
        if capacity <= 0 or refill_per_sec <= 0:
            raise ValueError("capacity and refill rate must be positive")
        self.capacity = capacity
        self.rate = refill_per_sec
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self):
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + max(0.0, now - self._last) * self.rate)
        self._last = now

    @property
    def tokens(self):
        self._refill()
        return self._tokens

    def _check(self, n):
        if n < 1 or n > self.capacity:
            raise ValueError("n must be between 1 and the capacity")

    def try_acquire(self, n=1):
        self._check(n)
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    def wait_time(self, n=1):
        self._check(n)
        self._refill()
        return 0.0 if self._tokens >= n else (n - self._tokens) / self.rate
''')
edit("cli/main.py", "from cli.commands import COMMANDS\n", "from cli.commands import COMMANDS\nfrom core.ratelimit import TokenBucket\nfrom core.retry import backoff_delays\n")
edit("cli/main.py", "    for add in COMMANDS.values():\n", '''    s = sub.add_parser("simulate-limiter", help="which requests a token bucket would allow")
    s.add_argument("--capacity", type=int, required=True)
    s.add_argument("--rate", type=float, required=True)
    s.add_argument("--times", required=True, help="comma-separated request times in seconds")
    s = sub.add_parser("retry-plan", help="the sleeps a retry would use")
    s.add_argument("--attempts", type=int, required=True)
    s.add_argument("--base", type=float, default=0.1)
    s.add_argument("--factor", type=float, default=2.0)
    s.add_argument("--max-delay", type=float, default=5.0)
    for add in COMMANDS.values():
''')
edit("cli/main.py", "def main(argv=None, registry=None, out=None):", '''class _Clock:
    t = 0.0

    def __call__(self):
        return self.t


def _utility(args, out):
    try:
        if args.cmd == "retry-plan":
            body = {"delays": backoff_delays(args.attempts, args.base, args.factor, args.max_delay)}
        else:
            clock = _Clock()
            bucket = TokenBucket(args.capacity, args.rate, clock=clock)
            allowed = []
            for t in args.times.split(","):
                clock.t = float(t)
                allowed.append(bucket.try_acquire())
            body = {"allowed": allowed}
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=out)
        return 1
    print(json.dumps(body, sort_keys=True), file=out)
    return 0


def main(argv=None, registry=None, out=None):''')
edit("cli/main.py", "    registry = registry or open_default()\n", '''    if args.cmd in ("simulate-limiter", "retry-plan"):
        return _utility(args, out)
    registry = registry or open_default()
''')
write("tests/test_retry_limiter.py", '''import unittest

from core.ratelimit import TokenBucket
from core.retry import backoff_delays, retry_call


class TestRetryLimiter(unittest.TestCase):
    def test_delays(self):
        self.assertEqual(backoff_delays(4, 1.0, 2.0, 3.0), [1.0, 2.0, 3.0])

    def test_retry_then_success(self):
        calls = []

        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("no")
            return "ok"
        slept = []
        self.assertEqual(retry_call(fn, 5, 0.5, 2.0, 5.0, sleep=slept.append), "ok")
        self.assertEqual(slept, [0.5, 1.0])

    def test_bucket(self):
        t = [0.0]
        b = TokenBucket(2, 1.0, clock=lambda: t[0])
        self.assertEqual([b.try_acquire() for _ in range(3)], [True, True, False])
        t[0] = 1.0
        self.assertTrue(b.try_acquire())


if __name__ == "__main__":
    unittest.main()
''')
sh("python3 -B -m unittest tests.test_retry_limiter")
sh("python3 -B -m cli simulate-limiter --capacity 2 --rate 1 --times 0,0,0,1")
sh("python3 -B -m cli retry-plan --attempts 4")
edit("docs/api.md", "## Command line", "## Utilities\n\n`python -m cli simulate-limiter --capacity C --rate R --times t1,t2` and\n`python -m cli retry-plan --attempts N` print JSON (`allowed`, `delays`).\n\n## Command line")
sh("python3 -B -m unittest discover -s tests -t .")
