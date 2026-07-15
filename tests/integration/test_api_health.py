from unittest.mock import patch

from pymongo.errors import PyMongoError

from api.services.health_service import check_mongo_connectivity


# ----------------------------------------------------------------
# api/services/health_service.py
# ----------------------------------------------------------------

def test_check_mongo_connectivity_true_when_reachable(mock_mongo):
    assert check_mongo_connectivity() is True


def test_check_mongo_connectivity_false_when_not_connected():
    with patch("db.mongo.get_collection", side_effect=RuntimeError("not connected")):
        assert check_mongo_connectivity() is False


def test_check_mongo_connectivity_false_on_pymongo_error():
    with patch("db.mongo.get_collection", side_effect=PyMongoError("boom")):
        assert check_mongo_connectivity() is False


# ----------------------------------------------------------------
# GET /health
# ----------------------------------------------------------------

def test_health_endpoint_ok_when_mongo_reachable(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "mongo": "connected"}


def test_health_endpoint_503_when_mongo_unreachable(app, mock_sentinel):
    with patch("db.mongo.get_collection", side_effect=RuntimeError("not connected")):
        response = app.test_client().get("/health")
        assert response.status_code == 503
        assert response.get_json() == {"status": "error", "mongo": "unreachable"}
