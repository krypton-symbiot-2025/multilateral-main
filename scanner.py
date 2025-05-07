import asyncio
from bleak import BleakScanner
import json
from datetime import datetime
from collections import deque
import socket
from datetime import datetime
from collections import deque

class BleScanner:
    def __init__(self, triangulator_position=(0, 0), window_size=5, kalman_q=0.01, kalman_r=0.8):
        self.triangulator_position = triangulator_position
        self.window_size = window_size
        self.kalman_q = kalman_q
        self.kalman_r = kalman_r
        self.devices_seen = {}
        self.filtered_rssi_buffer = {}
        self.kalman_state = {}
        self.kalman_covariance = {}


    def send_data_to_app(self, data):
        """
        Send updated device data to the app via a socket connection
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall(data.encode())
    def estimate_distance(self, rssi, tx_power=-59, n=2.7):
        """
        Estimate distance from RSSI using the Log-distance Path Loss Model.
        """
        return round(10 ** ((tx_power - rssi) / (10 * n)), 2)

    def moving_average(self, address, new_rssi):
        """
        Apply moving average filtering to smooth the RSSI.
        """
        buffer = self.filtered_rssi_buffer.setdefault(address, deque(maxlen=self.window_size))
        buffer.append(new_rssi)
        return sum(buffer) / len(buffer)

    def kalman_filter(self, address, measured_rssi):
        """
        Apply the Kalman filter for noise reduction in RSSI.
        """
        x = self.kalman_state.get(address, measured_rssi)
        p = self.kalman_covariance.get(address, 1)

        # Predict
        x_pred = x
        p_pred = p + self.kalman_q

        # Update
        k = p_pred / (p_pred + self.kalman_r)
        x_new = x_pred + k * (measured_rssi - x_pred)
        p_new = (1 - k) * p_pred

        self.kalman_state[address] = x_new
        self.kalman_covariance[address] = p_new

        return x_new

    async def callback(self, device, advertisement_data):
        """
        Callback function to handle received BLE advertisements.
        """
        # Try to get payload from manufacturer_data, fallback to local_name or service_data
        payload = None

        if advertisement_data.manufacturer_data:
            for _, v in advertisement_data.manufacturer_data.items():
                payload = v.decode("utf-8", errors="ignore").strip()
        elif advertisement_data.local_name:
            payload = advertisement_data.local_name.strip()
        elif advertisement_data.service_data:
            for _, v in advertisement_data.service_data.items():
                payload = v.decode("utf-8", errors="ignore").strip()

        # Skip if no usable payload found
        if not payload:
            return

        try:
            raw_rssi = device.rssi

            # Filtered RSSI
            filtered_rssi = self.kalman_filter(device.address, raw_rssi)
            smoothed_rssi = self.moving_average(device.address, filtered_rssi)

            # Adaptive path-loss exponent
            n = 2.0 if smoothed_rssi > -65 else 3.2 if smoothed_rssi < -80 else 2.7
            distance = self.estimate_distance(smoothed_rssi, n=n)

            self.devices_seen[device.address] = {
                "payload": payload,
                "rssi": round(smoothed_rssi, 2),
                "distance": distance,
                "last_seen": datetime.now().isoformat()
            }

            # Save the updated dictionary to a JSON file
            with open("ble_devices.json", "w") as f:
                json.dump(self.devices_seen, f, indent=2)

            print(
                f"🛰 {device.address} | RSSI: {raw_rssi} → {smoothed_rssi:.2f} | Distance: {distance}m | Payload: {payload}")

        except Exception as e:
            print(f"Error parsing device {device.address}: {e}")

    async def run_scanner(self):
        """
        Start scanning for BLE devices and process the advertisements.
        """
        print("🔍 Scanning for BLE advertisements...")

        scanner = BleakScanner(self.callback)
        await scanner.start()

        while True:
            await asyncio.sleep(1)  # Keep scanning indefinitely

if __name__ == "__main__":
    # Initialize the BLE scanner
    scanner = BleScanner()

    # Run the scanner asynchronously
    asyncio.run(scanner.run_scanner())

