"""A small spreadsheet: tokenizer, recursive-descent parser, memoised evaluation, cycle detection."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "budget.json"
CELL = re.compile(r"^([A-Z])([1-9][0-9]?)$")
TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|([A-Za-z][A-Za-z0-9]*)|(.))")
MAX_CELLS = 500
Value = float | str


class SheetError(Exception):
    """A spreadsheet error such as #DIV/0!; `code` is what the cell displays."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def tokenize(src: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(src.rstrip()):
        m = TOKEN.match(src, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1) is not None:
            out.append(("num", m.group(1)))
        elif m.group(2) is not None:
            out.append(("id", m.group(2).upper()))
        elif m.group(3) in "+-*/^(),:":
            out.append(("op", m.group(3)))
        else:
            raise SheetError("#SYNTAX")
    return out


def cells_in_range(a: str, b: str) -> list[str]:
    ma, mb = CELL.match(a), CELL.match(b)
    if not ma or not mb:
        raise SheetError("#REF!")
    c1, c2 = sorted((ma.group(1), mb.group(1)))
    r1, r2 = sorted((int(ma.group(2)), int(mb.group(2))))
    return [f"{chr(c)}{r}" for r in range(r1, r2 + 1) for c in range(ord(c1), ord(c2) + 1)]


class Sheet:
    def __init__(self, raw: dict[str, str]) -> None:
        if len(raw) > MAX_CELLS:
            raise SheetError("#TOOBIG")
        for k in raw:
            if not CELL.match(k):
                raise SheetError("#REF!")
        self.raw = {k: str(v) for k, v in raw.items()}
        self.cache: dict[str, Value] = {}
        self.stack: list[str] = []
        self.deps: dict[str, set[str]] = {}

    # ----- evaluation -----
    def get(self, ref: str) -> Value:
        if not CELL.match(ref):
            raise SheetError("#REF!")
        if ref in self.cache:
            return self.cache[ref]
        if ref in self.stack:
            raise SheetError("#CYCLE")
        text = self.raw.get(ref, "").strip()
        if not text.startswith("="):
            val: Value = self.literal(text)
            self.cache[ref] = val
            return val
        self.stack.append(ref)
        self.deps[ref] = set()
        try:
            val = Parser(self, ref, tokenize(text[1:])).run()
        except SheetError as e:
            val = e.code
        finally:
            self.stack.pop()
        if val == "#CYCLE" and self.stack:  # the error must reach every cell on the loop
            raise SheetError("#CYCLE")
        self.cache[ref] = val
        return val

    @staticmethod
    def literal(text: str) -> Value:
        if text == "":
            return ""
        try:
            return float(text)
        except ValueError:
            return text

    def number(self, ref: str) -> float:
        v = self.get(ref)
        if isinstance(v, str):
            if v == "":
                return 0.0
            raise SheetError(v if v.startswith("#") else "#VALUE!")
        return v

    def evaluate_all(self) -> dict[str, Value]:
        return {ref: self.get(ref) for ref in sorted(self.raw, key=lambda r: (int(r[1:]), r[0]))}

    def order(self) -> list[str]:
        """Cells in a safe calculation order (dependencies first)."""
        self.evaluate_all()
        seen: set[str] = set()
        out: list[str] = []

        def visit(r: str) -> None:
            if r in seen:
                return
            seen.add(r)
            for d in sorted(self.deps.get(r, ())):
                visit(d)
            out.append(r)

        for r in sorted(self.raw, key=lambda r: (int(r[1:]), r[0])):
            visit(r)
        return out


class Parser:
    def __init__(self, sheet: Sheet, me: str, toks: list[tuple[str, str]]) -> None:
        self.s, self.me, self.t, self.i = sheet, me, toks, 0

    def peek(self) -> tuple[str, str] | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, op: str) -> bool:
        p = self.peek()
        if p and p == ("op", op):
            self.i += 1
            return True
        return False

    def run(self) -> float:
        if not self.t:
            raise SheetError("#SYNTAX")
        v = self.expr()
        if self.peek() is not None:
            raise SheetError("#SYNTAX")
        return v

    def expr(self) -> float:
        v = self.term()
        while True:
            if self.take("+"):
                v += self.term()
            elif self.take("-"):
                v -= self.term()
            else:
                return v

    def term(self) -> float:
        v = self.power()
        while True:
            if self.take("*"):
                v *= self.power()
            elif self.take("/"):
                d = self.power()
                if d == 0:
                    raise SheetError("#DIV/0!")
                v /= d
            else:
                return v

    def power(self) -> float:
        base = self.unary()
        if self.take("^"):
            try:
                return float(base ** self.power())
            except (OverflowError, ZeroDivisionError, ValueError) as e:
                raise SheetError("#NUM!") from e
        return base

    def unary(self) -> float:
        if self.take("-"):
            return -self.unary()
        if self.take("+"):
            return self.unary()
        return self.primary()

    def ref(self, name: str) -> float:
        self.s.deps[self.me].add(name)
        return self.s.number(name)

    def primary(self) -> float:
        p = self.peek()
        if p is None:
            raise SheetError("#SYNTAX")
        self.i += 1
        kind, text = p
        if kind == "num":
            return float(text)
        if kind == "op" and text == "(":
            v = self.expr()
            if not self.take(")"):
                raise SheetError("#SYNTAX")
            return v
        if kind == "id":
            if self.take("("):
                return self.call(text)
            return self.ref(text)
        raise SheetError("#SYNTAX")

    def args(self) -> list[list[float]]:
        """Function arguments; a range contributes one list of numbers, an expression a single value."""
        out: list[list[float]] = []
        if self.take(")"):
            return out
        while True:
            start = self.i
            p = self.peek()
            nxt = self.t[start + 1] if start + 1 < len(self.t) else None
            if p and p[0] == "id" and nxt == ("op", ":"):
                self.i += 2
                q = self.peek()
                if not q or q[0] != "id":
                    raise SheetError("#SYNTAX")
                self.i += 1
                vals: list[float] = []
                for c in cells_in_range(p[1], q[1]):
                    self.s.deps[self.me].add(c)
                    v = self.s.get(c)
                    if isinstance(v, str) and v.startswith("#"):
                        raise SheetError(v)
                    if not isinstance(v, str):
                        vals.append(v)
                out.append(vals)
            else:
                out.append([self.expr()])
            if self.take(")"):
                return out
            if not self.take(","):
                raise SheetError("#SYNTAX")

    def call(self, name: str) -> float:
        a = self.args()
        flat = [x for grp in a for x in grp]
        if name == "SUM":
            return math.fsum(flat)
        if name == "COUNT":
            return float(len(flat))
        if name in ("AVG", "AVERAGE"):
            if not flat:
                raise SheetError("#DIV/0!")
            return math.fsum(flat) / len(flat)
        if name in ("MIN", "MAX"):
            if not flat:
                raise SheetError("#VALUE!")
            return min(flat) if name == "MIN" else max(flat)
        if name == "ABS" and len(flat) == 1:
            return abs(flat[0])
        if name == "ROUND" and len(a) == 2 and len(flat) == 2:
            return round(flat[0] + 0.0, int(flat[1]))
        raise SheetError("#NAME?")


def evaluate(raw: dict[str, str]) -> dict[str, object]:
    sheet = Sheet(raw)
    values = sheet.evaluate_all()
    return {"values": values, "order": sheet.order(), "deps": {k: sorted(v) for k, v in sheet.deps.items()}}


def sample() -> dict[str, str]:
    return json.loads(SAMPLE.read_text())  # type: ignore[no-any-return]
