import numpy as np
from shapely.geometry import LineString

def classify_edge_speed(edges, high_speed_threshold=50, low_speed_threshold=20):
    """
    Input is a pyrosm edge dataframe. Adds a new column to the dataframe with the speed classification of the edge.

    Thresholds are in mph.
    """

    # Create a new column for the speed classification
    edges["speed_classification"] = 0
    edges["speed_classification"] = np.where(edges['maxspeed'].apply(lambda x: int(x.split(' ')[0]) if (x is not None and x != "none" ) else 0) >= high_speed_threshold, "high",
                                             np.where(edges['maxspeed'].apply(lambda x: int(x.split(' ')[0]) if (x is not None and x != "none" ) else 0) <= low_speed_threshold, "low", None))

    return edges