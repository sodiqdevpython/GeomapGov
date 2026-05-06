from sklearn.cluster import DBSCAN
import numpy as np

def cluster_points(coords):
    model = DBSCAN(eps=0.01, min_samples=3)
    labels = model.fit_predict(coords)
    return labels