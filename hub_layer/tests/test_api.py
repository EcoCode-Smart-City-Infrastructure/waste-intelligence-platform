"""Tests for hub-layer API endpoints."""

import pytest
from hub_layer.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_list_bins(client):
    response = client.get("/bins")
    assert response.status_code == 200


def test_create_bin(client):
    response = client.post("/bins", json={"bin_id": "test-bin-001"})
    assert response.status_code == 201
