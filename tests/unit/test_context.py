"""Unit tests for agents/context.py functions."""

from unittest.mock import MagicMock, patch

from agents.context import fetch_url_content, get_content_json, get_waste_materials


def test_get_waste_materials():
    """Verify get_waste_materials returns expected states structure."""
    data = get_waste_materials()
    assert isinstance(data, dict)
    assert "states" in data
    assert len(data["states"]) > 0

    first_state = data["states"][0]
    assert "name" in first_state
    assert "raw_waste_materials" in first_state
    assert len(first_state["raw_waste_materials"]) > 0

    first_mat = first_state["raw_waste_materials"][0]
    assert "material" in first_mat
    assert "source" in first_mat
    assert "potential_packaging_type" in first_mat


def test_fetch_url_content_success():
    """Verify fetch_url_content correctly parses HTML and extracts text and title."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head><title>Test Packaging</title></head><body><p>Hello Sustainable World</p></body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch("agents.context.httpx.get", return_value=mock_resp):
        res = fetch_url_content("https://example.com/test")

        assert res["url"] == "https://example.com/test"
        assert res["status_code"] == 200
        assert res["title"] == "Test Packaging"
        assert "Hello Sustainable World" in res["content"]
        assert res["error"] is None


def test_fetch_url_content_failure():
    """Verify fetch_url_content handles exceptions gracefully."""
    with patch("agents.context.httpx.get", side_effect=Exception("Connection timed out")):
        res = fetch_url_content("https://example.com/bad")

        assert res["url"] == "https://example.com/bad"
        assert res["status_code"] is None
        assert res["error"] == "Connection timed out"


def test_get_content_json():
    """Verify get_content_json processes a list of URLs."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><head><title>Test</title></head><body>Sample text</body></html>"
    mock_resp.raise_for_status = MagicMock()

    with patch("agents.context.httpx.get", return_value=mock_resp):
        res = get_content_json(["https://example.com/1", "https://example.com/2"])
        assert len(res) == 2
        assert res[0]["title"] == "Test"
        assert res[1]["title"] == "Test"
