document.addEventListener("DOMContentLoaded", () => {
    const rawMap = L.map('rawMap', {
        zoomControl: true,
        maxZoom: 22,
    }).setView([12.24755, 76.715283], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 22,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(rawMap);

    const predictionMap = L.map('predictionMap', {
        zoomControl: true,
        maxZoom: 22,
    }).setView([12.24755, 76.715283], 15);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(predictionMap);

    const triangulator = [12.24755, 76.715283];
    L.marker(triangulator).addTo(rawMap).bindPopup("Triangulator (Laptop)");
    L.marker(triangulator).addTo(predictionMap).bindPopup("Triangulator (Laptop)");

    const socket = io("http://localhost:5050"); // Ensure correct connection
    const circles = {}; // for device_data updates

    socket.on("connect", () => {
        socket.emit("request_device_data");
    });

    // 1. Initial device data (BLE JSON fallback)
    socket.on("device_data", (data) => {
        const devices = data.devices;
        const baseLat = data.triangulator[0];
        const baseLng = data.triangulator[1];

        for (const [addr, info] of Object.entries(devices)) {
            const lat = baseLat + (info.distance / 111000); // crude north offset
            const lng = baseLng;

            if (circles[addr]) {
                circles[addr]
                    .setLatLng([lat, lng])
                    .setPopupContent(`${addr}: ${info.distance}m`);
            } else {
                circles[addr] = L.circle([lat, lng], {
                    radius: 1,
                    color: 'red',
                    fill: true,
                    fillOpacity: 0.5
                }).addTo(rawMap).bindPopup(`${addr}: ${info.distance}m`);
            }
        }
    });

    // 2. Live raw distances as blue circles on rawMap
    socket.on("raw_distance_point", (data) => {
        const { anchor, distance, payload } = data;

        const circle = L.circle(anchor, {
            radius: distance,
            color: "blue",
            fillOpacity: 0.1
        }).addTo(rawMap);

        circle.bindPopup(`Device: ${payload}<br>Distance: ${distance.toFixed(2)}m`);
    });

    // 3. Multilaterated prediction as marker on predictionMap
    socket.on("device_prediction", (data) => {
        const { predicted_location, payload } = data;

       console.log("Received multilateration prediction:", data);


        // Check if predicted_location exists and is a valid array with two elements (lat, lng)
        if (Array.isArray(predicted_location) && predicted_location.length === 2) {
            const marker = L.marker(predicted_location).addTo(predictionMap);
            marker.bindPopup(`${payload}`);
        } else {
            console.warn("Invalid predicted location data:", predicted_location);
        }
    });
});
