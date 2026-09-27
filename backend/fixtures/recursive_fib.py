def fib(n: int) -> int:
    """Return the nth Fibonacci number."""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)


def fib_sequence(n: int) -> list:
    """Return the Fibonacci sequence up to position n."""
    if n <= 0:
        return []
    return [fib(i) for i in range(n)]
