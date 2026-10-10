"""Packet builder and validator for Waste Intelligence Platform.

Provides validation and normalization of telemetry packets.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import Config

logger = logging.getLogger(__name__)


def validate_bin_packet(packet: dict) -> dict:
    """Validate and normalize a bin telemetry packet.
    
    Args:
        packet: Raw bin telemetry packet
        
    Returns:
        Validated and normalized bin packet
    """
    try:
        # Ensure required fields
        if "bin_id" not in packet:
            raise ValueError("Missing bin_id in bin packet")
        
        if "timestamp" not in packet:
            raise ValueError("Missing timestamp in bin packet")
        
        # Ensure sensors dict
        if "sensors" not in packet:
            packet["sensors"] = {}
        
        # Ensure location dict
        if "location" not in packet:
            packet["location"] = {}
        
        # Validate sensor values
        sensors = packet["sensors"]
        
        # Mass in kg (0-1000)
        if "mass_kg" in sensors:
            sensors["mass_kg"] = float(sensors["mass_kg"])
            if sensors["mass_kg"] < 0:
                sensors["mass_kg"] = 0.0
            elif sensors["mass_kg"] > 1000:
                logger.warning(f"High mass value: {sensors['mass_kg']} kg")
        else:
            sensors["mass_kg"] = 0.0
        
        # Fill level percentage (0-100)
        if "filllevelpct" in sensors:
            sensors["filllevelpct"] = float(sensors["filllevelpct"])
            if sensors["filllevelpct"] < 0:
                sensors["filllevelpct"] = 0.0
            elif sensors["filllevelpct"] > 100:
                sensors["filllevelpct"] = 100.0
        else:
            sensors["filllevelpct"] = 0.0
        
        # Gas in ppm (0-100)
        if "gas_ppm" in sensors:
            sensors["gas_ppm"] = float(sensors["gas_ppm"])
            if sensors["gas_ppm"] < 0:
                sensors["gas_ppm"] = 0.0
        else:
            sensors["gas_ppm"] = 0.0
        
        # Temperature in Celsius
        if "temperature_c" in sensors:
            sensors["temperature_c"] = float(sensors["temperature_c"])
        else:
            sensors["temperature_c"] = None
        
        # Battery percentage (0-100)
        if "battery_pct" in sensors:
            sensors["battery_pct"] = float(sensors["battery_pct"])
            if sensors["battery_pct"] < 0:
                sensors["battery_pct"] = 0.0
            elif sensors["battery_pct"] > 100:
                sensors["battery_pct"] = 100.0
        else:
            sensors["battery_pct"] = None
        
        # Validate location
        location = packet["location"]
        
        if "borough_id" not in location:
            location["borough_id"] = "Unknown"
        
        if "block_id" not in location:
            location["block_id"] = "Unknown"
        
        # Add coordinates if available
        if "latitude" not in location:
            location["latitude"] = None
        else:
            location["latitude"] = float(location["latitude"])
        
        if "longitude" not in location:
            location["longitude"] = None
        else:
            location["longitude"] = float(location["longitude"])
        
        # Add facility metadata if available
        if "facility_id" not in packet:
            packet["facility_id"] = None
        
        return packet
        
    except Exception as e:
        logger.error(f"Validation failed for bin packet: {e}")
        # Return minimal valid packet
        return {
            "bin_id": packet.get("bin_id", "unknown"),
            "timestamp": packet.get("timestamp", ""),
            "sensors": {
                "mass_kg": 0.0,
                "filllevelpct": 0.0,
                "gas_ppm": 0.0,
            },
            "location": {
                "borough_id": "Unknown",
                "block_id": "Unknown",
            },
        }


def validate_cluster_packet(packet: dict) -> dict:
    """Validate and normalize a cluster telemetry packet.
    
    Args:
        packet: Raw cluster telemetry packet
        
    Returns:
        Validated and normalized cluster packet
    """
    try:
        # Ensure required fields
        if "cluster_id" not in packet:
            raise ValueError("Missing cluster_id in cluster packet")
        
        if "timestamp" not in packet:
            raise ValueError("Missing timestamp in cluster packet")
        
        # Ensure aggregated dict
        if "aggregated" not in packet:
            packet["aggregated"] = {}
        
        # Validate aggregated values
        aggregated = packet["aggregated"]
        
        # Total mass in kg
        if "total_mass_kg" in aggregated:
            aggregated["total_mass_kg"] = float(aggregated["total_mass_kg"])
            if aggregated["total_mass_kg"] < 0:
                aggregated["total_mass_kg"] = 0.0
        else:
            aggregated["total_mass_kg"] = 0.0
        
        # Average fill level percentage (0-100)
        if "avg_filllevelpct" in aggregated:
            aggregated["avg_filllevelpct"] = float(aggregated["avg_filllevelpct"])
            if aggregated["avg_filllevelpct"] < 0:
                aggregated["avg_filllevelpct"] = 0.0
            elif aggregated["avg_filllevelpct"] > 100:
                aggregated["avg_filllevelpct"] = 100.0
        else:
            aggregated["avg_filllevelpct"] = 0.0
        
        # Max fill level percentage (0-100)
        if "max_filllevelpct" in aggregated:
            aggregated["max_filllevelpct"] = float(aggregated["max_filllevelpct"])
            if aggregated["max_filllevelpct"] < 0:
                aggregated["max_filllevelpct"] = 0.0
            elif aggregated["max_filllevelpct"] > 100:
                aggregated["max_filllevelpct"] = 100.0
        else:
            aggregated["max_filllevelpct"] = 0.0
        
        # Bin count
        if "bin_count" in aggregated:
            aggregated["bin_count"] = int(aggregated["bin_count"])
            if aggregated["bin_count"] < 0:
                aggregated["bin_count"] = 0
        else:
            aggregated["bin_count"] = 0
        
        # Bins near full
        if "bins_near_full" in aggregated:
            aggregated["bins_near_full"] = int(aggregated["bins_near_full"])
            if aggregated["bins_near_full"] < 0:
                aggregated["bins_near_full"] = 0
        else:
            aggregated["bins_near_full"] = 0
        
        # Average gas in ppm
        if "avg_gas_ppm" in aggregated:
            aggregated["avg_gas_ppm"] = float(aggregated["avg_gas_ppm"])
            if aggregated["avg_gas_ppm"] < 0:
                aggregated["avg_gas_ppm"] = 0.0
        else:
            aggregated["avg_gas_ppm"] = 0.0
        
        # Average temperature in Celsius
        if "avg_temperature_c" in aggregated:
            aggregated["avg_temperature_c"] = float(aggregated["avg_temperature_c"])
        else:
            aggregated["avg_temperature_c"] = None
        
        # Add location if available
        if "location" not in packet:
            packet["location"] = {}
        
        # Add facility metadata if available
        if "facility_id" not in packet:
            packet["facility_id"] = None
        
        return packet
        
    except Exception as e:
        logger.error(f"Validation failed for cluster packet: {e}")
        # Return minimal valid packet
        return {
            "cluster_id": packet.get("cluster_id", "unknown"),
            "timestamp": packet.get("timestamp", ""),
            "aggregated": {
                "total_mass_kg": 0.0,
                "avg_filllevelpct": 0.0,
                "max_filllevelpct": 0.0,
                "bin_count": 0,
                "bins_near_full": 0,
                "avg_gas_ppm": 0.0,
            },
        }


def validate_facility_packet(packet: dict) -> dict:
    """Validate and normalize a facility telemetry packet.
    
    Args:
        packet: Raw facility telemetry packet
        
    Returns:
        Validated and normalized facility packet
    """
    try:
        # Ensure required fields
        if "facility_id" not in packet:
            raise ValueError("Missing facility_id in facility packet")
        
        if "timestamp" not in packet:
            raise ValueError("Missing timestamp in facility packet")
        
        # Ensure load dict
        if "load" not in packet:
            packet["load"] = {}
        
        # Ensure forecast dict
        if "forecast" not in packet:
            packet["forecast"] = {}
        
        # Add facility name from metadata if available
        if "facility_name" not in packet:
            facility_id = packet.get("facility_id", "")
            if facility_id in Config.FACILITY_METADATA:
                packet["facility_name"] = Config.FACILITY_METADATA[facility_id]["name"]
            else:
                packet["facility_name"] = f"Facility {facility_id}"
        
        # Validate load values
        load = packet["load"]
        
        # Inbound mass in kg
        if "inbound_mass_kg" in load:
            load["inbound_mass_kg"] = float(load["inbound_mass_kg"])
            if load["inbound_mass_kg"] < 0:
                load["inbound_mass_kg"] = 0.0
        else:
            load["inbound_mass_kg"] = 0.0
        
        # Outbound mass in kg
        if "outbound_mass_kg" in load:
            load["outbound_mass_kg"] = float(load["outbound_mass_kg"])
            if load["outbound_mass_kg"] < 0:
                load["outbound_mass_kg"] = 0.0
        else:
            load["outbound_mass_kg"] = 0.0
        
        # Capacity used percentage (0-100)
        if "capacity_used_pct" in load:
            load["capacity_used_pct"] = float(load["capacity_used_pct"])
            if load["capacity_used_pct"] < 0:
                load["capacity_used_pct"] = 0.0
            elif load["capacity_used_pct"] > 100:
                load["capacity_used_pct"] = 100.0
        else:
            load["capacity_used_pct"] = 0.0
        
        # Current throughput in kg/hour
        if "current_throughput_kg_per_hour" in load:
            load["current_throughput_kg_per_hour"] = float(load["current_throughput_kg_per_hour"])
            if load["current_throughput_kg_per_hour"] < 0:
                load["current_throughput_kg_per_hour"] = 0.0
        else:
            load["current_throughput_kg_per_hour"] = 0.0
        
        # Validate forecast values
        forecast = packet["forecast"]
        
        # Predicted inbound mass in kg
        if "predicted_inbound_kg" in forecast:
            forecast["predicted_inbound_kg"] = float(forecast["predicted_inbound_kg"])
            if forecast["predicted_inbound_kg"] < 0:
                forecast["predicted_inbound_kg"] = 0.0
        else:
            forecast["predicted_inbound_kg"] = 0.0
        
        # Predicted outbound mass in kg
        if "predicted_outbound_kg" in forecast:
            forecast["predicted_outbound_kg"] = float(forecast["predicted_outbound_kg"])
            if forecast["predicted_outbound_kg"] < 0:
                forecast["predicted_outbound_kg"] = 0.0
        else:
            forecast["predicted_outbound_kg"] = 0.0
        
        # Predicted capacity percentage (0-100)
        if "predicted_capacity_pct" in forecast:
            forecast["predicted_capacity_pct"] = float(forecast["predicted_capacity_pct"])
            if forecast["predicted_capacity_pct"] < 0:
                forecast["predicted_capacity_pct"] = 0.0
            elif forecast["predicted_capacity_pct"] > 100:
                forecast["predicted_capacity_pct"] = 100.0
        else:
            forecast["predicted_capacity_pct"] = 0.0
        
        # Add location if available
        if "location" not in packet:
            packet["location"] = {}
        
        return packet
        
    except Exception as e:
        logger.error(f"Validation failed for facility packet: {e}")
        # Return minimal valid packet
        return {
            "facility_id": packet.get("facility_id", "unknown"),
            "facility_name": packet.get("facility_name", "Unknown Facility"),
            "timestamp": packet.get("timestamp", ""),
            "load": {
                "inbound_mass_kg": 0.0,
                "outbound_mass_kg": 0.0,
                "capacity_used_pct": 0.0,
                "current_throughput_kg_per_hour": 0.0,
            },
            "forecast": {
                "predicted_inbound_kg": 0.0,
                "predicted_outbound_kg": 0.0,
                "predicted_capacity_pct": 0.0,
            },
        }
