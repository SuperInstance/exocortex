"""Demo script — simulates agents hitting the cortex to show shadow traffic."""

import asyncio
import random
import httpx

BASE = "http://localhost:9000"


async def main() -> None:
    async with httpx.AsyncClient() as client:
        print("🎬 Exocortex Demo — generating shadow traffic\n")

        # 1. Remember some things
        topics = [
            ("kitchen temperature is 28°C", ["iot", "temperature", "kitchen"]),
            ("soil moisture zone 3 is critically low at 23%", ["iot", "moisture", "garden"]),
            ("deployed model v2.3 to production", ["devops", "deployment"]),
            ("user satisfaction score: 94%", ["metrics", "users"]),
            ("disk usage at 87%, approaching limit", ["devops", "infrastructure"]),
            ("ESP32:kitchen sensor online", ["iot", "sensor"]),
            ("zone 2 moisture 31%, adequate", ["iot", "moisture", "garden"]),
            ("API latency p99: 142ms", ["metrics", "api"]),
        ]

        print("📌 Storing memories...")
        for content, tags in topics:
            r = await client.post(f"{BASE}/api/v1/remember", json={
                "content": content, "tags": tags, "agent_id": "demo-agent",
            })
            print(f"   → {content[:50]}... ✓")
            await asyncio.sleep(0.3)

        print("\n🔍 Searching memories...")
        queries = [
            "should I water the garden?",
            "infrastructure issues",
            "how's the kitchen?",
        ]
        for q in queries:
            r = await client.post(f"{BASE}/api/v1/recall", json={
                "query": q, "agent_id": "demo-agent",
            })
            data = r.json()
            print(f"   → '{q}' → {data['n']} results")
            for m in data.get("results", []):
                print(f"      • {m['content'][:60]} (sim: {m['similarity']})")
            await asyncio.sleep(0.3)

        print("\n🏋️ Training a model...")
        r = await client.post(f"{BASE}/api/v1/train", json={
            "model": "greenhouse-predictor",
            "epochs": 200,
            "agent_id": "demo-agent",
        })
        data = r.json()
        print(f"   → accuracy: {data.get('accuracy', 0):.1%}")

        print("\n📡 Simulating ESP32 sensor traffic...")
        for i in range(10):
            temp = 28 + random.gauss(0, 2)
            r = await client.get(f"{BASE}/tap/predict", params={
                "sensor": f"zone_{random.randint(1,3)}",
                "reading": f"{temp:.1f}",
            })
            print(f"   → zone sensor: {temp:.1f}°C → {r.text}")
            await asyncio.sleep(0.2)

        print("\n⚠️ Sending anomaly (kitchen fire?)...")
        r = await client.get(f"{BASE}/tap/predict", params={
            "sensor": "kitchen_temp",
            "reading": "211.8",
        })
        print(f"   → {r.text}")

        print("\n📡 TAP recall from ESP32...")
        r = await client.get(f"{BASE}/tap/recall", params={"q": "should I water zone 3"})
        print(f"   → {r.text}")

        print("\n✅ Demo complete. The TUI should be full of shadows!")


if __name__ == "__main__":
    asyncio.run(main())
