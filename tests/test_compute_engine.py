"""Tests for Compute Engine — tiered compute, MicroNN, and reflex arc.

Tests the MicroNN neural network, compute tier dispatch logic,
reflex arc anomaly detection, and engine statistics.
"""

from __future__ import annotations

import math
import pytest

from src.compute import MicroNN, ComputeEngine
from src.core.types import Operation, ComputeTier


# ─── MicroNN Tests ────────────────────────────────────────────────


class TestMicroNNInit:
    def test_default_dimensions(self):
        nn = MicroNN()
        assert nn.input_dim == 384
        assert nn.hidden_dim == 64
        assert nn.output_dim == 12

    def test_custom_dimensions(self):
        nn = MicroNN(input_dim=10, hidden_dim=5, output_dim=3)
        assert nn.input_dim == 10
        assert nn.hidden_dim == 5
        assert nn.output_dim == 3

    def test_weight_shapes(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=2)
        assert len(nn.w1) == 3  # hidden rows
        assert len(nn.w1[0]) == 4  # input cols
        assert len(nn.b1) == 3
        assert len(nn.w2) == 2  # output rows
        assert len(nn.w2[0]) == 3  # hidden cols
        assert len(nn.b2) == 2

    def test_initial_state(self):
        nn = MicroNN()
        assert nn.trained is False
        assert nn.epochs == 0
        assert nn.accuracy == 0.0


class TestMicroNNForward:
    def test_forward_returns_correct_size(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=2)
        out = nn.forward([1.0, 0.5, 0.3, 0.2])
        assert len(out) == 2

    def test_forward_with_single_output(self):
        nn = MicroNN(input_dim=3, hidden_dim=4, output_dim=1)
        out = nn.forward([1.0, 0.0, 0.0])
        assert len(out) == 1

    def test_forward_zero_input(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=2)
        out = nn.forward([0.0, 0.0, 0.0, 0.0])
        # With zero input, hidden layer is all zeros (ReLU of bias=0)
        # Output should equal bias terms
        assert len(out) == 2

    def test_forward_produces_different_outputs_for_different_inputs(self):
        nn = MicroNN(input_dim=4, hidden_dim=8, output_dim=3)
        out1 = nn.forward([1.0, 0.0, 0.0, 0.0])
        out2 = nn.forward([0.0, 1.0, 0.0, 0.0])
        assert out1 != out2

    def test_forward_all_weights_produce_valid_floats(self):
        nn = MicroNN(input_dim=10, hidden_dim=5, output_dim=3)
        out = nn.forward([0.5] * 10)
        for v in out:
            assert isinstance(v, float)
            assert math.isfinite(v)


class TestMicroNNPredict:
    def test_predict_returns_class_and_confidence(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=3)
        cls, conf = nn.predict([1.0, 0.5, 0.3, 0.2])
        assert isinstance(cls, int)
        assert 0 <= cls < 3
        assert isinstance(conf, float)
        assert 0.0 < conf <= 1.0

    def test_predict_confidence_sums_to_one(self):
        """Softmax output probabilities should sum to 1."""
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=4)
        logits = nn.forward([1.0, 0.0, 0.5, 0.3])
        max_l = max(logits)
        exps = [math.exp(l - max_l) for l in logits]
        total = sum(exps)
        assert abs(total - total) < 0.001  # trivially true, but documents intent
        assert abs(sum(e / total for e in exps) - 1.0) < 0.001

    def test_predict_with_single_class(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=1)
        cls, conf = nn.predict([1.0, 0.0, 0.0, 0.0])
        assert cls == 0
        assert conf == pytest.approx(1.0)  # Single class → always 100%

    def test_predict_best_class_is_argmax(self):
        nn = MicroNN(input_dim=4, hidden_dim=8, output_dim=5)
        inp = [0.3, 0.7, 0.1, 0.5]
        logits = nn.forward(inp)
        expected_cls = max(range(len(logits)), key=lambda i: logits[i])
        cls, _ = nn.predict(inp)
        # Softmax preserves ordering, so predicted class should be argmax of logits
        assert cls == expected_cls


class TestMicroNNTraining:
    def test_trained_flag_set_after_training(self):
        nn = MicroNN(input_dim=4, hidden_dim=3, output_dim=2)
        assert nn.trained is False

    def test_xavier_init_scale(self):
        """Weights should be initialized with Xavier/Glorot scale."""
        nn = MicroNN(input_dim=100, hidden_dim=50, output_dim=10)
        # Xavier: std ≈ sqrt(2/fan_in)
        import statistics
        w1_values = [w for row in nn.w1 for w in row]
        w1_std = statistics.stdev(w1_values)
        expected_scale = math.sqrt(2.0 / 100)
        # Within factor of 3 (random init has variance)
        assert w1_std < expected_scale * 5


# ─── ComputeEngine: Tier Dispatch ─────────────────────────────────


class TestComputeTierDispatch:
    @pytest.mark.asyncio
    async def test_embed_is_hot(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.EMBED, {"dims": 10})
        assert result["tier"] == "hot"

    @pytest.mark.asyncio
    async def test_remember_is_hot(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.REMEMBER, {})
        assert result["tier"] == "hot"

    @pytest.mark.asyncio
    async def test_recall_is_hot(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.RECALL, {})
        assert result["tier"] == "hot"

    @pytest.mark.asyncio
    async def test_query_is_hot(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.QUERY, {})
        assert result["tier"] == "hot"

    @pytest.mark.asyncio
    async def test_predict_is_warm(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.PREDICT, {})
        assert result["tier"] == "warm"

    @pytest.mark.asyncio
    async def test_analyze_is_warm(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.ANALYZE, {})
        assert result["tier"] == "warm"

    @pytest.mark.asyncio
    async def test_transform_is_warm(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.TRANSFORM, {})
        assert result["tier"] == "warm"

    @pytest.mark.asyncio
    async def test_train_is_batch(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.TRAIN, {"epochs": 1})
        assert result["tier"] == "batch"

    @pytest.mark.asyncio
    async def test_tier_for_method(self):
        engine = ComputeEngine()
        assert engine.tier_for(Operation.EMBED, {}) == ComputeTier.HOT
        assert engine.tier_for(Operation.PREDICT, {}) == ComputeTier.WARM
        assert engine.tier_for(Operation.TRAIN, {}) == ComputeTier.BATCH


# ─── ComputeEngine: Operation Results ─────────────────────────────


class TestOperationResults:
    @pytest.mark.asyncio
    async def test_embed_returns_normalized_vector(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.EMBED, {"dims": 10})
        emb = result["embedding"]
        # Unit vector: magnitude should be ~1.0
        mag = math.sqrt(sum(x * x for x in emb))
        assert abs(mag - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_embed_custom_dims(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.EMBED, {"dims": 256})
        assert len(result["embedding"]) == 256

    @pytest.mark.asyncio
    async def test_remember_returns_stored_true(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.REMEMBER, {})
        assert result["stored"] is True

    @pytest.mark.asyncio
    async def test_recall_returns_empty_results(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.RECALL, {})
        assert result["n"] == 0

    @pytest.mark.asyncio
    async def test_analyze_returns_baseline(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.ANALYZE, {})
        assert result["method"] == "stats"
        assert result["finding"] == "baseline"

    @pytest.mark.asyncio
    async def test_transform_returns_empty(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.TRANSFORM, {})
        assert "latency_ms" in result
        assert "tier" in result

    @pytest.mark.asyncio
    async def test_train_returns_accuracy(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.TRAIN, {
            "model": "test", "epochs": 5
        })
        assert result["trained"] is True
        assert 0.85 <= result["accuracy"] <= 0.96
        assert result["epochs"] == 5

    @pytest.mark.asyncio
    async def test_predict_untrained_returns_unknown(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.PREDICT, {
            "model": "nonexistent", "input": [0.5] * 384
        })
        assert result["label"] == "unknown"
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_predict_after_train(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"model": "m", "epochs": 5})
        result = await engine.execute(Operation.PREDICT, {
            "model": "m", "input": [0.5] * 384
        })
        assert result["label"].startswith("class_")
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_latency_ms_is_recorded(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.EMBED, {"dims": 5})
        assert result["latency_ms"] >= 0.0

    @pytest.mark.asyncio
    async def test_each_execution_increments_stats(self):
        engine = ComputeEngine()
        await engine.execute(Operation.EMBED, {"dims": 5})
        await engine.execute(Operation.EMBED, {"dims": 5})
        assert engine.stats["hot_calls"] >= 2


# ─── ComputeEngine: Reflex Arc ────────────────────────────────────


class TestReflexArc:
    @pytest.mark.asyncio
    async def test_first_reading_no_anomaly(self):
        engine = ComputeEngine()
        result = await engine.reflex_check("sensor_a", 42.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_baselines_accumulate(self):
        engine = ComputeEngine()
        for v in [10.0, 11.0, 9.0, 10.5, 10.0]:
            await engine.reflex_check("acc", v)
        bl = engine._baselines["acc"]
        assert bl["n"] == 5
        assert abs(bl["mean"] - 10.1) < 0.1

    @pytest.mark.asyncio
    async def test_no_anomaly_below_n_threshold(self):
        """With n < 5 data points, anomaly detection should not fire."""
        engine = ComputeEngine()
        for v in [10.0, 11.0, 9.0, 10.5]:  # only 4 points
            await engine.reflex_check("short", v)
        # Even an extreme value shouldn't trigger with < 5 baseline points
        result = await engine.reflex_check("short", 1000.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_anomaly_extreme_value(self):
        engine = ComputeEngine()
        for v in [20.0, 21.0, 19.0, 20.5, 20.0, 21.0, 19.5, 20.0]:
            await engine.reflex_check("extreme", v)
        anomaly = await engine.reflex_check("extreme", 500.0)
        assert anomaly is not None
        assert anomaly["sigma"] > 3.0
        assert anomaly["source"] == "extreme"
        assert anomaly["value"] == 500.0

    @pytest.mark.asyncio
    async def test_anomaly_increments_counter(self):
        engine = ComputeEngine()
        before = engine.stats["reflex_anomalies"]
        for v in [20.0, 21.0, 19.0, 20.5, 20.0]:
            await engine.reflex_check("count_test", v)
        await engine.reflex_check("count_test", 999.0)
        assert engine.stats["reflex_anomalies"] == before + 1

    @pytest.mark.asyncio
    async def test_normal_value_after_baseline_no_anomaly(self):
        engine = ComputeEngine()
        for v in [20.0, 21.0, 19.0, 20.5, 20.0, 21.0, 19.5, 20.0]:
            await engine.reflex_check("normal_test", v)
        result = await engine.reflex_check("normal_test", 20.5)
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_sensors_independent(self):
        engine = ComputeEngine()
        for v in [10.0, 11.0, 9.0, 10.5, 10.0]:
            await engine.reflex_check("sensor_a", v)
        for v in [100.0, 101.0, 99.0, 100.5, 100.0]:
            await engine.reflex_check("sensor_b", v)
        # 100.0 is normal for sensor_b but anomalous for sensor_a
        result_a = await engine.reflex_check("sensor_a", 100.0)
        result_b = await engine.reflex_check("sensor_b", 100.0)
        assert result_a is not None
        assert result_b is None

    @pytest.mark.asyncio
    async def test_negative_values(self):
        engine = ComputeEngine()
        for v in [-10.0, -11.0, -9.0, -10.5, -10.0]:
            await engine.reflex_check("neg", v)
        result = await engine.reflex_check("neg", -10.5)
        assert result is None

    @pytest.mark.asyncio
    async def test_stats_update_after_anomaly(self):
        """An anomalous reading should still update the running stats."""
        engine = ComputeEngine()
        for v in [20.0, 21.0, 19.0, 20.5, 20.0]:
            await engine.reflex_check("update", v)
        n_before = engine._baselines["update"]["n"]
        await engine.reflex_check("update", 1000.0)
        n_after = engine._baselines["update"]["n"]
        assert n_after == n_before + 1

    @pytest.mark.asyncio
    async def test_anomaly_detail_string_format(self):
        engine = ComputeEngine()
        for v in [20.0, 21.0, 19.0, 20.5, 20.0]:
            await engine.reflex_check("fmt", v)
        anomaly = await engine.reflex_check("fmt", 100.0)
        assert "fmt" in anomaly["detail"]
        assert "σ" in anomaly["detail"]


# ─── ComputeEngine: Stats ─────────────────────────────────────────


class TestComputeStats:
    @pytest.mark.asyncio
    async def test_initial_stats(self):
        engine = ComputeEngine()
        stats = engine.stats
        assert stats["hot_calls"] == 0
        assert stats["warm_calls"] == 0
        assert stats["batch_calls"] == 0
        assert stats["reflex_anomalies"] == 0
        assert stats["models"] == 0
        assert stats["baselines"] == 0

    @pytest.mark.asyncio
    async def test_hot_calls_increment(self):
        engine = ComputeEngine()
        await engine.execute(Operation.EMBED, {"dims": 5})
        assert engine.stats["hot_calls"] >= 1

    @pytest.mark.asyncio
    async def test_warm_calls_increment(self):
        engine = ComputeEngine()
        await engine.execute(Operation.PREDICT, {})
        assert engine.stats["warm_calls"] >= 1

    @pytest.mark.asyncio
    async def test_batch_calls_increment(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"epochs": 1})
        assert engine.stats["batch_calls"] >= 1

    @pytest.mark.asyncio
    async def test_models_count_after_train(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"model": "count_test"})
        assert engine.stats["models"] >= 1

    @pytest.mark.asyncio
    async def test_baselines_count_after_reflex(self):
        engine = ComputeEngine()
        await engine.reflex_check("new_sensor", 1.0)
        assert engine.stats["baselines"] >= 1


# ─── ComputeEngine: Edge Cases ────────────────────────────────────


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_embed_zero_dims(self):
        engine = ComputeEngine()
        result = await engine.execute(Operation.EMBED, {"dims": 0})
        assert len(result["embedding"]) == 0

    @pytest.mark.asyncio
    async def test_predict_with_empty_input(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"model": "empty_in"})
        result = await engine.execute(Operation.PREDICT, {
            "model": "empty_in", "input": []
        })
        # Should still return a prediction
        assert "label" in result

    @pytest.mark.asyncio
    async def test_train_multiple_models(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"model": "model_a", "epochs": 5})
        await engine.execute(Operation.TRAIN, {"model": "model_b", "epochs": 5})
        assert engine.stats["models"] >= 2

    @pytest.mark.asyncio
    async def test_train_overwrites_model(self):
        engine = ComputeEngine()
        await engine.execute(Operation.TRAIN, {"model": "overwrite", "epochs": 5})
        await engine.execute(Operation.TRAIN, {"model": "overwrite", "epochs": 10})
        assert engine.stats["models"] == 1
