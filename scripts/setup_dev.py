"""Development environment setup script for WIN OS.

This script automates the setup of the WIN OS development environment,
including database initialization, schema migration, and sample data seeding.

Usage:
    python scripts/setup_dev.py [--reset] [--seed] [--no-seed] [--tenant TENANT]

Options:
    --reset: Drop and recreate the database
    --seed: Seed the database with sample data (default: True)
    --no-seed: Don't seed the database
    --tenant: Specify tenant name for sample data (default: 'demo-tenant')
    --count: Number of sample records to create (default: 10)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from typing import Optional

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# ============================================================================
# Configuration
# ============================================================================

DEFAULT_TENANT = "demo-tenant"
DEFAULT_COUNT = 10

# Database configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "waste")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Schema files
SCHEMA_FILES = [
    "hub_layer/database/01_extensions_and_types.sql",
    "hub_layer/database/02_core_tables.sql",
    "hub_layer/database/03_operations_tables.sql",
    "hub_layer/database/04_environmental_tables.sql",
    "hub_layer/database/05_intelligence_tables.sql",
]


# ============================================================================
# Database Setup
# ============================================================================

class DatabaseSetup:
    """Handle database setup and initialization."""

    def __init__(self):
        self.connection = None
        self.dsn = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

    def connect(self, database: Optional[str] = None):
        """Create a database connection."""
        dsn = self.dsn
        if database:
            dsn = f"host={DB_HOST} port={DB_PORT} dbname={database} user={DB_USER} password={DB_PASSWORD}"
        
        try:
            conn = psycopg2.connect(dsn)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return None

    def database_exists(self, db_name: str) -> bool:
        """Check if a database exists."""
        try:
            # Connect to default postgres database
            conn = self.connect(database="postgres")
            if not conn:
                return False

            cursor = conn.cursor()
            cursor.execute(
                "SELECT EXISTS (SELECT FROM pg_database WHERE datname = %s)",
                (db_name,),
            )
            exists = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return exists
        except Exception:
            return False

    def create_database(self) -> bool:
        """Create the database if it doesn't exist."""
        if self.database_exists(DB_NAME):
            print(f"Database '{DB_NAME}' already exists")
            return True

        try:
            # Connect to default postgres database
            conn = self.connect(database="postgres")
            if not conn:
                return False

            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE {DB_NAME} WITH OWNER {DB_USER} ENCODING 'UTF8'"
            )
            cursor.close()
            conn.close()
            print(f"✓ Created database '{DB_NAME}'")
            return True
        except Exception as e:
            print(f"Error creating database: {e}")
            return False

    def drop_database(self) -> bool:
        """Drop the database."""
        try:
            # Connect to default postgres database
            conn = self.connect(database="postgres")
            if not conn:
                return False

            # Disconnect all existing connections
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity WHERE pg_stat_activity.datname = '{DB_NAME}'"
            )
            cursor.close()

            # Drop the database
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
            cursor.close()
            conn.close()
            print(f"✓ Dropped database '{DB_NAME}'")
            return True
        except Exception as e:
            print(f"Error dropping database: {e}")
            return False

    def execute_sql_file(self, file_path: str) -> bool:
        """Execute a SQL file."""
        try:
            conn = self.connect()
            if not conn:
                return False

            cursor = conn.cursor()

            # Read the SQL file
            with open(file_path, "r") as f:
                sql_content = f.read()

            # Split into individual statements
            statements = self.split_sql_statements(sql_content)

            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)

            cursor.close()
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error executing {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def split_sql_statements(self, sql: str) -> List[str]:
        """Split SQL content into individual statements."""
        statements = []
        current_statement = ""
        in_quotes = False
        quote_char = None

        for char in sql:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ";" and not in_quotes:
                if current_statement.strip():
                    statements.append(current_statement)
                current_statement = ""
            else:
                current_statement += char

        if current_statement.strip():
            statements.append(current_statement)

        return statements

    def initialize_schema(self) -> bool:
        """Initialize the database schema."""
        print("Initializing database schema...")

        for schema_file in SCHEMA_FILES:
            if not os.path.exists(schema_file):
                print(f"Warning: Schema file not found: {schema_file}")
                continue

            print(f"  Executing {schema_file}...")
            if self.execute_sql_file(schema_file):
                print(f"  ✓ {schema_file}")
            else:
                print(f"  ✗ Failed to execute {schema_file}")
                return False

        print("✓ Database schema initialized")
        return True

    def check_extensions(self) -> bool:
        """Check and install required PostgreSQL extensions."""
        required_extensions = ["postgis", "timescaledb", "uuid-ossp"]

        try:
            conn = self.connect()
            if not conn:
                return False

            cursor = conn.cursor()

            for ext in required_extensions:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM pg_extension WHERE extname = %s)",
                    (ext,),
                )
                if not cursor.fetchone()[0]:
                    print(f"  Installing extension: {ext}")
                    cursor.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
                    conn.commit()

            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error checking extensions: {e}")
            return False


# ============================================================================
# Sample Data Seeding
# ============================================================================

class DataSeeder:
    """Handle sample data seeding."""

    def seed_data(self, tenant: str = DEFAULT_TENANT, count: int = DEFAULT_COUNT):
        """Seed the database with sample data."""
        print(f"\nSeeding sample data for tenant '{tenant}'...")

        # Import and run the seed script
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "seed_data",
                "scripts/seed_data.py"
            )
            seed_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(seed_module)

            # Create database connection for seed
            db = seed_module.Database()
            generator = seed_module.SeedDataGenerator(db, tenant, count)
            generator.seed_all(clear=False)

            print("✓ Sample data seeded")
            return True
        except Exception as e:
            print(f"Error seeding data: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="WIN OS Development Environment Setup")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the database",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        default=True,
        help="Seed the database with sample data",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Don't seed the database",
    )
    parser.add_argument(
        "--tenant",
        default=DEFAULT_TENANT,
        help="Tenant name for sample data",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help="Number of sample records to create",
    )
    args = parser.parse_args()

    # Determine if we should seed
    should_seed = not args.no_seed and (args.seed or not (args.no_seed or args.seed))

    print("=" * 60)
    print("WIN OS - Development Environment Setup")
    print("=" * 60)
    print()

    # Database setup
    db_setup = DatabaseSetup()

    if args.reset:
        print("Resetting database...")
        if not db_setup.drop_database():
            print("Error: Failed to drop database")
            return 1
        time.sleep(2)  # Wait for database to be fully dropped

    # Create database
    if not db_setup.create_database():
        print("Error: Failed to create database")
        return 1

    time.sleep(2)  # Wait for database to be ready

    # Check and install extensions
    print("\nChecking PostgreSQL extensions...")
    if not db_setup.check_extensions():
        print("Warning: Some extensions may not be installed")

    # Initialize schema
    if not db_setup.initialize_schema():
        print("Error: Failed to initialize schema")
        return 1

    # Seed data if requested
    if should_seed:
        seeder = DataSeeder()
        if not seeder.seed_data(args.tenant, args.count):
            print("Warning: Failed to seed sample data")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start the services: docker-compose up -d")
    print("  2. Run health checks: python scripts/health_checks.py")
    print("  3. Access the application at http://localhost:3000")

    return 0


if __name__ == "__main__":
    sys.exit(main())
