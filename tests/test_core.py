#Test route creation with pytest 
from georouter import area_creator, routes
from pyrosm import OSM
import os

"""
----------
MAKE SURE TO BUILD THE C MODULES PRIOR TO RUNNING THIS TEST

To build the C modules, run the following command in the root directory of the project:
python setup.py build_ext --inplace
_________
"""

def test_area_creation():
    osm = OSM(os.path.join(os.path.dirname(__file__), "testing_data", "state_college_large.osm.pbf"))
    water = area_creator.create_water_area(osm)
    wooded = area_creator.create_wooded_area(osm)
    building, tall_building = area_creator.create_building_boundary(osm)
    cliffs = area_creator.create_sharp_elevation_areas(osm._nodes, nasa_token=os.environ['NASA_TOKEN'], download_missing_elevation_files=True)
    assert len(water) > 0
    assert len(wooded) > 0
    assert len(building) > 0
    assert len(tall_building) > 0    
    assert len(cliffs) > 0

def test_edge_classification():
    osm = OSM(os.path.join(os.path.dirname(__file__), "testing_data", "state_college_large.osm.pbf"))
    nodes, edges = osm.get_network(nodes=True, network_type="driving")
    classified_edges = routes.classify_edge_speed(edges)
    assert len(classified_edges) == len(edges)
    assert 'speed_classification' in classified_edges.columns

def test_route_creation_positive():
    preference_dict = {
        'sharp_elevation_change': 0,
        'building_density': 0,
        'tall_buildings': 0,
        'wooded_areas': 0,
        'water': 0,
        'high_speed': 1,
        'low_speed': -1
    }
    graph = routes.process_edges(osm_file_name=os.path.join(os.path.dirname(__file__), "testing_data", "state_college_large.osm.pbf"), preference_dict=preference_dict, download_missing_elevation_files=True, nasa_token=os.environ['NASA_TOKEN'], use_negative_weights=False)
    start_location = (40.783708, -77.828748)
    end_location = (40.827601, -77.877053)
    route = routes.create_route_from_graph(graph, start_location, end_location, negative_edges=False)
    assert len(route) > 0

def test_route_creation_negative():
    preference_dict = {
        'sharp_elevation_change': 0,
        'building_density': 0,
        'tall_buildings': 0,
        'wooded_areas': 0,
        'water': 0,
        'high_speed': -1,
        'low_speed': 0
    }
    graph = routes.process_edges(osm_file_name=os.path.join(os.path.dirname(__file__), "testing_data", "state_college_large.osm.pbf"), preference_dict=preference_dict, download_missing_elevation_files=True, nasa_token=os.environ['NASA_TOKEN'], use_negative_weights=True)
    start_location = (40.783708, -77.828748)
    end_location = (40.827601, -77.877053)
    route = routes.create_route_from_graph(graph, start_location, end_location, negative_edges=True)

    assert len(route) > 0