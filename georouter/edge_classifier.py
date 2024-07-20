import numpy as np
from shapely.geometry import LineString

def parse_speed(speed):
    """
    Parses the speed string and returns the speed as an integer.
    """
    try:
        if speed is not None and speed != "none" and speed.isnumeric():
            return int(speed.split(' ')[0])
        else:
            return 0
    except:
        print(f"\nCould not parse speed: {speed}\n")
        raise ValueError("Could not parse speed")
    


def classify_edge_speed(edges, high_speed_threshold=50, low_speed_threshold=20):
    """
    Input is a pyrosm edge dataframe. Adds a new column to the dataframe with the speed classification of the edge.

    Thresholds are in mph.
    """

    # Create a new column for the speed classification
    edges["speed_classification"] = 0
    edges["speed_classification"] = np.where(edges['maxspeed'].apply(lambda x: parse_speed(x)) >= high_speed_threshold, "high",
                                             np.where(edges['maxspeed'].apply(lambda x: parse_speed(x)) <= low_speed_threshold, "low", None))

    return edges