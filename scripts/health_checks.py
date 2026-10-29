"""Service health checks for WIN OS.

This script provides comprehensive health checking for all WIN OS services.

Usage:
    python scripts/health_checks.py [--service SERVICE_NAME] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import psycopg2
from psycopg2 import OperationalError


# ============================================================================
# Configuration
# ============================================================================

# Default service endpoints
SERVICE_ENDPOINTS = {
    "hub-layer": "http://localhost:5000/health",
    "api": "http://localhost:8000/health",
    "control-center": "http://localhost:8001/health",
    "analytics": "http://localhost:8002/health",
    "copilot": "http://localhost:8004/health",
    "mqtt-bridge": "http://localhost:8005/health",
}

# Database configuration
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "waste",
    "user": "postgres",
    "password": "postgres",
}

# Health check thresholds
THRESHOLDS = {
    "response_time_ms": 5000,  # 5 seconds
    "database_connection": 10,  # 10 seconds
}


# ============================================================================
# Health Check Classes
# ============================================================================

class HealthCheckResult:
    """Represents the result of a health check."""

    def __init__(
        self,
        service: str,
        status: str,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: float = 0.0,
    ):
        self.service = service
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "response_time_ms": round(self.response_time_ms, 2),
            "timestamp": self.timestamp,
        }

    def is_healthy(self) -> bool:
        return self.status in ["healthy", "ok", "up"]


class ServiceHealthChecker:
    """Check the health of HTTP services."""

    def __init__(self, endpoints: Optional[Dict[str, str]] = None):
        self.endpoints = endpoints or SERVICE_ENDPOINTS

    async def check_service(self, service_name: str, endpoint: str) -> HealthCheckResult:
        """Check a single service endpoint."""
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=THRESHOLDS["response_time_ms"] / 1000) as client:
                response = await client.get(endpoint)
                response_time_ms = (time.time() - start_time) * 1000

                if response.status_code >= 200 and response.status_code < 300:
                    try:
                        data = response.json()
                        status = data.get("status", "healthy")
                        message = data.get("message", "Service is healthy")
                        details = data.get("details", {})
                    except Exception:
                        status = "healthy"
                        message = "Service responded with success"
                        details = {}

                    return HealthCheckResult(
                        service=service_name,
                        status=status,
                        message=message,
                        details=details,
                        response_time_ms=response_time_ms,
                    )
                else:
                    return HealthCheckResult(
                        service=service_name,
                        status="unhealthy",
                        message=f"HTTP {response.status_code}: {response.text[:100]}",
                        response_time_ms=response_time_ms,
                    )

        except httpx.TimeoutException:
            return HealthCheckResult(
                service=service_name,
                status="timeout",
                message=f"Request timed out after {THRESHOLDS['response_time_ms']}ms",
                response_time_ms=THRESHOLDS["response_time_ms"],
            )
        except httpx.ConnectError:
            return HealthCheckResult(
                service=service_name,
                status="unreachable",
                message="Could not connect to service",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                service=service_name,
                status="error",
                message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def check_all(self) -> List[HealthCheckResult]:
        """Check all registered services."""
        results = []
        for service_name, endpoint in self.endpoints.items():
            result = await self.check_service(service_name, endpoint)
            results.append(result)
        return results


class DatabaseHealthChecker:
    """Check the health of the PostgreSQL database."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DATABASE_CONFIG

    def check_connection(self) -> HealthCheckResult:
        """Check database connection."""
        start_time = time.time()

        try:
            # Build connection string
            dsn = (
                f"host={self.config['host']} "
                f"port={self.config['port']} "
                f"dbname={self.config['database']} "
                f"user={self.config['user']} "
                f"password={self.config['password']}"
            )

            # Test connection
            conn = psycopg2.connect(dsn)
            conn.close()

            response_time_ms = (time.time() - start_time) * 1000

            return HealthCheckResult(
                service="postgresql",
                status="healthy",
                message="Database connection successful",
                details={
                    "host": self.config["host"],
                    "port": self.config["port"],
                    "database": self.config["database"],
                },
                response_time_ms=response_time_ms,
            )

        except OperationalError as e:
            return HealthCheckResult(
                service="postgresql",
                status="unhealthy",
                message=f"Database connection failed: {e}",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return HealthCheckResult(
                service="postgresql",
                status="error",
                message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    def check_tables(self) -> HealthCheckResult:
        """Check that required tables exist."""
        start_time = time.time()

        required_tables = [
            "organizations",
            "tenants",
            "users",
            "assets",
            "bins",
            "facilities",
            "routes",
            "telemetry",
            "collection_events",
        ]

        try:
            dsn = (
                f"host={self.config['host']} "
                f"port={self.config['port']} "
                f"dbname={self.config['database']} "
                f"user={self.config['user']} "
                f"password={self.config['password']}"
            )

            conn = psycopg2.connect(dsn)
            cursor = conn.cursor()

            # Check for each table
            missing_tables = []
            for table in required_tables:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table,),
                )
                if not cursor.fetchone()[0]:
                    missing_tables.append(table)

            cursor.close()
            conn.close()

            response_time_ms = (time.time() - start_time) * 1000

            if missing_tables:
                return HealthCheckResult(
                    service="postgresql-tables",
                    status="degraded",
                    message=f"Missing tables: {', '.join(missing_tables)}",
                    details={"missing_tables": missing_tables},
                    response_time_ms=response_time_ms,
                )
            else:
                return HealthCheckResult(
                    service="postgresql-tables",
                    status="healthy",
                    message=f"All {len(required_tables)} required tables exist",
                    details={"checked_tables": required_tables},
                    response_time_ms=response_time_ms,
                )

        except Exception as e:
            return HealthCheckResult(
                service="postgresql-tables",
                status="error",
                message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    def check_extensions(self) -> HealthCheckResult:
        """Check that required PostgreSQL extensions are installed."""
        start_time = time.time()

        required_extensions = ["postgis", "timescaledb", "uuid-ossp"]

        try:
            dsn = (
                f"host={self.config['host']} "
                f"port={self.config['port']} "
                f"dbname={self.config['database']} "
                f"user={self.config['user']} "
                f"password={self.config['password']}"
            )

            conn = psycopg2.connect(dsn)
            cursor = conn.cursor()

            # Check for each extension
            missing_extensions = []
            for ext in required_extensions:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = %s)",
                    (ext,),
                )
                if not cursor.fetchone()[0]:
                    missing_extensions.append(ext)

            cursor.close()
            conn.close()

            response_time_ms = (time.time() - start_time) * 1000

            if missing_extensions:
                return HealthCheckResult(
                    service="postgresql-extensions",
                    status="degraded",
                    message=f"Missing extensions: {', '.join(missing_extensions)}",
                    details={"missing_extensions": missing_extensions},
                    response_time_ms=response_time_ms,
                )
            else:
                return HealthCheckResult(
                    service="postgresql-extensions",
                    status="healthy",
                    message=f"All {len(required_extensions)} required extensions installed",
                    details={"checked_extensions": required_extensions},
                    response_time_ms=response_time_ms,
                )

        except Exception as e:
            return HealthCheckResult(
                service="postgresql-extensions",
                status="error",
                message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )


class SystemHealthChecker:
    """Check overall system health."""

    def __init__(
        self,
        service_endpoints: Optional[Dict[str, str]] = None,
        db_config: Optional[Dict[str, Any]] = None,
    ):
        self.service_checker = ServiceHealthChecker(service_endpoints)
        self.db_checker = DatabaseHealthChecker(db_config)

    async def check_all(self) -> Dict[str, Any]:
        """Perform all health checks."""
        results = {}

        # Check services
        service_results = await self.service_checker.check_all()
        for result in service_results:
            results[result.service] = result.to_dict()

        # Check database
        db_connection = self.db_checker.check_connection()
        results[db_connection.service] = db_connection.to_dict()

        db_tables = self.db_checker.check_tables()
        results[db_tables.service] = db_tables.to_dict()

        db_extensions = self.db_checker.check_extensions()
        results[db_extensions.service] = db_extensions.to_dict()

        # Calculate overall status
        all_healthy = all(r.is_healthy() for r in service_results)
        db_healthy = db_connection.is_healthy() and db_tables.is_healthy()

        if all_healthy and db_healthy:
            overall_status = "healthy"
        elif any(r.status == "unhealthy" or r.status == "error" for r in service_results) or not db_healthy:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": results,
            "summary": {
                "total_services": len(service_results) + 3,  # +3 for db checks
                "healthy": sum(1 for r in service_results if r.is_healthy()) + (2 if db_healthy else 0),
                "degraded": sum(1 for r in service_results if r.status == "degraded"),
                "unhealthy": sum(1 for r in service_results if not r.is_healthy() and r.status != "degraded") + (3 - (2 if db_healthy else 0)),
            },
        }


# ============================================================================
# Main
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="WIN OS Health Checks")
    parser.add_argument(
        "--service",
        default=None,
        help="Check specific service (default: check all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--db-host",
        default=None,
        help="Database host",
    )
    parser.add_argument(
        "--db-port",
        type=int,
        default=None,
        help="Database port",
    )
    parser.add_argument(
        "--db-name",
        default=None,
        help="Database name",
    )
    parser.add_argument(
        "--db-user",
        default=None,
        help="Database user",
    )
    parser.add_argument(
        "--db-password",
        default=None,
        help="Database password",
    )
    args = parser.parse_args()

    # Update database config if provided
    db_config = DATABASE_CONFIG.copy()
    if args.db_host:
        db_config["host"] = args.db_host
    if args.db_port:
        db_config["port"] = args.db_port
    if args.db_name:
        db_config["database"] = args.db_name
    if args.db_user:
        db_config["user"] = args.db_user
    if args.db_password:
        db_config["password"] = args.db_password

    # Create checkers
    service_checker = ServiceHealthChecker()
    db_checker = DatabaseHealthChecker(db_config)

    # Run checks
    if args.service:
        # Check specific service
        if args.service == "postgresql":
            result = db_checker.check_connection()
            results = [result]
        elif args.service == "postgresql-tables":
            result = db_checker.check_tables()
            results = [result]
        elif args.service == "postgresql-extensions":
            result = db_checker.check_extensions()
            results = [result]
        else:
            result = await service_checker.check_service(args.service, SERVICE_ENDPOINTS.get(args.service, args.service))
            results = [result]
    else:
        # Check all services
        service_results = await service_checker.check_all()
        db_connection = db_checker.check_connection()
        db_tables = db_checker.check_tables()
        db_extensions = db_checker.check_extensions()
        results = service_results + [db_connection, db_tables, db_extensions]

    # Output results
    if args.json:
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": [r.to_dict() for r in results],
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 60)
        print("WIN OS - Service Health Checks")
        print("=" * 60)
        print()

        all_healthy = all(r.is_healthy() for r in results)
        any_unhealthy = any(r.status in ["unhealthy", "error", "timeout", "unreachable"] for r in results)

        if all_healthy:
            print("Status: HEALTHY")
        elif any_unhealthy:
            print("Status: UNHEALTHY")
        else:
            print("Status: DEGRADED")

        print()

        for result in results:
            status_indicator = "✓" if result.is_healthy() else "✗"
            print(f"{status_indicator} {result.service:25s} [{result.status:12s}] {result.message}")
            
            if args.verbose and result.details:
                for key, value in result.details.items():
                    print(f"    {key}: {value}")
                print(f"    Response time: {result.response_time_ms:.2f}ms")
            print()

        # Summary
        healthy_count = sum(1 for r in results if r.is_healthy())
        print(f"Summary: {healthy_count}/{len(results)} services healthy")

    return 0


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
