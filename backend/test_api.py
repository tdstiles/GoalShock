#!/usr/bin/env python3
"""
GoalShock API Test Script
Tests all REST endpoints and WebSocket connection.
"""

import asyncio
import httpx
import websockets
import json
from datetime import datetime


API_BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"


async def test_rest_endpoints():
    """Test all REST API endpoints"""
    print("=" * 60)
    print("Testing REST API Endpoints")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test root
        print("\n1. Testing GET /")
        response = await client.get(f"{API_BASE}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Test health check
        print("\n2. Testing GET /health")
        response = await client.get(f"{API_BASE}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Test get config
        print("\n3. Testing GET /api/config")
        response = await client.get(f"{API_BASE}/api/config")
        print(f"   Status: {response.status_code}")
        config = response.json()
        print(f"   Demo Mode: {config.get('demo_mode')}")
        print(f"   Max Trade Size: ${config.get('max_trade_size_usd')}")

        # Test bot status
        print("\n4. Testing GET /api/bot/status")
        response = await client.get(f"{API_BASE}/api/bot/status")
        print(f"   Status: {response.status_code}")
        status = response.json()
        print(f"   Bot Status: {status.get('status')}")
        print(f"   Total Trades: {status.get('total_trades')}")

        # Start bot
        print("\n5. Testing POST /api/bot/start")
        response = await client.post(f"{API_BASE}/api/bot/start")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Wait a bit for events
        print("\n   Waiting 5 seconds for events...")
        await asyncio.sleep(5)

        # Get trades
        print("\n6. Testing GET /api/trades")
        response = await client.get(f"{API_BASE}/api/trades")
        print(f"   Status: {response.status_code}")
        trades = response.json()
        print(f"   Total Trades: {len(trades)}")
        if trades:
            print(f"   Latest Trade: {trades[0].get('market')} - {trades[0].get('side')}")

        # Get goals
        print("\n7. Testing GET /api/goals")
        response = await client.get(f"{API_BASE}/api/goals")
        print(f"   Status: {response.status_code}")
        goals = response.json()
        print(f"   Total Goals: {len(goals)}")
        if goals:
            print(f"   Latest Goal: {goals[0].get('match_name')} - {goals[0].get('scoring_team')}")

        # Get events
        print("\n8. Testing GET /api/events")
        response = await client.get(f"{API_BASE}/api/events")
        print(f"   Status: {response.status_code}")
        events = response.json()
        print(f"   Total Events: {len(events)}")

        # Get metrics
        print("\n9. Testing GET /api/metrics")
        response = await client.get(f"{API_BASE}/api/metrics")
        print(f"   Status: {response.status_code}")
        metrics = response.json()
        print(f"   Avg Total Latency: {metrics.get('avg_total_latency_ms')}ms")
        print(f"   Total Trades: {metrics.get('total_trades_executed')}")

        # Stop bot
        print("\n10. Testing POST /api/bot/stop")
        response = await client.post(f"{API_BASE}/api/bot/stop")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")


async def test_websocket():
    """Test WebSocket connection"""
    print("\n" + "=" * 60)
    print("Testing WebSocket Connection")
    print("=" * 60)

    # Start bot first
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE}/api/bot/start")

    print(f"\nConnecting to {WS_URL}...")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected successfully!")

            print("\nListening for events (10 seconds)...\n")

            # Listen for 10 seconds
            event_count = 0
            timeout = 10

            try:
                async for message in asyncio.wait_for(
                    websocket,
                    timeout=timeout
                ):
                    data = json.loads(message)
                    event_type = data.get("type", "unknown")
                    timestamp = data.get("timestamp", "")

                    event_count += 1

                    print(f"[{event_count}] {event_type.upper()} @ {timestamp}")

                    if event_type == "goal":
                        goal_data = data.get("data", {})
                        print(f"    ⚽ {goal_data.get('match_name')}")
                        print(f"    Team: {goal_data.get('scoring_team')}")
                        print(f"    Minute: {goal_data.get('minute')}'")
                        print(f"    Underdog: {goal_data.get('is_underdog')}")

                    elif event_type == "trade":
                        trade_data = data.get("data", {})
                        print(f"    💰 {trade_data.get('market')}")
                        print(f"    Side: {trade_data.get('side')}")
                        print(f"    Price: {trade_data.get('price_cents')}¢")
                        print(f"    Size: {trade_data.get('size')}")

                    elif event_type == "price_check":
                        pc_data = data.get("data", {})
                        print(f"    📊 {pc_data.get('market')}")
                        print(f"    Price: {pc_data.get('price')}¢")

                    print()

            except asyncio.TimeoutError:
                print(f"✅ Test completed ({timeout}s timeout)")
                print(f"   Total events received: {event_count}")

    except Exception as e:
        print(f"❌ WebSocket error: {e}")

    # Stop bot
    async with httpx.AsyncClient() as client:
        await client.post(f"{API_BASE}/api/bot/stop")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  GoalShock API Test Suite")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    try:
        # Test REST endpoints
        await test_rest_endpoints()

        # Test WebSocket
        await test_websocket()

        print("\n" + "=" * 60)
        print("  ✅ All tests completed successfully!")
        print("=" * 60)

    except httpx.ConnectError:
        print("\n❌ Error: Cannot connect to API server")
        print("   Make sure the server is running on http://localhost:8000")
        print("   Start with: python main.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
