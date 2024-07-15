from pyrosm import OSM
from .area_creator import create_building_boundary, create_wooded_area, create_water_area, create_sharp_elevation_areas
import numpy as np
from .edge_classifier import classify_edge_speed
from shapely import LineString
from .core import haversine
import georouter.path_finding as path_finding # type: ignore
def get_closest_node(graph, latitude, longitude):
    """Returns the index of the graph node that is closest to the given latitude and longitude"""
    min_distance = float('inf')
    closest_node = None
    for node in graph.vs:
        node_attrs = node.attributes()
        distance = haversine(node_attrs['lat'], node_attrs['lon'], latitude, longitude)
        if distance < min_distance:
            min_distance = distance
            closest_node = node
    assert min_distance < 10, f"Closest node is {min_distance} km away. Too far away to be considered."
    return closest_node

def create_route_from_graph(graph, start_location, end_location, negative_edges = True):
    """
    Returns a list of nodes that represent the shortest path between the start and end location
    
    The start and end location should be a tuple of the form (lat, lon)

    If using custom weights, the graph should have a 'user_weight' attribute for each edge that represents the weight of the edge

    If using negative_edges = True, the graph will use a custom shortest path algorithm to prevent negative cycles
    Otherwise, it will use iGraph's built-in shortest path algorithm which is faster but can't handle negative weights
    """
    latitude, longitude = start_location[0], start_location[1]
    start_node = get_closest_node(graph, latitude, longitude)
    latitude, longitude = end_location[0], end_location[1]
    end_node = get_closest_node(graph, latitude, longitude)
    assert start_node is not None, "Start node not found"
    assert end_node is not None, "End node not found"

    if negative_edges:
        edge_list = [[float(edge.source), float(edge.target), edge['user_weight']] for edge in graph.es]
        path = path_finding.bellman_ford_no_intersections(edge_list, len(graph.vs), start_node.index, end_node.index)
        return path
    else:
        path = graph.get_shortest_paths(start_node, end_node, weights='user_weight', output='vpath')[0]
        return path

    
def process_edges(osm_file_name, preference_dict, buffer=.0003, tall_threshold=10, use_negative_weights = True, download_missing_elevation_files=False, nasa_token=None):
    """
    Returns an iGraph instance of the osm data with edges weighted according to the preferences.

    osm_file_name: The name of the OSM file to use
    preference_dict: A dictionary that contains the preferences for the route
    buffer: The buffer to add to polygon area such that it intersects with the road network
    tall_threshold: The threshold for a building to be considered tall
    use_negative_weights: Negative weights are used to incentivize the algorithm to travel to certain areas.
    This can be very effective for routing, but scales badly with the number of nodes during route calculation as negative cycle mitigation is computationally expensive.
    download_missing_elevation_files: If set to True, it will download missing elevation files
    nasa_token: The NASA bearer token to use for downloading elevation data. You can get one from urs.earthdata.nasa.gov

    The preference_dict should have the following keys:
    'sharp_elevation_change': A float that represents the importance of sharp elevation changes
    'building_density': A float that represents the importance of building density
    'tall_buildings': A float that represents the importance of tall buildings
    'wooded_areas': A float that represents the importance of greenery
    'water': A float that represents the importance of water
    'high_speed': A float that represents the importance of high speed roads
    'low_speed': A float that represents the importance of low speed roads

    Preference values MUST be between -1 and 1. Negative values represent areas to avoid, positive values represent areas to prefer.

    If you would prefer to use other values, you can weight the edges yourself and use create_route on the resulting graph
    """
    osm = OSM(osm_file_name)
    nodes, edges = osm.get_network(nodes=True, network_type="driving")
    assert preference_dict.keys() == {'sharp_elevation_change', 'tall_buildings', 'wooded_areas', 'water', 'high_speed', 'low_speed', 'building_density'}, "preference_dict must have the keys 'sharp_elevation_change', 'tall_buildings', 'wooded_areas', 'water', 'high_speed', 'low_speed'"

    if use_negative_weights:
        #we must shift the values to work with the shortest path algorithm
        for key, value in preference_dict.items():
            assert -1 <= value <= 1, f"{key} should be between -1 and 1"
            if value < 0:
                preference_dict[key] = np.exp(5*value)
            elif value > 0:
                preference_dict[key] = -(np.exp(-12*value + 7) + 9.99)
            else:
                preference_dict[key] = 1
    else:
        for key, value in preference_dict.items():
            assert -1 <= value <= 1, f"{key} should be between -1 and 1"
            preference_dict[key] = np.exp(-3*value)

    wooded_area = create_wooded_area(osm, buffer=buffer)
    water_area = create_water_area(osm, buffer=buffer)
    building_area, tall_building_area = create_building_boundary(osm, buffer=buffer, tall_threshold=tall_threshold)
    sharp_elevation_area = create_sharp_elevation_areas(osm._nodes, buffer=buffer, download_missing_elevation_files=download_missing_elevation_files, nasa_token=nasa_token)
    edges = classify_edge_speed(edges)


    edges['user_weight'] = edges['length'].copy() * .1 if use_negative_weights else edges['length'].copy()
    for i, edge in edges.iterrows():
        edge_coords = LineString(edge['geometry'])
        edge_weight = edge['user_weight']
        edge_length = edge['length']
        for polygon in building_area:
            if edge_coords.intersects(polygon):
                edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['building_density'] if use_negative_weights else edge_length * preference_dict['building_density']
        for polygon in tall_building_area:
            if edge_coords.intersects(polygon):
                edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['tall_buildings'] if use_negative_weights else edge_length * preference_dict['tall_buildings']
        for polygon in wooded_area:
            if edge_coords.intersects(polygon):
                edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['wooded_areas'] if use_negative_weights else edge_length * preference_dict['wooded_areas']
        for polygon in water_area:
            if edge_coords.intersects(polygon):
                edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['water'] if use_negative_weights else edge_length * preference_dict['water']
        for polygon in sharp_elevation_area:
            if edge_coords.intersects(polygon):
                edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['sharp_elevation_change'] if use_negative_weights else edge_length * preference_dict['sharp_elevation_change']
        if edges.at[i, 'speed_classification'] == 'high':
            edges.at[i, 'user_weight'] = edge_weight + edge_length / preference_dict['high_speed'] if use_negative_weights else edge_length * preference_dict['high_speed']
        elif edges.at[i, 'speed_classification'] == 'low':
            edges.at[i, 'user_weight'] = edge_weight +edge_length / preference_dict['low_speed'] if use_negative_weights else edge_length * preference_dict['low_speed']
    return osm.to_graph(nodes, edges)