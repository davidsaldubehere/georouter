# GeoRouter

---

GeoRouter is a python library that provides a highly customizable offline routing engine that allows users to find routes based on scenery and other typical navigation preferences. In addition, GeoRouter provides powerful tools for OSM (OpenStreetMap) and SRTM (Shuttle Radar Topography Mission) data manipulation and visualization. User's can easily get accurate elevation data by simply providing a latitude and longitude bounding box.

GeoRouter currently supports two routing algorithms: A\* and a custom Bellman-Ford algorithm. The A\* algorithm shortens or lengths corresponding edges based on the user's scenery preferences while the Bellman-Ford algorithm directly incentivizes edges with negative weights which virtually guarantees routes will align with the user's scenery preferences. The Bellman-Ford algorithm is therefore more powerful, but extra compute is needed to prevent negative cycles from forming via backtracking.

## Installation

    pip install georouter

You will also need OSM datasets from either [BBBike](https://extract.bbbike.org/) or [Geofabrik](https://download.geofabrik.de/). The datasets should be in the form of .osm.pbf files.

SRTM datasets are automatically downloaded by GeoRouter, but a NASA Earthdata account is required as well as an account token.

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

#### `create_building_boundary(osm, buffer=0.0003, tall_threshold=10)`

Returns a list of shapely `Polygon` objects that represent boundaries of areas with buildings, and a list of shapely `Polygon` objects that represent tall buildings.

- **Parameters:**

  - `osm` (OSM): The OSM object containing OpenStreetMap data.
  - `buffer` (float, optional): The buffer distance to apply to each polygon. Default is 0.0003.
  - `tall_threshold` (int, optional): The height threshold to classify tall buildings. Default is 10.

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
