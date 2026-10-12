"""Tests for hub-layer data models."""

from hub_layer.api.models.bin import Bin
from hub_layer.api.models.facility import Facility


def test_bin_model():
    bin_obj = Bin(
        bin_id="bin-001",
        cluster_id="cluster-01",
        facility_id="facility-01",
        latitude=40.7128,
        longitude=-74.0060,
        fill_level_percent=50.0,
        mass_kg=25.0,
    )
    assert bin_obj.bin_id == "bin-001"
    assert bin_obj.fill_level_percent == 50.0
    dict_repr = bin_obj.to_dict()
    assert dict_repr["bin_id"] == "bin-001"


def test_facility_model():
    facility = Facility(
        facility_id="comp-01",
        name="Composting Facility 1",
        latitude=40.7400,
        longitude=-73.9800,
        facility_type="composting",
        capacity_kg=5000.0,
        current_load_kg=2500.0,
    )
    assert facility.facility_id == "comp-01"
    dict_repr = facility.to_dict()
    assert dict_repr["utilization_percent"] == 50.0
