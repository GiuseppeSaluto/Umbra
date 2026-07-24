import os

from db.seed_comuni import _parse_row, load_comuni

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures", "sample_istat_comuni.csv")


def test_parse_row_extracts_expected_fields():
    # Real ISTAT row for Agliè (Torino, Piemonte).
    row = [
        "01",
        "201",
        "001",
        "001",
        "001001",
        "Agliè",
        "Agliè",
        "",
        "1",
        "Nord-ovest",
        "Piemonte",
        "Torino",
        "3",
        "0",
        "TO",
        "1001",
    ]
    assert _parse_row(row) == {
        "istat_code": "001001",
        "name": "Agliè",
        "province": "Torino",
        "province_abbr": "TO",
        "region": "Piemonte",
    }


def test_load_comuni_upserts_every_row(mock_mongo):
    count = load_comuni(SAMPLE_CSV_PATH)

    assert count == 3
    assert mock_mongo.update_one.call_count == 3


def test_load_comuni_upserts_keyed_by_istat_code(mock_mongo):
    load_comuni(SAMPLE_CSV_PATH)

    first_call_filter, first_call_update = mock_mongo.update_one.call_args_list[0][0]
    assert first_call_filter == {"istat_code": "001001"}
    assert first_call_update["$set"]["name"] == "Agliè"


def test_load_comuni_creates_a_unique_index_on_istat_code(mock_mongo):
    load_comuni(SAMPLE_CSV_PATH)

    mock_mongo.create_index.assert_called_once_with("istat_code", unique=True)
