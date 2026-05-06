import numpy as np
from math import radians, sin, cos, sqrt, atan2

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2-lat1)
    dlon = radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def compute_density(points, eps=0.5):
    density = []
    for i, p in enumerate(points):
        count = 0
        for j, q in enumerate(points):
            if haversine(p[0], p[1], q[0], q[1]) < eps:
                count += 1
        density.append(count)
    return density