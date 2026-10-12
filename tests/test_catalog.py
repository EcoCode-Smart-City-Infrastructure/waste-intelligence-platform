"""Tests for NYC Open Data catalog tools."""

from __future__ import annotations

import pytest

from src.nyc_opendata_mcp.tools.catalog import (
    nyc_analyze_dataset,
    nyc_get_dataset,
    nyc_list_categories,
    nyc_list_tags,
    nyc_search_datasets,
)
from src.nyc_opendata_mcp.config import NYC_CATEGORIES


class TestSearchDatasets:
    """Test dataset search functionality."""

    @pytest.mark.asyncio
    async def test_search_all_datasets(self):
        """Test searching all datasets."""
        from src.nyc_opendata_mcp.tools.catalog import SearchDatasetsInput
        
        input_data = SearchDatasetsInput(query="*")
        result = await nyc_search_datasets(input_data)
        
        assert result is not None
        assert "model" in result or "markdown" in result

    @pytest.mark.asyncio
    async def test_search_specific_query(self):
        """Test searching with specific query."""
        from src.nyc_opendata_mcp.tools.catalog import SearchDatasetsInput
        
        input_data = SearchDatasetsInput(query="waste")
        result = await nyc_search_datasets(input_data)
        
        assert result is not None
        assert "model" in result or "markdown" in result

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self):
        """Test searching with category filter."""
        from src.nyc_opendata_mcp.tools.catalog import SearchDatasetsInput
        
        input_data = SearchDatasetsInput(
            query="recycling",
            filter_category="waste-management"
        )
        result = await nyc_search_datasets(input_data)
        
        assert result is not None
        assert "model" in result or "markdown" in result


class TestGetDataset:
    """Test dataset retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_dataset_by_id(self):
        """Test getting dataset by ID."""
        from src.nyc_opendata_mcp.tools.catalog import GetDatasetInput
        
        # Use a known dataset ID (this would be a real ID in production)
        input_data = GetDatasetInput(dataset_id="7c3d-6b2j")
        result = await nyc_get_dataset(input_data)
        
        assert result is not None
        assert isinstance(result, str)


class TestListCategories:
    """Test category listing functionality."""

    @pytest.mark.asyncio
    async def test_list_categories_markdown(self):
        """Test listing categories in markdown format."""
        from src.nyc_opendata_mcp.tools.catalog import ListCategoriesInput
        
        input_data = ListCategoriesInput(format="markdown")
        result = await nyc_list_categories(input_data)
        
        assert result is not None
        assert isinstance(result, str)
        assert "Verf\u00fcgbare Kategorien" in result or "Available Categories" in result

    @pytest.mark.asyncio
    async def test_list_categories_json(self):
        """Test listing categories in JSON format."""
        from src.nyc_opendata_mcp.tools.catalog import ListCategoriesInput
        
        input_data = ListCategoriesInput(format="json")
        result = await nyc_list_categories(input_data)
        
        assert result is not None
        assert isinstance(result, str)
        assert "categories" in result


class TestListTags:
    """Test tag listing functionality."""

    @pytest.mark.asyncio
    async def test_list_tags(self):
        """Test listing tags."""
        from src.nyc_opendata_mcp.tools.catalog import ListTagsInput
        
        input_data = ListTagsInput(limit=10)
        result = await nyc_list_tags(input_data)
        
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_list_tags_with_category(self):
        """Test listing tags with category filter."""
        from src.nyc_opendata_mcp.tools.catalog import ListTagsInput
        
        input_data = ListTagsInput(
            category="waste-management",
            limit=10
        )
        result = await nyc_list_tags(input_data)
        
        assert result is not None
        assert isinstance(result, str)


class TestCatalogStats:
    """Test catalog statistics functionality."""

    @pytest.mark.asyncio
    async def test_catalog_stats(self):
        """Test getting catalog statistics."""
        result = await nyc_catalog_stats()
        
        assert result is not None
        assert isinstance(result, str)
        assert "Katalog Statistik" in result or "Catalog Statistics" in result


class TestAnalyzeDataset:
    """Test dataset analysis functionality."""

    @pytest.mark.asyncio
    async def test_analyze_dataset(self):
        """Test analyzing a dataset."""
        from src.nyc_opendata_mcp.tools.catalog import AnalyzeDatasetInput
        
        input_data = AnalyzeDatasetInput(dataset_id="7c3d-6b2j")
        result = await nyc_analyze_dataset(input_data)
        
        assert result is not None
        assert isinstance(result, str)
