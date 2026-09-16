"""
analyzer.py
-----------
Static analysis engine for GreenCode. Uses Python's built-in `ast` module
to detect coding patterns known to waste compute (and therefore energy) --
this is the "pattern detection" AI component in the architecture.

Rule-based on purpose: reliable to demo live, transparent to explain to
judges ("here is exactly what pattern was matched and why it costs more
compute"), and immune to the flakiness a trained model would add for a
3-day build. IBM Granite's job (in message_generator.py) is to turn each
raw detection into a clear explanation + suggested fix -- that's the
generative layer on top of this deterministic detection layer.
"""

import ast
from dataclasses import dataclass, field


@dataclass
class Issue:
    line: int
    pattern: str
    severity: str          # "low" | "medium" | "high"
    detail: str            # short technical description (grounds the LLM explanation)


PATTERN_WEIGHTS = {
    "nested_loop": 25,
    "range_len": 5,
    "string_concat_in_loop": 15,
    "unmemoized_recursion": 20,
    "pandas_iterrows": 20,
    "growing_list_len_check": 15,
    "list_for_reduction": 8,
}


class GreenCodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.issues: list[Issue] = []
        self._loop_depth = 0
        self._current_function_names: set[str] = set()
        self._decorated_functions: set[str] = set()

    # ---------- loop nesting ----------
    def visit_For(self, node):
        self._loop_depth += 1
        if self._loop_depth == 2:  # flag once, at the point nesting begins -- not again for deeper levels
            self.issues.append(Issue(
                line=node.lineno,
                pattern="nested_loop",
                severity="high",
                detail=f"Nested loop starting here — likely O(n^2) or worse complexity as nesting continues."
            ))
        self._check_range_len(node)
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node):
        self._loop_depth += 1
        if self._loop_depth == 2:  # flag once, at the point nesting begins
            self.issues.append(Issue(
                line=node.lineno,
                pattern="nested_loop",
                severity="high",
                detail="Nested while loop starting here — likely O(n^2) or worse complexity as nesting continues."
            ))
        self._check_growing_list_len_check(node)
        self.generic_visit(node)
        self._loop_depth -= 1

    def _check_range_len(self, node: ast.For):
        # detect: for i in range(len(x))
        if (isinstance(node.iter, ast.Call) and getattr(node.iter.func, "id", "") == "range"
                and len(node.iter.args) == 1
                and isinstance(node.iter.args[0], ast.Call)
                and getattr(node.iter.args[0].func, "id", "") == "len"):
            self.issues.append(Issue(
                line=node.lineno,
                pattern="range_len",
                severity="low",
                detail="`range(len(x))` pattern — usually cleaner and slightly more efficient with `enumerate(x)`."
            ))

    def _check_growing_list_len_check(self, node: ast.While):
        # detect: while i < len(some_list): ... some_list.append(...)
        test_src = ast.dump(node.test)
        if "len" in test_src:
            for child in ast.walk(node):
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "append"):
                    self.issues.append(Issue(
                        line=node.lineno,
                        pattern="growing_list_len_check",
                        severity="medium",
                        detail="Loop condition re-checks `len()` on a list that grows inside the same loop — "
                               "recomputed on every iteration; consider a for-loop or precomputed bound."
                    ))
                    break

    # ---------- string concatenation in loop ----------
    def visit_AugAssign(self, node):
        is_simple_counter_increment = (
            isinstance(node.op, ast.Add)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, (int, float))
            and abs(node.value.value) <= 1
        )
        if self._loop_depth > 0 and isinstance(node.op, ast.Add) and not is_simple_counter_increment:
            self.issues.append(Issue(
                line=node.lineno,
                pattern="string_concat_in_loop",
                severity="medium",
                detail="`+=` accumulation inside a loop — if this builds a string, each += reallocates memory; "
                       "use `''.join(...)` or a list accumulator instead. (If this is numeric accumulation, "
                       "this pattern is fine — review the line to confirm which case applies.)"
            ))
        self.generic_visit(node)

    # ---------- pandas iterrows ----------
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "iterrows":
            self.issues.append(Issue(
                line=node.lineno,
                pattern="pandas_iterrows",
                severity="high",
                detail="`.iterrows()` iterates row-by-row in Python — orders of magnitude slower than a "
                       "vectorized pandas/numpy operation on the whole column."
            ))
        # detect sum(/any(/all( wrapping a list comprehension -> should be a generator
        if (isinstance(node.func, ast.Name) and node.func.id in ("sum", "any", "all", "max", "min")
                and len(node.args) == 1 and isinstance(node.args[0], ast.ListComp)):
            self.issues.append(Issue(
                line=node.lineno,
                pattern="list_for_reduction",
                severity="low",
                detail=f"`{node.func.id}([...])` builds a full list just to reduce it — "
                       f"a generator expression `{node.func.id}(...)` (no brackets) avoids the extra memory allocation."
            ))
        self.generic_visit(node)

    # ---------- unmemoized recursion ----------
    def visit_FunctionDef(self, node):
        has_cache_decorator = any(
            (isinstance(d, ast.Name) and d.id in ("lru_cache", "cache"))
            or (isinstance(d, ast.Call) and getattr(d.func, "id", "") == "lru_cache")
            or (isinstance(d, ast.Attribute) and d.attr in ("lru_cache", "cache"))
            for d in node.decorator_list
        )
        calls_self = any(
            isinstance(n, ast.Call) and getattr(n.func, "id", "") == node.name
            for n in ast.walk(node)
        )
        if calls_self and not has_cache_decorator:
            self.issues.append(Issue(
                line=node.lineno,
                pattern="unmemoized_recursion",
                severity="high",
                detail=f"`{node.name}()` calls itself recursively with no `@lru_cache`/memoization — "
                       f"likely recomputes overlapping subproblems exponentially (classic in naive Fibonacci-style code)."
            ))
        self.generic_visit(node)


def analyze_code(source_code: str) -> list[Issue]:
    tree = ast.parse(source_code)
    visitor = GreenCodeVisitor()
    visitor.visit(tree)
    return visitor.issues


if __name__ == "__main__":
    with open("sample_code/inefficient_example.py") as f:
        code = f.read()
    issues = analyze_code(code)
    print(f"Found {len(issues)} issues:\n")
    for issue in issues:
        print(f"  Line {issue.line} [{issue.severity.upper()}] {issue.pattern}: {issue.detail}")