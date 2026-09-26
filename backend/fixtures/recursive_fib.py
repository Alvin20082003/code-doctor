"""
Fixture: naive recursive Fibonacci — O(2^n) time, O(n) space (call stack).
"""


def fib(n: int) -> int:
    """
    Textbook recursive Fibonacci.
    Makes two recursive calls per invocation, leading to exponential
    time complexity O(2^n) and O(n) stack depth.
    """
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)


def fib_sequence(n: int) -> list:
    """
    Build the full Fibonacci sequence up to n using the naive recursion above.
    Demonstrates that even wrapping the naive fib in a list comprehension
    doesn't save the underlying exponential work.
    """
    if n <= 0:
        return []
    return [fib(i) for i in range(n)]
