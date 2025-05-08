import numpy as np
from numpy.linalg import lstsq

def wnls_multilateration(anchors, distances, variances):
    if len(anchors) < 2:
        raise ValueError("At least 2 anchors required")

    def latlon_to_xy(lat, lon):
        R = 6371000
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        return R * lon_rad * np.cos(np.mean(lat_rad)), R * lat_rad

    def xy_to_latlon(x, y):
        R = 6371000
        lat = y / R
        lon = x / (R * np.cos(lat))
        return np.degrees(lat), np.degrees(lon)

    xy_anchors = np.array([latlon_to_xy(lat, lon) for lat, lon in anchors])
    weights = 1 / (np.array(variances) + 1e-6)

    if len(anchors) == 2:
        a, b = xy_anchors
        d1, d2 = distances

        dx, dy = b - a
        d = np.hypot(dx, dy)

        if d > d1 + d2:
            # No intersection; return midpoint as fallback
            midpoint = (a + b) / 2
            return xy_to_latlon(midpoint[0], midpoint[1])

        # Compute intersection points
        a_norm = d1**2 - d2**2 + d**2
        a_div = 2 * d
        x2 = a + (a_norm / a_div) * (b - a) / d

        h = np.sqrt(max(d1**2 - (a_norm / (2 * d))**2, 0))
        rx = -dy * (h / d)
        ry = dx * (h / d)

        intersection1 = x2 + np.array([rx, ry])
        intersection2 = x2 - np.array([rx, ry])

        # Return midpoint of the two intersections
        midpoint = (intersection1 + intersection2) / 2
        return xy_to_latlon(midpoint[0], midpoint[1])

    # WNLS for 3+ anchors
    x = np.average(xy_anchors[:, 0], weights=weights)
    y = np.average(xy_anchors[:, 1], weights=weights)
    position = np.array([x, y])

    for _ in range(10):
        pred_dists = np.linalg.norm(xy_anchors - position, axis=1)
        residuals = pred_dists - distances
        J = (position - xy_anchors) / (pred_dists[:, np.newaxis] + 1e-6)
        W = np.diag(weights)
        try:
            delta = lstsq(J.T @ W @ J, -J.T @ W @ residuals, rcond=None)[0]
        except np.linalg.LinAlgError:
            break
        position += delta
        if np.linalg.norm(delta) < 1e-3:
            break

    return xy_to_latlon(position[0], position[1])

