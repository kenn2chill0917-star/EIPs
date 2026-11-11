"""Tests for the reference validator (validator.py).

Shares the vectors of test_overflow.py, run with STACK_LIMIT reduced
to 16 so the overflow examples stay small.  The overflow-only
rejections of the bounds-proving validator are valid here — overflow
is not validated — and every other expectation, underflow included,
is unchanged.

The memo of validator.py is covered too: an unchanged code answers
from the cache, a changed stack limit does not, the key is the code's
content rather than the buffer holding it, and clearing empties it.
Opcodes: CALLDEST=0xBB, CALLSUB=0xBC, RETURNSUB=0xBF.
"""
import validator as ref
from test_overflow import TESTS

# Rejected only for overflow by the bounds-proving validator.
OVERFLOW_ONLY = {
    "17 pushes overflow",
    "sub high amplified, 2 calls",
    "call chain depth 17",
}

# PUSH0 x17, PUSH1 21, CALLSUB, STOP, CALLDEST, POP x17, RETURNSUB:
# the subroutine demands 17 items from its caller, which the stack
# limit of 16 refuses and the default limit of 1024 allows.
DEEP_DEMAND = bytes.fromhex("5F" * 17 + "6015" + "BC" + "00" + "BB"
                            + "50" * 17 + "BF")


def cache_checks():
    """The memo's behaviour: a hit on unchanged input, no conflation of
    stack limits, a content key, and an emptying clear_cache()."""
    results = []
    code = bytes.fromhex(TESTS[0][1])

    ref.clear_cache()
    first = ref.validate(code)
    before = ref.cache_info()
    again = ref.validate(code)
    after = ref.cache_info()
    results.append(("repeat call hits the memo",
                    again == first and after.hits == before.hits + 1
                    and after.misses == before.misses))

    results.append(("stack limits are not conflated",
                    ref.validate(DEEP_DEMAND) is True
                    and ref.validate(DEEP_DEMAND, stack_limit=16) is False))

    ref.clear_cache()
    ref.validate(code)
    hits = ref.cache_info().hits
    ref.validate(bytearray(code))
    info = ref.cache_info()
    results.append(("bytearray keys by content",
                    info.hits == hits + 1 and info.currsize == 1))

    ref.clear_cache()
    results.append(("clear_cache empties the memo",
                    ref.cache_info().currsize == 0))

    # Cached answers must be the answers the traversal gives.
    agree = True
    for _, hexcode, _ in TESTS:
        walked = ref._validate_uncached(bytes.fromhex(hexcode), 16)
        for _ in range(2):
            if ref.validate(bytes.fromhex(hexcode), stack_limit=16) != walked:
                agree = False
    results.append(("cached answers match the traversal", agree))
    return results


def main() -> int:
    failures = 0
    for name, hexcode, expected in TESTS:
        want = True if name in OVERFLOW_ONLY else expected
        got = ref.validate(bytes.fromhex(hexcode), stack_limit=16)
        ok = got == want
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  {name:32s} "
              f"code=0x{hexcode:<28s} expected={want} got={got}")

    checks = cache_checks()
    for name, ok in checks:
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    total = len(TESTS) + len(checks)
    print(f"\n{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
