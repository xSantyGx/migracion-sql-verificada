from decimal import Decimal, localcontext
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


def test_decimal_differences_beyond_context_precision_are_not_hidden():
    source = result([[Decimal("1000")]])
    target = result([[Decimal("1000.0000000000000000000000000001")]])
    assert compare(source, target)


def test_number_normalization_preserves_digits_independently_of_context():
    with localcontext() as context:
        context.prec = 6
        assert normalize(Decimal("123456789012345678901234567890.123400")) == {
            "number": "123456789012345678901234567890.1234"
        }
        assert normalize(123456789012345678901234567890) == {
            "number": "123456789012345678901234567890"
        }
        assert normalize(Decimal("1E+3")) == normalize(Decimal("1000.0000"))
        assert normalize(Decimal("-0.000")) == normalize(0)


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
