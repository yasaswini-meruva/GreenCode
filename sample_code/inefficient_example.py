"""
Sample intentionally inefficient code, used to demo GreenCode's detection.
Every pattern in here is a real anti-pattern the analyzer should catch.
"""

import pandas as pd


def naive_fibonacci(n):
    # unmemoized recursion -- exponential recomputation
    if n <= 1:
        return n
    return naive_fibonacci(n - 1) + naive_fibonacci(n - 2)


def build_report(names, scores):
    report = ""
    for i in range(len(names)):          # range(len(x)) instead of enumerate
        report += f"{names[i]}: {scores[i]}\n"   # string += in a loop
    return report


def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):          # nested loop -> O(n^2)
        for j in range(len(items)):
            if i != j and items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates


def process_dataframe(df: pd.DataFrame):
    total = 0
    for index, row in df.iterrows():     # pandas iterrows anti-pattern
        total += row["value"]
    return total


def sum_of_squares(numbers):
    return sum([n * n for n in numbers])  # list comp inside sum() instead of generator


def collect_growing(data_stream, target_size):
    result = []
    i = 0
    while len(result) < target_size:     # len() recomputed on 'result' every iteration
        result.append(data_stream[i])
        i += 1
    return result