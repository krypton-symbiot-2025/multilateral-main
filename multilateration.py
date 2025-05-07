import numpy as np
from numpy.linalg import lstsq

def wnls_multilateration(anchors, distances, variances):
    if len(anchors) < 3:
        raise ValueError("At least 3 anchors required")

    def latlon_to_xy(lat, lon):
        R = 6371000  # Earth radius
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        return R * lon_rad * np.cos(np.mean(lat_rad)), R * lat_rad

    xy_anchors = np.array([latlon_to_xy(lat, lon) for lat, lon in anchors])
    weights = 1 / (np.array(variances) + 1e-6)

    x = np.average(xy_anchors[:, 0], weights=weights)
    y = np.average(xy_anchors[:, 1], weights=weights)
    position = np.array([x, y])

    for _ in range(10):
        pred_dists = np.linalg.norm(xy_anchors - position, axis=1)
        residuals = pred_dists - distances
        J = (position - xy_anchors) / pred_dists[:, np.newaxis]
        W = np.diag(weights)
        try:
            delta = lstsq(J.T @ W @ J, -J.T @ W @ residuals, rcond=None)[0]
        except np.linalg.LinAlgError:
            break
        position += delta
        if np.linalg.norm(delta) < 1e-3:
            break

    return position.tolist()
