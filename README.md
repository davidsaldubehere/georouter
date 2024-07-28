# GeoRouter

GeoRouter is a python library that provides a highly customizable offline routing engine that allows users to find routes based on scenery and other typical navigation preferences. In addition, GeoRouter provides powerful tools for OSM (OpenStreetMap) and SRTM (Shuttle Radar Topography Mission) data manipulation and visualization. User's can easily get accurate elevation data by simply providing a latitude and longitude bounding box.

GeoRouter currently supports two routing algorithms: A\* and a custom Bellman-Ford algorithm. The A\* algorithm shortens or lengths corresponding edges based on the user's scenery preferences while the Bellman-Ford algorithm directly incentivizes edges with negative weights which virtually guarantees routes will align with the user's scenery preferences. The Bellman-Ford algorithm is therefore more powerful, but extra compute is needed to prevent negative cycles from forming via backtracking.

## Installation

    pip install georouter

You will also need OSM datasets from either [BBBike](https://extract.bbbike.org/) or [Geofabrik](https://download.geofabrik.de/). The datasets should be in the form of .osm.pbf files.

SRTM datasets are automatically downloaded by GeoRouter, but a NASA Earthdata account is required as well as an account token.

## Examples

---

Plot a nice drive through Paris that sticks to the Marne river as much as possible

```python
from georouter import routes
from pyrosm import OSM
import matplotlib.pyplot as plt
import os
import numpy as np

#We want to incentivize a route that goes near water
preference_dict = {
    'sharp_elevation_change': 0,
    'building_density': 0,
    'tall_buildings': 0,
    'wooded_areas': 0,
    'water': 1,
    'high_speed': 0,
    'low_speed': 0
}
#for large datasets you'll want to process the edges separately (time consuming)
#I am using https://extract.bbbike.org/?sw_lng=2.496&sw_lat=48.833&ne_lng=2.581&ne_lat=48.874&format=osm.pbf&city=asdfasdf&lang=en
graph = routes.process_edges(osm_file_name="paris_small.osm.pbf", preference_dict=preference_dict, download_missing_elevation_files=True, nasa_token=os.environ['NASA_TOKEN'], use_negative_weights=True, buffer=.0008)
start_location = (48.83715, 2.5)
end_location = (48.85879, 2.57970)
route = routes.create_route_from_graph(graph, start_location, end_location, negative_edges=True)

#Lets plot the route
nodes, edges = OSM("paris_small.osm.pbf").get_network(nodes=True, network_type="driving")
ax = edges.plot()
vseq = graph.vs
path_coords_lat = np.array([vseq[i].attributes()['lat'] for i in route])
path_coords_lon = np.array([vseq[i].attributes()['lon'] for i in route])
ax.scatter(path_coords_lon, path_coords_lat, color='red', s=15)
plt.show()
```
<img width="994" alt="Screenshot 2024-07-28 at 2 56 35 PM" src="https://github.com/user-attachments/assets/cf92fd65-aab6-48bf-bcdf-98acffd05b90">
<img width="991" alt="Screenshot 2024-07-20 at 6 17 37 PM" src="https://github.com/user-attachments/assets/79c17cb1-f318-448f-a770-d93768a3662e">
As you can see, the value 1 may be a bit too strong which causes the route the jump across the river and then back again

---

Find a non-intersecting drive through downtown Manhattan that goes by as many tall buildings as possible using custom graph

```python
from georouter import area_creator, routes
import matplotlib.pyplot as plt
from pyrosm import OSM
from shapely.geometry import LineString
import numpy as np

#Using https://extract.bbbike.org/?sw_lng=-74.021&sw_lat=40.7&ne_lng=-73.978&ne_lat=40.721&format=osm.pbf&city=Manhattan&lang=en
osm = OSM("nyc.osm.pbf")

#We will consider super tall buildings ≅ 230m or greater
building_areas = area_creator.create_building_boundary(osm = osm, eps=.01, buffer=.0005, tall_threshold=230, min_samples=1)[1] #returns only the tall buildings

#Let's process the edges ourselves to demonstrate how to use routing on a custom network
nodes, edges = osm.get_network(nodes=True, network_type="driving")

#Our goal is to find a route in downtown Manhattan that hits as many tall buildings as possible

#We will create a new column for the user weight with some default value
edges['user_weight'] = edges['length'].copy() * .1

#We will iterate over the edges and set -400 to the user weight if the edge intersects with a tall building area
#Using very large negative values can result in slow compute times since negative cycle prevention becomes tougher
#The built in edge processor uses scaled values proportional to the edge length to avoid this
#Negative values may seem counterintuitive, but they are used to incentivize the shortest path algorithm to go to certain areas
for i, edge in edges.iterrows():
    edge_coords = LineString(edge['geometry'])
    edge_weight = edge['user_weight']
    for polygon in building_areas:
        if edge_coords.intersects(polygon):
            edges.at[i, 'user_weight'] = -400 #doesn't need to be this large, but we want to make sure the route goes through the tall buildings

#convert the nodes and edges to an iGraph using pyrosm
graph = osm.to_graph(nodes, edges)
start_location = (40.70314, -74.01339)
end_location = (40.72021, -73.99358)

#Find the optimal route
route = routes.create_route_from_graph(graph, start_location, end_location, negative_edges=True)

# Plot all the information
ax = edges.plot(color="black", linewidth=0.5)
vseq = graph.vs
path_coords_lat = np.array([vseq[i].attributes()['lat'] for i in route])
path_coords_lon = np.array([vseq[i].attributes()['lon'] for i in route])
ax.scatter(path_coords_lon, path_coords_lat, color='red', s=10)
for area in building_areas:
    x, y = area.exterior.xy
    ax.plot(x, y)
plt.show()
```

<img width="1083" alt="Screenshot 2024-07-28 at 3 28 57 PM" src="https://github.com/user-attachments/assets/4e215868-8e59-42bc-b3af-d862786aded5">
We can see that it doesn't hit all areas with tall buildings, but this is because the shortest path algorithm doesn't allow for path intersections

---

Utility example - Find driveable places with no nearby buildings

```python
from georouter import area_creator
import matplotlib.pyplot as plt
from pyrosm import OSM

# Find locations with no buildings
osm = OSM("state_college_large.osm.pbf")
# eps is the maximum distance between two samples for one to be considered as in the neighborhood of the other (in km)
# default is .1, you can and probably should change it depending on how urban the area is
# We will also increase the buffer added to the polygons so that we don't classifiy nodes as isolate when they are not
building_areas = area_creator.create_building_boundary(osm = osm, eps=.03, buffer=.001)[0] #returns only the buildings not the tall buildings

# Plot the areas
fig, ax = plt.subplots()
for area in building_areas:
    x, y = area.exterior.xy
    ax.plot(x, y)

# Okay let's get drivable nodes that are not inside these building areas
nodes, edges = osm.get_network(nodes=True, network_type="driving")
nodes = nodes[~nodes['geometry'].apply(lambda x: any([area.contains(x) for area in building_areas]))]
# Plot the nodes
x, y = nodes['geometry'].x, nodes['geometry'].y
ax.scatter(x, y, c='red')
plt.show()
```

<img width="1336" alt="Screenshot 2024-07-25 at 4 58 24 PM" src="https://github.com/user-attachments/assets/e3bd9d81-07f2-4611-bc3d-031bdf896539">

---

Most of the points are part of highways, but you can see that it did pick up on an isolated area that appears to be a quarry

<img width="389" alt="Screenshot 2024-07-25 at 5 08 56 PM" src="https://github.com/user-attachments/assets/84edeb76-00b2-40bb-9c7c-8f80d3bc6e3c"> ![Screenshot 2024-07-25 at 5 07 55 PM](https://github.com/user-attachments/assets/374329d1-9fdc-42a5-b2cb-160849d8e652)

---

Utility example - Easily get SRTM elevation data for bounding boxes

```python
from georouter import elevation
import matplotlib.pyplot as plt
import os
# Terrain map of Pennsylvania
data, lon_vals, lat_vals = elevation.get_elevation_data(min_lat = 39.7, max_lat = 42.3, min_lon = -80.5, max_lon = -74.7, download=True, nasa_token=os.getenv("NASA_TOKEN"))

#plot the terrain map
plt.imshow(data, cmap='terrain', extent=(-80.5, -74.7, 39.7, 42.3))
plt.colorbar(label='Elevation [m]')
plt.title('Elevation data')
plt.show()
```

<img width="1289" alt="Screenshot 2024-07-27 at 11 14 41 PM" src="https://github.com/user-attachments/assets/87e59cb2-98c5-4d7b-8940-d30d8abd7268">

## Usage

```python
from georouter import area_creator, elevation, routes
```

### Core API Usage

### area_creator

#### `create_water_area(osm, buffer=0.0003)`

Returns a list of shapely `Polygon` objects sorted by area that represent water areas. These polygons are buffered slightly by the buffer parameter to intersect the surrounding edges.

- **Parameters:**

  - `osm` (OSM): The OSM object containing OpenStreetMap data.
  - `buffer` (float, optional): The buffer distance to apply to each polygon. Default is 0.0003.

- **Returns:**
  - `List[Polygon]`: A list of shapely `Polygon` objects representing water areas.

#### `create_wooded_area(osm, buffer=0.0003)`

Returns a list of shapely `Polygon` objects that represent wooded areas. Included OSM types are 'tree', 'wood', 'tree_row', 'scrub', 'wetland', and 'shrubbery'. These polygons are buffered slightly by the buffer parameter to intersect the surrounding edges.

- **Parameters:**

  - `osm` (OSM): The OSM object containing OpenStreetMap data.
  - `buffer` (float, optional): The buffer distance to apply to each polygon. Default is 0.0003.

- **Returns:**
  - `List[Polygon]`: A list of shapely `Polygon` objects representing wooded areas.

#### `create_building_boundary(osm, buffer=0.0003, tall_threshold=10, eps=0.1, min_samples=5)`

Returns a list of shapely `Polygon` objects that represent boundaries of areas with buildings, and a list of shapely `Polygon` objects that represent tall buildings.

- **Parameters:**

  - `osm` (OSM): The OSM object containing OpenStreetMap data.
  - `buffer` (float, optional): The buffer distance to apply to each polygon. Default is 0.0003.
  - `tall_threshold` (int, optional): The height threshold to classify tall buildings. Default is 10.
  - `eps` (float, optional): The maximum distance between two samples for one to be considered as in the neighborhood of the other (in km). Default is 0.1.
  - `min_samples` (int, optional): The miniumum number of samples in the neighborhood required to form a cluster. Default is 5.

- **Returns:**
  - `Tuple[List[Polygon], List[Polygon]]`: A tuple containing two lists of shapely `Polygon` objects representing building boundaries and tall buildings, respectively.

#### `create_sharp_elevation_areas(nodes, percentile_cutoff=90, buffer=0.0003, download_missing_elevation_files=False, nasa_token=None)`

Returns a list of shapely `Polygon` objects that represent areas with sharp elevation changes (e.g., cliffs). These areas are in the top `percentile_cutoff` of elevation changes in the nodes list. The polygons are buffered slightly by the buffer parameter to intersect the surrounding edges.

- **Parameters:**

  - `nodes` (DataFrame): A DataFrame containing latitude and longitude information of nodes.
  - `percentile_cutoff` (int, optional): The percentile cutoff for determining sharp elevation changes. Default is 90.
  - `buffer` (float, optional): The buffer distance to apply to each polygon. Default is 0.0003.
  - `download_missing_elevation_files` (bool, optional): Whether to download missing elevation files if not present. Default is False.
  - `nasa_token` (str, optional): NASA API token for downloading elevation data, if necessary.

- **Returns:**
  - `List[Polygon]`: A list of shapely `Polygon` objects representing areas with sharp elevation changes.

---

### elevation

#### `SRTM_SAMPLE_DENSITY`

- **Description:** Number of samples per file for 30m resolution SRTM data.
- **Type:** `int`
- **Value:** `3601`

#### `HGTDIR`

- **Description:** Directory to store HGT files.
- **Type:** `str`
- **Value:** Obtained from the environment variable `HGT_DIR`, default is `'hgt'`.

### Functions

#### `get_file_names(min_lat, max_lat, min_lon, max_lon, download=False, nasa_token=None)`

Returns a list of file paths that contain the elevation data for the given bounding box.

- **Parameters:**

  - `min_lat` (float): Minimum latitude.
  - `max_lat` (float): Maximum latitude.
  - `min_lon` (float): Minimum longitude.
  - `max_lon` (float): Maximum longitude.
  - `download` (bool, optional): If `True`, download missing files. Default is `False`.
  - `nasa_token` (str, optional): NASA token for downloading files.

- **Returns:**

  - `List[str]`: List of file paths.

- **Notes:**
  - If `download` is set to `True`, the function will attempt to download missing files using the provided `nasa_token`.
  - The bounding box should not cross hemispheres.

#### `get_elevation_data(min_lat, max_lat, min_lon, max_lon, download=False, nasa_token=None)`

Returns the elevation data for the given bounding box via NASA's SRTM data.

- **Parameters:**

  - `min_lat` (float): Minimum latitude.
  - `max_lat` (float): Maximum latitude.
  - `min_lon` (float): Minimum longitude.
  - `max_lon` (float): Maximum longitude.
  - `download` (bool, optional): If `True`, download missing files. Default is `False`.
  - `nasa_token` (str, optional): NASA token for downloading files.

- **Returns:**

  - `Tuple[np.ndarray, np.ndarray, np.ndarray]`: Numpy array of elevation data, longitude values, and latitude values.

- **Notes:**
  - The function uses the `get_file_names` function to retrieve or download the necessary HGT files.
  - The bounding box should not cross hemispheres.

#### `read_elevation_data_from_files(hgt_files, min_lat, max_lat, min_lon, max_lon)`

Reads the elevation data from the given HGT files and returns a numpy array.

- **Parameters:**

  - `hgt_files` (List[str]): List of file paths to HGT files.
  - `min_lat` (float): Minimum latitude.
  - `max_lat` (float): Maximum latitude.
  - `min_lon` (float): Minimum longitude.
  - `max_lon` (float): Maximum longitude.

- **Returns:**

  - `Tuple[np.ndarray, np.ndarray, np.ndarray]`: Numpy array of elevation data, longitude values, and latitude values.

- **Notes:**
  - If reading from multiple files, the files must be ordered from north to south and west to east.
  - The resulting numpy array includes data for each 30m x 30m square in the bounding box.

---

### routes

#### `get_closest_node(graph, latitude, longitude)`

Returns the index of the graph node that is closest to the given latitude and longitude.

- **Parameters:**

  - `graph` (Graph): The graph containing nodes with latitude and longitude attributes.
  - `latitude` (float): The latitude of the target location.
  - `longitude` (float): The longitude of the target location.

- **Returns:**
  - `Node`: The closest node in the graph.

#### `create_route_from_graph(graph, start_location, end_location, negative_edges=True)`

Returns a list of nodes that represent the shortest path between the start and end location.

- **Parameters:**

  - `graph` (Graph): The graph containing the nodes and edges.
  - `start_location` (tuple): The starting location as a tuple of the form (lat, lon).
  - `end_location` (tuple): The ending location as a tuple of the form (lat, lon).
  - `negative_edges` (bool, optional): Whether to use a custom shortest path algorithm to handle negative edges. Default is True.

- **Returns:**
  - `List[int]`: A list of node indices representing the shortest path.

#### `process_edges(osm_file_name, preference_dict, buffer=0.0003, tall_threshold=10, use_negative_weights=True, download_missing_elevation_files=False, nasa_token=None)`

Returns an iGraph instance of the OSM data with edges weighted according to the preferences.

- **Parameters:**

  - `osm_file_name` (str): The name of the OSM file to use.
  - `preference_dict` (dict): A dictionary that contains the preferences for the route.
  - `buffer` (float, optional): The buffer to add to polygon areas so that they intersect with the road network. Default is 0.0003.
  - `tall_threshold` (int, optional): The threshold for a building to be considered tall. Default is 10.
  - `use_negative_weights` (bool, optional): Whether to use negative weights to incentivize the algorithm to travel to certain areas. Default is True.
  - `download_missing_elevation_files` (bool, optional): Whether to download missing elevation files. Default is False.
  - `nasa_token` (str, optional): The NASA bearer token to use for downloading elevation data.

- **Returns:**
  - `Graph`: An iGraph instance with edges weighted according to the preferences.

## TODO

- [ ] Add support for Southern Hemisphere SRTM data
- [ ] Increase speed of Bellman-Ford algorithm via caching previous paths for negative cycle detection
- [ ] Add more routing preferences
- [ ] Remove utility roads from routing graph
- [ ] Improve edge preprocessing via parallelization
- [ ] Add a save and load function for graphs and preprocessed edges
- [ ] Add coastline as a water body since no ocean polygons are saved in OSM
- [ ] Expand support for multipolygons in area creation
- [ ] Add intermediate plotting for each step
