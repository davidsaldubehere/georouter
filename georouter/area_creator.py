import numpy as np
from shapely import Polygon
from .clustering import cluster_geospatial_points
from scipy.ndimage import gaussian_gradient_magnitude
from skimage.measure import find_contours
from .elevation import get_elevation_data
import re

def parse_polygon_type(polygon, buffer=None):
    try:

        if polygon.geom_type == 'Polygon':
            return [polygon.buffer(buffer)] if buffer else [polygon]
        elif polygon.geom_type == 'MultiPolygon':
            return [poly.buffer(buffer) for poly in polygon.geoms] if buffer else [poly for poly in polygon.geoms]
    except Exception:
        raise ValueError("Polygon type not recognized")

def create_water_area(osm, buffer=.0003):
    """
    Returns a list of shapely Polygon objects sorted by area that represent water areas.
    They are buffered slightly by the buffer parameter so that they can intersect the surrounding edges
    """
    water = osm.get_natural()
    water = water[water['natural'] == 'water']

    #Ensures that only Polygon types are considered since there are some bugs with the shapely library
    polygons = []

    for poly in water['geometry']:
        parsed = parse_polygon_type(poly, buffer)
        if parsed:
            polygons.extend(parsed)
    return sorted(polygons, key=lambda poly: poly.area)

def create_wooded_area(osm, buffer=.0003):
    """
    Returns a list of shapely Polygon objects that represent wooded areas.
    Included osm types are 'tree' 'wood' 'tree_row' 'scrub' 'wetland' 'shrubbery' we're pretty lenient for wooded types

    They are buffered slightly by the buffer parameter so that they can intersect the surrounding edges
    """

    natural = osm.get_natural()
    filtered_natural = natural[natural['natural'].isin(['tree', 'wood', 'tree_row', 'scrub', 'wetland', 'shrubbery'])]
    wooded_polygons = filtered_natural[filtered_natural['geometry'].apply(lambda x: x.geom_type) == 'Polygon']['geometry']
    
    #Now we need to run clustering to combine the points into polygons
    wooded_points = filtered_natural[filtered_natural['geometry'].apply(lambda x: x.geom_type) == 'Point']['geometry']
    coordinated = np.vstack([np.array([point.x, point.y]) for point in wooded_points])
    
    buffered_polygons = []
    for poly in list(wooded_polygons) + cluster_geospatial_points(coordinated):
        buffer_result = poly.buffer(buffer)
        if buffer_result.geom_type == 'Polygon':
            buffered_polygons.append(buffer_result)
        else:
            buffered_polygons.extend([poly in buffer_result.geoms]) #Weird bug where buffer returns a MultiPolygon https://github.com/shapely/shapely/issues/1044
    return buffered_polygons

def create_building_boundary(osm, buffer=.0003, tall_threshold=10, eps=.1, min_samples=5):
    """
    Returns a list of shapely Polygon objects that represent boundaries of areas with buildings. Also returns a listt of shapely Polygon objects that represent tall buildings (list, list)
    """
    buildings = osm.get_buildings()
    assert 'height' in buildings.columns, "No height data available for the selected OSM file"

    buildings_elaborated = [] #list of polygons from potential multipolygons
    for poly in buildings['geometry']:
        parsed = parse_polygon_type(poly)
        if parsed:
            buildings_elaborated.extend(parsed)

    building_points = [polygon.exterior.xy for polygon in buildings_elaborated]
    #Make sure that all non numeric values are removed from the entries in the height column (Some entires are like 6m or 6.0m)
    buildings['height'] = buildings['height'].apply(lambda x: x if x == None or x.replace('.','',1).isdigit() else (re.sub(r'\D', '', x) or '0'))

    filtered_buildings = buildings[buildings['height'].astype(float) > tall_threshold]
    buildings_elaborated = [] #list of polygons from potential multipolygons
    for poly in filtered_buildings['geometry']:
        parsed = parse_polygon_type(poly)
        if parsed:
            buildings_elaborated.extend(parsed)
    tall_building_points = [polygon.exterior.xy for polygon in buildings_elaborated]

    #It has a really weird format with a list of tuples of two arrays that represent the x and y coordinates
    x_points, y_points = [], []
    for tuple_thing in building_points:
        x,y = tuple_thing
        x_points.extend(x)
        y_points.extend(y)
    points = np.vstack(list(zip(x_points, y_points)))
    x_points, y_points = [], []
    for tuple_thing in tall_building_points:
        x,y = tuple_thing
        x_points.extend(x)
        y_points.extend(y)
    tall_points = np.vstack(list(zip(x_points, y_points)))
    buffered_polygons = []

    for poly in cluster_geospatial_points(points, eps=eps, min_samples=min_samples):
        buffer_result = poly.buffer(buffer)
        if buffer_result.geom_type == 'Polygon':
            buffered_polygons.append(buffer_result)
        else:
            buffered_polygons.extend([poly in buffer_result.geoms])

    tall_buffered_polygons = []
    for poly in cluster_geospatial_points(tall_points, eps=eps, min_samples=min_samples):
        buffer_result = poly.buffer(buffer)
        if buffer_result.geom_type == 'Polygon':
            tall_buffered_polygons.append(buffer_result)
        else:
            tall_buffered_polygons.extend([poly for poly in buffer_result.geoms])
    
    return buffered_polygons, tall_buffered_polygons

def create_sharp_elevation_areas(nodes, percentile_cutoff=90, buffer=.0003, download_missing_elevation_files=False, nasa_token=None):
    """
    Returns a list of shapely Polygon objects that represent areas with sharp elevation changes (cliffs, etc).
    These are areas that are in the top percentile_cutoff of elevation changes in the nodes list.
    They are buffered slightly by the buffer parameter so that they can intersect the surrounding edges

    These areas may range in elevation change since we are using relative elevation changes as regions differ significantly in elevation

    Requires the necessary SRTM elevation data files to be present in the HGT_DIR directory if download_missing_elevation_files is set to False (default)
    If you do not have the HGT_DIR environment variable set, it will default to the 'hgt' directory
    """

    lat_min, lat_max = nodes['lat'].min(), nodes['lat'].max()
    lon_min, lon_max = nodes['lon'].min(), nodes['lon'].max()


    elevation, lon_labels, lat_labels = get_elevation_data(lat_min, lat_max, lon_min, lon_max, download=download_missing_elevation_files, nasa_token=nasa_token)
    gradient_magnitude = gaussian_gradient_magnitude(elevation, sigma=1)
    sharp_cutoff = gradient_magnitude > np.percentile(gradient_magnitude, percentile_cutoff)

    #Create shapely polygons from the contours
    polygons = []
    for contour in find_contours(sharp_cutoff, .5):
        coords = [(lon_labels[int(p[1])], lat_labels[int(p[0])]) for p in contour]
        polygon = Polygon(coords)
        
        if polygon.is_valid:
            polygon = polygon.buffer(buffer) # Buffer the polygon slightly
            if polygon.geom_type == 'Polygon':
                polygons.append(polygon)
            else:
                polygons.extend([poly for poly in polygon.geoms])

    return polygons