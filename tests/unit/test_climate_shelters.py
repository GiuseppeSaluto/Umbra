from db.climate_shelters import ClimateShelterCatalog


def _add_sample(catalog, name="Biblioteca Comunale", source_id="biblioteche:1"):
    catalog.add(
        istat_code="048017",
        source_id=source_id,
        comune="Firenze",
        name=name,
        lat=43.7696,
        lon=11.2558,
        source_url="https://opendata.comune.fi.it/content/rifugi-climatici",
        shelter_type="library",
        free_access=True,
        has_air_conditioning=True,
        has_drinking_water=True,
        has_seating=True,
    )


def test_catalog_starts_empty():
    catalog = ClimateShelterCatalog()
    assert len(catalog) == 0


def test_add_appends_a_normalized_record():
    catalog = ClimateShelterCatalog()
    _add_sample(catalog)
    assert len(catalog) == 1


def test_add_leaves_unspecified_fields_as_none_not_false():
    catalog = ClimateShelterCatalog()
    catalog.add(
        istat_code="048017",
        source_id="aree_fresche:00100",
        comune="Firenze",
        name="Parco delle Cascine",
        lat=43.7796,
        lon=11.2258,
        source_url="https://opendata.comune.fi.it/content/rifugi-climatici",
    )
    record = catalog._records[0]
    assert record["free_access"] is None
    assert record["has_air_conditioning"] is None
    assert record["shade_coverage_pct"] is None


def test_save_upserts_each_record_keyed_by_istat_code_and_source_id(mock_mongo):
    catalog = ClimateShelterCatalog()
    _add_sample(catalog, name="Giardino di via Toscanini", source_id="aree_fresche:02394")
    _add_sample(catalog, name="Giardino di via Toscanini", source_id="aree_fresche:05409")

    count = catalog.save()

    assert count == 2
    assert mock_mongo.update_one.call_count == 2
    first_filter = mock_mongo.update_one.call_args_list[0][0][0]
    assert first_filter == {"istat_code": "048017", "source_id": "aree_fresche:02394"}


def test_save_stores_location_as_geojson_point(mock_mongo):
    catalog = ClimateShelterCatalog()
    _add_sample(catalog)

    catalog.save()

    update_doc = mock_mongo.update_one.call_args_list[0][0][1]
    assert update_doc["$set"]["location"] == {"type": "Point", "coordinates": [11.2558, 43.7696]}


def test_save_creates_a_unique_index_on_istat_code_and_source_id(mock_mongo):
    catalog = ClimateShelterCatalog()
    _add_sample(catalog)

    catalog.save()

    mock_mongo.create_index.assert_called_once_with([("istat_code", 1), ("source_id", 1)], unique=True)
