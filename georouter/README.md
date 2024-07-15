# GeoRouter

---

GeoRouter is a python library that provides a highly customizable offline routing engine that allows users to find routes based on scenery and other typical navigation preferences. In addition, GeoRouter provides powerful tools for OSM (OpenStreetMap) and SRTM (Shuttle Radar Topography Mission) data manipulation and visualization. User's can easily get accurate elevation data by simply providing a latitude and longitude bounding box.

GeoRouter currently supports two routing algorithms: A\* and a custom Bellman-Ford algorithm. The A\* algorithm shortens or lengths corresponding edges based on the user's scenery preferences while the Bellman-Ford algorithm directly incentivizes edges with negative weights which virtually guarantees routes will align with the user's scenery preferences. The Bellman-Ford algorithm is therefore more powerful, but extra compute is needed to prevent negative cycles from forming via backtracking.

## Installation

    ```bash
    pip install georouter
    ```

You will also need OSM datasets from either [BBBike](https://extract.bbbike.org/) or [Geofabrik](https://download.geofabrik.de/). The datasets should be in the form of .osm.pbf files.

SRTM datasets are automatically downloaded by GeoRouter, but a NASA Earthdata account is required as well as an account token.

## Usage

```python
from georouter import GeoRouter

```

## Todo

- [ ] Add support for Southern Hemisphere SRTM data
- [ ] Increase speed of Bellman-Ford algorithm via caching previous paths for negative cycle detection
- [ ] Add more routing preferences
- [ ] Remove utility roads from routing graph
