from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import json, os, time
from collections import defaultdict, deque
from multilateration import wnls_multilateration  # you'll add this
import numpy as np

app = Flask(__name__)
socketio = SocketIO(app)

triangulator_location = [12.24755, 76.715283]

device_measurements = {}
rssi_history = defaultdict(lambda: defaultdict(lambda: deque(maxlen=10)))  # device_id -> coord -> rssi_list

@app.route("/")
def index():
    return render_template("index.html", triangulator=triangulator_location)

@socketio.on("connect")
def handle_connect():
    print("Client connected")

@socketio.on("request_device_data")
def send_device_data():
    if os.path.exists("ble_devices.json"):
        with open("ble_devices.json") as f:
            devices = json.load(f)
        emit("device_data", {
            "devices": devices,
            "triangulator": triangulator_location
        })

@socketio.on("distance_data")
def handle_distance_data(data):
    try:
        device_id = data["device"]
        coords = tuple(data["coords"])
        distance = data["distance"]
        rssi = data["rssi"]
        payload = data.get("payload", "N/A")

        if device_id not in device_measurements:
            device_measurements[device_id] = {}

        # Track RSSI history
        rssi_history[device_id][coords].append(rssi)
        rssi_list = list(rssi_history[device_id][coords])
        rssi_variance = np.var(rssi_list) if len(rssi_list) > 1 else 1.0

        device_measurements[device_id][coords] = {
            "distance": distance,
            "rssi": rssi,
            "variance": rssi_variance,
            "payload": payload,
            "timestamp": time.time()
        }

        print(f"📡 {device_id} from {coords}: distance={distance}m rssi={rssi} var={rssi_variance:.2f}")

        if len(device_measurements[device_id]) >= 3:
            anchors = list(device_measurements[device_id].keys())
            distances = [device_measurements[device_id][c]["distance"] for c in anchors]
            variances = [device_measurements[device_id][c]["variance"] for c in anchors]

            predicted = wnls_multilateration(anchors, distances, variances)

            print(f"📍 Predicted location for {device_id}: {predicted}")

            # Emit individual anchor distances as points (for raw display)
            for anchor_coord, data in device_measurements[device_id].items():
                socketio.emit("raw_distance_point", {
                    "device": device_id,
                    "anchor": anchor_coord,
                    "distance": data["distance"],
                    "payload": data["payload"]
                }, broadcast=True)

            # Emit final multilaterated prediction separately
            socketio.emit("device_prediction", {
                "device": device_id,
                "predicted_location": predicted,
                "sources": anchors,
                "payload": payload
            }, broadcast=True)

    except Exception as e:
        print(f"❌ Error handling distance_data: {e}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
