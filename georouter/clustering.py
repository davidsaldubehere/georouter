import numpy as np
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon

def cluster_geospatial_points(points, eps=.1, min_samples=5):
    """
    Returns a list of shapely Polygon objects that represent the clustered points
    
    eps: The maximum distance between two samples for one to be considered as in the neighborhood of the other (in km)
    min_samples: The number of samples in a neighborhood for a cluster to be considered
    """

    dbscan_obj = DBSCAN(eps=eps/6371, min_samples=min_samples, metric='haversine')

    #Assuming geospatial data, we need to convert the points to radians
    labels = dbscan_obj.fit_predict(np.radians(points))
    
    #filter out the noise points and create cluster list
    clusters = [points[labels == label] for label in np.unique(labels) if label != -1]

    polygons = []
    for cluster in clusters:
        hull = ConvexHull(cluster)
        polygons.append(Polygon(hull.points[hull.vertices]))

    return list(polygons)
