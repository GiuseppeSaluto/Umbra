import pytest

from api.routes._params import parse_float


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("44.6471", 44.6471),
        ("44,6471", 44.6471),
        (" 44.6471 ", 44.6471),
        ("-3.98", -3.98),
        ("500", 500.0),
    ],
)
def test_parse_float_accepts_comma_and_whitespace(raw, expected):
    assert parse_float(raw) == pytest.approx(expected)


def test_parse_float_rejects_garbage():
    with pytest.raises(ValueError):
        parse_float("not-a-number")
