import asyncio
import websockets
import json
import requests
import sys
import io

# Fix Windows console encoding — allows printing any Unicode character
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# =====================================================================
#  SET THIS TO THE IP ADDRESS SHOWN IN ARDUINO SERIAL MONITOR
# =====================================================================
ESP32_DRONE_IP = "10.75.93.203"  # LiteWing drone - confirmed online
# =====================================================================

async def drone_client():
    uri = "ws://localhost:8000/ws/drone"
    print("[BRIDGE] ESP32 Drone bridge booting up...")
    print(f"[BRIDGE] Connecting to Backend WebSocket at {uri}")
    print(f"[BRIDGE] Physical drone IP: {ESP32_DRONE_IP}")

    try:
        async with websockets.connect(uri) as websocket:
            print("[BRIDGE] Connected! Drone is Standby at Pad.")

            # Send initial status to backend
            await websocket.send(json.dumps({
                "status": "online",
                "battery": 98,
                "gps": "locked"
            }))

            while True:
                # Wait for command from backend
                message = await websocket.recv()
                data = json.loads(message)

                if data.get("action") == "TEST_SPIN":
                    print("\n" + "="*40)
                    print("[DRONE] >>> TEST SPIN COMMAND RECEIVED! <<<")
                    print("="*40 + "\n")
                    try:
                        print(f"[DRONE] Sending /spin to http://{ESP32_DRONE_IP}/spin ...")
                        res = requests.get(f"http://{ESP32_DRONE_IP}/spin", timeout=8)
                        print(f"[DRONE] Physical drone responded: {res.text}")
                        print("[DRONE] Motors spinning for 3 seconds!")
                    except requests.exceptions.ConnectionError:
                        print(f"[DRONE] ERROR: Cannot reach drone at {ESP32_DRONE_IP}")
                        print("[DRONE] Check: Is drone powered on? Same WiFi network?")
                    except Exception as e:
                        print(f"[DRONE] Failed: {e}")

                elif data.get("action") == "LAUNCH":
                    print("\n" + "="*40)
                    print("[DRONE] >>> LAUNCH COMMAND RECEIVED! <<<")
                    print(f"[DRONE] Order ID: {data.get('order_id')}")
                    print(f"[DRONE] Destination: {data.get('destination')}")
                    print("="*40 + "\n")

                    print("[DRONE] Motors armed. Sending spin command to physical drone...")
                    try:
                        res = requests.get(f"http://{ESP32_DRONE_IP}/spin", timeout=8)
                        print(f"[DRONE] Physical drone responded: {res.text}")
                    except Exception as e:
                        print(f"[DRONE] Failed to reach drone: {e}")
                        print("[DRONE] Continuing with software simulation...")

                    await asyncio.sleep(2)

                    print("[DRONE] Airborne. Routing to destination...")
                    for i in range(1, 6):
                        await asyncio.sleep(1.5)
                        print(f"[DRONE] Flight Progress: {i*20}%...")
                        await websocket.send(json.dumps({
                            "status": "in_flight",
                            "progress": i*20
                        }))

                    print("\n[DRONE] Arrived at destination. Delivering payload...")
                    await asyncio.sleep(2)
                    print("[DRONE] Payload delivered! Returning to base.")

                    await websocket.send(json.dumps({
                        "status": "delivered"
                    }))

    except ConnectionRefusedError:
        print("[BRIDGE] ERROR: Backend server is not running on port 8000.")
        print("[BRIDGE] Start it with: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"[BRIDGE] Drone disconnected: {e}")

if __name__ == "__main__":
    asyncio.run(drone_client())
