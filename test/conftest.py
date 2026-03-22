import os
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

# Set the environment variable before importing anything that reads config
# This ensures all tests use a temporary isolated database instead of the real one
temp_dir = tempfile.TemporaryDirectory()
temp_db_path = Path(temp_dir.name) / "test_food.db"
os.environ["FOOD_DB_PATH"] = str(temp_db_path)

from core.service import FoodService
from web.app import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize the test database once per test session."""
    service = FoodService()
    service.init_db()
    
    yield
    
    # Cleanup temporary directory after tests finish
    temp_dir.cleanup()

@pytest.fixture
def db_service():
    """Provides a FoodService instance pointing to the test DB."""
    # The autouse fixture already initialized the schema.
    # We can just return a fresh service instance here.
    return FoodService()

@pytest.fixture
def api_client():
    """Provides a FastAPI TestClient."""
    return TestClient(app)

@pytest.fixture
def cli_runner():
    """Provides a Typer CLI TestRunner."""
    return CliRunner()
