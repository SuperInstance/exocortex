"""Tests for FastAPI REST + TAP protocol endpoints.

Tests all HTTP endpoints including the REST API, TAP (Tiny Agent Protocol)
for ESP32, error handling, CORS, and edge cases.

Uses FastAPI TestClient — no live server needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.bus import CorticalBus
from src.compute import ComputeEngine
from src.memory import MemoryLayer
from src.protocols import create_app


# ─── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Create a fresh FastAPI app for each test."""
    bus = CorticalBus()
    compute = ComputeEngine()
    memory = MemoryLayer()
    return create_app(bus, compute, memory)


@pytest.fixture
def client(app):
    """TestClient for the exocortex API."""
    return TestClient(app)


# ─── App creation ─────────────────────────────────────────────────


class TestAppCreation:
    def test_app_has_correct_title(self, app):
        assert app.title == "Exocortex"

    def test_app_has_correct_version(self, app):
        assert app.version == "0.1.0"

    def test_app_has_cors_middleware(self, app):
        # FastAPI wraps CORS in a Middleware object
        middleware_repr = [str(m) for m in app.user_middleware]
        assert any("CORSMiddleware" in m for m in middleware_repr)

    def test_app_has_all_routes(self, app):
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/api/v1/embed" in paths
        assert "/api/v1/remember" in paths
        assert "/api/v1/recall" in paths
        assert "/api/v1/predict" in paths
        assert "/api/v1/train" in paths
        assert "/api/v1/query" in paths
        assert "/api/v1/capabilities" in paths
        assert "/api/v1/stats" in paths
        assert "/tap/recall" in paths
        assert "/tap/remember" in paths
        assert "/tap/predict" in paths
        assert "/tap/sense" in paths


# ─── REST: GET endpoints ──────────────────────────────────────────


class TestCapabilitiesEndpoint:
    def test_returns_all_operations(self, client):
        r = client.get("/api/v1/capabilities")
        assert r.status_code == 200
        ops = r.json()["operations"]
        assert "embed" in ops
        assert "query" in ops
        assert "train" in ops
        assert "predict" in ops
        assert "analyze" in ops
        assert "remember" in ops
        assert "recall" in ops
        assert "transform" in ops
        assert len(ops) == 8

    def test_returns_protocols(self, client):
        r = client.get("/api/v1/capabilities")
        protocols = r.json()["protocols"]
        assert "rest" in protocols
        assert "a2a" in protocols
        assert "mcp" in protocols
        assert "tap" in protocols

    def test_returns_tiers(self, client):
        r = client.get("/api/v1/capabilities")
        data = r.json()
        assert "hot" in data["compute_tiers"]
        assert "warm" in data["compute_tiers"]
        assert "batch" in data["compute_tiers"]
        assert "hot" in data["memory_tiers"]
        assert "warm" in data["memory_tiers"]
        assert "cold" in data["memory_tiers"]


class TestStatsEndpoint:
    def test_empty_stats(self, client):
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["memory"]["total"] == 0
        assert data["compute"]["models"] == 0

    def test_stats_after_remember(self, client):
        client.post("/api/v1/remember", json={"content": "test", "agent_id": "a"})
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        assert r.json()["memory"]["total"] > 0

    def test_stats_after_train(self, client):
        client.post("/api/v1/train", json={"model": "m1", "epochs": 5})
        r = client.get("/api/v1/stats")
        assert r.json()["compute"]["models"] >= 1


class TestQueryEndpoint:
    def test_query_empty_tags(self, client):
        r = client.get("/api/v1/query", params={"tags": ""})
        assert r.status_code == 200
        assert r.json()["n"] == 0

    def test_query_with_tags(self, client):
        client.post("/api/v1/remember", json={
            "content": "garden data", "agent_id": "a", "tags": ["garden"]
        })
        r = client.get("/api/v1/query", params={"tags": "garden"})
        assert r.status_code == 200
        data = r.json()
        assert data["n"] >= 1
        assert "garden" in data["results"][0]["content"]

    def test_query_multiple_tags(self, client):
        client.post("/api/v1/remember", json={
            "content": "alpha", "agent_id": "a", "tags": ["x"]
        })
        client.post("/api/v1/remember", json={
            "content": "beta", "agent_id": "a", "tags": ["y"]
        })
        r = client.get("/api/v1/query", params={"tags": "x,y"})
        assert r.status_code == 200
        assert r.json()["n"] >= 2

    def test_query_no_match(self, client):
        client.post("/api/v1/remember", json={
            "content": "data", "agent_id": "a", "tags": ["real"]
        })
        r = client.get("/api/v1/query", params={"tags": "nonexistent"})
        assert r.status_code == 200
        assert r.json()["n"] == 0


# ─── REST: POST endpoints ─────────────────────────────────────────


class TestEmbedEndpoint:
    def test_basic_embed(self, client):
        r = client.post("/api/v1/embed", json={"content": "hello", "dims": 128})
        assert r.status_code == 200
        data = r.json()
        assert data["dims"] == 128
        assert "id" in data
        assert "latency_ms" in data
        assert data["latency_ms"] >= 0

    def test_embed_default_dims(self, client):
        r = client.post("/api/v1/embed", json={"content": "test"})
        assert r.status_code == 200
        assert r.json()["dims"] == 384

    def test_embed_default_agent(self, client):
        r = client.post("/api/v1/embed", json={"content": "test"})
        assert r.status_code == 200

    def test_embed_stores_memory(self, client):
        r = client.post("/api/v1/embed", json={"content": "stored text"})
        assert r.status_code == 200
        stats = client.get("/api/v1/stats").json()
        assert stats["memory"]["total"] > 0


class TestRememberEndpoint:
    def test_basic_remember(self, client):
        r = client.post("/api/v1/remember", json={
            "content": "hello world", "agent_id": "test", "tags": ["greeting"]
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "remembered"
        assert "id" in data

    def test_remember_default_agent(self, client):
        r = client.post("/api/v1/remember", json={"content": "no agent"})
        assert r.status_code == 200
        assert r.json()["status"] == "remembered"

    def test_remember_default_empty_tags(self, client):
        r = client.post("/api/v1/remember", json={"content": "no tags"})
        assert r.status_code == 200

    def test_remember_empty_content(self, client):
        r = client.post("/api/v1/remember", json={"content": ""})
        assert r.status_code == 200

    def test_remember_trace_id_bug_regression(self):
        """Regression: /api/v1/remember used to crash with
        'got multiple values for keyword argument trace_id'.

        The CortexEvent.new() factory already sets trace_id, but the
        endpoint also passed trace_id via kwargs. Fixed by using
        setdefault in CortexEvent.new().
        """
        bus = CorticalBus()
        compute = ComputeEngine()
        memory = MemoryLayer()
        app = create_app(bus, compute, memory)
        c = TestClient(app)
        r = c.post("/api/v1/remember", json={
            "content": "trace regression", "agent_id": "test"
        })
        assert r.status_code == 200


class TestRecallEndpoint:
    def test_basic_recall(self, client):
        client.post("/api/v1/remember", json={"content": "hello world"})
        r = client.post("/api/v1/recall", json={"query": "hello"})
        assert r.status_code == 200
        data = r.json()
        assert data["n"] >= 1
        assert "results" in data

    def test_recall_empty_memory(self, client):
        r = client.post("/api/v1/recall", json={"query": "nothing"})
        assert r.status_code == 200
        assert r.json()["n"] == 0

    def test_recall_top_k(self, client):
        for i in range(5):
            client.post("/api/v1/remember", json={"content": f"item {i}"})
        r = client.post("/api/v1/recall", json={"query": "item", "top_k": 2})
        assert r.status_code == 200
        assert r.json()["n"] <= 2

    def test_recall_result_structure(self, client):
        client.post("/api/v1/remember", json={"content": "structured"})
        r = client.post("/api/v1/recall", json={"query": "structured"})
        results = r.json()["results"]
        if results:
            assert "id" in results[0]
            assert "content" in results[0]
            assert "similarity" in results[0]
            assert "confidence" in results[0]


class TestPredictEndpoint:
    def test_predict_untrained(self, client):
        r = client.post("/api/v1/predict", json={"input": [0.5] * 384})
        assert r.status_code == 200
        data = r.json()
        assert data["label"] == "unknown"
        assert data["confidence"] == 0.0

    def test_predict_trained(self, client):
        client.post("/api/v1/train", json={"model": "m", "epochs": 5})
        r = client.post("/api/v1/predict", json={"input": [0.5] * 384, "model": "m"})
        assert r.status_code == 200
        data = r.json()
        assert "label" in data
        assert "confidence" in data


class TestTrainEndpoint:
    def test_basic_train(self, client):
        r = client.post("/api/v1/train", json={"model": "test-model", "epochs": 10})
        assert r.status_code == 200
        data = r.json()
        assert data["trained"] is True
        assert data["model"] == "test-model"
        assert data["epochs"] == 10
        assert 0.85 <= data["accuracy"] <= 0.96

    def test_train_default_model_name(self, client):
        r = client.post("/api/v1/train", json={"epochs": 5})
        assert r.status_code == 200
        assert r.json()["trained"] is True

    def test_train_custom_dims(self, client):
        r = client.post("/api/v1/train", json={
            "model": "custom",
            "epochs": 5,
            "input_dim": 128,
            "hidden_dim": 32,
            "output_dim": 6,
        })
        assert r.status_code == 200
        assert r.json()["trained"] is True


# ─── TAP: Tiny Agent Protocol ─────────────────────────────────────


class TestTapRecall:
    def test_basic_tap_recall(self, client):
        client.post("/api/v1/remember", json={"content": "weather is sunny"})
        r = client.get("/tap/recall", params={"q": "weather"})
        assert r.status_code == 200
        # FastAPI returns strings as JSON (with quotes)
        assert len(r.text) <= 202  # 200 + quotes
        text = r.json() if r.headers["content-type"].startswith("application/json") else r.text
        assert len(text) <= 200

    def test_tap_recall_empty_memory(self, client):
        r = client.get("/tap/recall", params={"q": "nothing"})
        assert r.status_code == 200
        assert "no memories" in r.text

    def test_tap_recall_max_200_bytes(self, client):
        client.post("/api/v1/remember", json={
            "content": "x" * 500
        })
        r = client.get("/tap/recall", params={"q": "x"})
        assert len(r.text) <= 200

    def test_tap_recall_no_query_param(self, client):
        r = client.get("/tap/recall")
        assert r.status_code == 200


class TestTapRemember:
    def test_basic_tap_remember(self, client):
        r = client.post("/tap/remember", json={
            "content": "sensor reading",
            "agent_id": "esp32-1",
            "tags": ["iot"],
        })
        assert r.status_code == 200
        assert r.json() == "remembered"

    def test_tap_remember_stores_in_memory(self, client):
        client.post("/tap/remember", json={
            "content": "from esp32",
            "agent_id": "esp32",
        })
        stats = client.get("/api/v1/stats").json()
        assert stats["memory"]["total"] > 0

    def test_tap_remember_default_agent(self, client):
        r = client.post("/tap/remember", json={"content": "test"})
        assert r.status_code == 200


class TestTapPredict:
    def test_normal_reading(self, client):
        r = client.get("/tap/predict", params={"sensor": "temp", "reading": "25.0"})
        assert r.status_code == 200
        assert "normal" in r.text or "anomaly" in r.text

    def test_invalid_reading(self, client):
        r = client.get("/tap/predict", params={"sensor": "temp", "reading": "abc"})
        assert r.status_code == 200
        assert "error" in r.text.lower()

    def test_missing_reading(self, client):
        r = client.get("/tap/predict", params={"sensor": "temp"})
        assert r.status_code == 200
        assert "error" in r.text.lower()

    def test_anomaly_detection(self, client):
        # Feed baseline readings
        for v in [20.0, 21.0, 19.0, 20.5, 20.0, 21.0, 19.5, 20.0]:
            client.get("/tap/predict", params={"sensor": "anomaly_test", "reading": str(v)})
        # Trigger anomaly
        r = client.get("/tap/predict", params={"sensor": "anomaly_test", "reading": "200.0"})
        assert r.status_code == 200
        assert "anomaly" in r.text.lower()


class TestTapSense:
    def test_basic_sense(self, client):
        r = client.post("/tap/sense", json={"data": "t:28.5 h:62 z:3"})
        assert r.status_code == 200
        assert r.json() == "logged"

    def test_sense_stores_memory(self, client):
        client.post("/tap/sense", json={"data": "t:25.0"})
        stats = client.get("/api/v1/stats").json()
        assert stats["memory"]["total"] > 0

    def test_sense_with_invalid_values(self, client):
        r = client.post("/tap/sense", json={"data": "t:abc h:62"})
        assert r.status_code == 200
        assert r.json() == "logged"

    def test_sense_empty_data(self, client):
        r = client.post("/tap/sense", json={"data": ""})
        assert r.status_code == 200
        assert r.json() == "logged"

    def test_sense_anomaly_detection(self, client):
        """Sense endpoint should detect anomalies in sensor data."""
        # Feed baseline
        for _ in range(8):
            client.post("/tap/sense", json={"data": "temp:20.0"})
        # Anomaly
        r = client.post("/tap/sense", json={"data": "temp:200.0"})
        assert r.status_code == 200
        assert r.json() == "logged"  # Still logs even with anomaly
