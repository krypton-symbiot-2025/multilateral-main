# app.py
from flask import Flask
import folium
import json
import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
triangulator_location = [12.9716, 77.5946]

@app.route("/")
def show_map():
    m = folium.Map(location=triangulator_location, zoom_start=20)
    folium.Marker(triangulator_location, tooltip="Triangulator (Laptop)").add_to(m)

    if os.path.exists("ble_devices.json"):
        with open("ble_devices.json") as f:
            devices = json.load(f)

        for addr, data in devices.items():
            est_lat = triangulator_location[0] + (data["distance"] / 111000)  # ~111 km per degree
            est_lng = triangulator_location[1]
            folium.Circle(
                [est_lat, est_lng],
                radius=5,
                popup=f"{addr}: {data['distance']:.2f}m",
                color='red',
                fill=True,
                fill_opacity=0.5
            ).add_to(m)

    return m._repr_html_()

if __name__ == "__main__":
    app.run(debug=True)

