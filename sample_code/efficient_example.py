"""Same functionality as inefficient_example.py, written efficiently."""

from functools import lru_cache
import pandas as pd


@lru_cache(maxsize=None)
def fast_fibonacci(n):
    if n <= 1:
        return n
    return fast_fibonacci(n - 1) + fast_fibonacci(n - 2)


def build_report(names, scores):
    lines = [f"{name}: {score}" for name, score in zip(names, scores)]
    return "\n".join(lines)


def find_duplicates(items):
    seen = set()
    duplicates = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return list(duplicates)


def process_dataframe(df: pd.DataFrame):
    return df["value"].sum()


def sum_of_squares(numbers):
    return sum(n * n for n in numbers)
