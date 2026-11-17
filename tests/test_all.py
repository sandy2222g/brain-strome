import pytest
from fastapi.testclient import TestClient

from minisheet.api import app
from minisheet.core import Sheet, SheetError, cells_in_range, evaluate, sample, tokenize

c = TestClient(app)


def val(formula: str, **cells: str) -> object:
    return Sheet({"Z9": formula, **cells}).get("Z9")


def test_tokenizer():
    assert tokenize("A1+2.5*SUM(B1:B3)") == [("id", "A1"), ("op", "+"), ("num", "2.5"), ("op", "*"), ("id", "SUM"),
                                            ("op", "("), ("id", "B1"), ("op", ":"), ("id", "B3"), ("op", ")")]
    with pytest.raises(SheetError):
        tokenize("1 $ 2")


def test_precedence_and_associativity_by_hand():
    assert val("=2+3*4") == 14
    assert val("=(2+3)*4") == 20
    assert val("=10-4-3") == 3  # left associative
    assert val("=2^3^2") == 512  # right associative: 2^(3^2)
    assert val("=-2^2") == 4  # unary minus binds tighter, as in Excel
    assert val("=8/4/2") == 1


def test_cell_references_and_blank_cells():
    assert val("=A1*2+A2", A1="5", A2="1") == 11
    assert val("=B1+1") == 1  # blank counts as zero


def test_range_functions():
    cells = {"A1": "2", "A2": "4", "A3": "text", "A4": ""}
    assert val("=SUM(A1:A4)", **cells) == 6
    assert val("=AVG(A1:A4)", **cells) == 3  # text and blanks are skipped
    assert val("=MAX(A1:A2, 10)", **cells) == 10
    assert val("=MIN(A1:A2)", **cells) == 2
    assert val("=COUNT(A1:A4)", **cells) == 2
    assert val("=ROUND(2.567, 2)") == 2.57 and val("=ABS(-3)") == 3
    assert cells_in_range("B2", "A1") == ["A1", "B1", "A2", "B2"]  # corners in any order


def test_errors_and_propagation():
    assert val("=1/0") == "#DIV/0!"
    assert val("=1+") == "#SYNTAX"
    assert val("=FOO(1)") == "#NAME?"
    assert val("=A1+1", A1="hello") == "#VALUE!"
    assert val("=AVG(A1:A2)") == "#DIV/0!"
    s = Sheet({"A1": "=1/0", "A2": "=A1+5", "A3": "=SUM(A1:A2)"})
    assert s.get("A2") == "#DIV/0!" and s.get("A3") == "#DIV/0!"


def test_cycles_are_detected_everywhere_on_the_loop():
    r = evaluate({"A1": "=B1", "B1": "=A1+1", "C1": "=A1*2", "D1": "=D1"})["values"]
    assert r["A1"] == r["B1"] == r["C1"] == r["D1"] == "#CYCLE"


def test_dependency_order_puts_inputs_first():
    r = evaluate(sample())
    order = r["order"]
    assert order.index("B2") < order.index("E2") < order.index("E6") and order.index("B8") < order.index("B5")
    assert r["deps"]["E2"] == ["B2", "C2", "D2"]


def test_budget_sheet_by_hand():
    v = evaluate(sample())["values"]
    assert v["B5"] == 150 and v["E5"] == 465  # fun money is 10% of income
    assert v["E6"] == 2400 + 720 + 185 + 465  # total spent
    assert v["E7"] == 4650 - 3770 and round(v["F7"], 4) == round(880 / 4650, 4)


def test_edits_change_dependents():
    cells = sample() | {"B8": "2000"}
    assert evaluate(cells)["values"]["B7"] == 2000 - (800 + 220 + 60 + 200)


def test_validation():
    with pytest.raises(SheetError):
        Sheet({"AA1": "1"})
    with pytest.raises(SheetError):
        Sheet({f"{c}{i}": "1" for c in "ABCDEF" for i in range(1, 100)})  # 594 cells > 500 limit


def test_api():
    assert c.get("/health").json() == {"status": "ok"}
    s = c.get("/sample").json()["cells"]
    r = c.post("/evaluate", json={"cells": s}).json()
    assert r["values"]["E6"] == 3770
    assert c.post("/evaluate", json={"cells": {"ZZ": "1"}}).status_code == 422
    assert c.get("/").status_code == 200
