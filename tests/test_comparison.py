from decimal import Decimal
from migrator.compare import normalize, compare


def result(rows, state=None, error=None):
    return {
        "columns": ["amount"],
        "rows": [[normalize(v) for v in row] for row in rows],
        "error": error,
        "state": state or {},
    }


def test_financial_precision_is_exact():
    assert compare(result([[Decimal("1.0050")]]), result([[Decimal("1.0051")]]))
    assert not compare(result([[Decimal("1.00")]]), result([[1]]))
    assert compare(result([[Decimal("1")]]), result([[1.0]]))


def test_null_and_text_are_never_normalized_away():
    for value in ["", "NULL", "abc ", "ABC"]:
        assert compare(result([[None]]), result([[value]]))
    assert compare(result([["abc"]]), result([["ABC"]]))
    assert compare(result([["abc"]]), result([["abc "]]))


def test_multiset_preserves_duplicates_and_order_contract():
    a = result([[1], [2], [1]])
    b = result([[2], [1], [1]])
    assert not compare(a, b)
    assert compare(a, b, ordered=True)
    assert compare(a, result([[1], [2]]))


def test_matching_result_cannot_hide_different_writes_or_errors():
    assert compare(result([[1]], {"payments": [[1]]}), result([[1]], {"payments": [[2]]}))
    assert compare(result([], error="INVALID_AMOUNT"), result([], error="TARGET_ERROR"))


def test_tds_empty_preamble_preserves_catch_result_without_hiding_real_sets():
    from migrator.db import tabular_result

    empty = {"columns": ["ratio", "error_code"], "rows": []}
    catch = {"columns": ["ratio", "error_code"], "rows": [[None, normalize("DIVISION_BY_ZERO")]]}
    assert tabular_result([empty, catch]) == catch
    assert tabular_result([catch, catch]) is None
    assert tabular_result([{"columns": ["different"], "rows": []}, catch]) is None
