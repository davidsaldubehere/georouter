import os
import numpy as np
from .data_loader import download_elevation_data

SRTM_SAMPLE_DENSITY = 3601 # 3601 x 3601 samples per file for 30m resolution SRMT data
HGTDIR = os.getenv('HGT_DIR', 'hgt')

def get_file_names(min_lat, max_lat, min_lon, max_lon, download = False, nasa_token = None):
    """
    Returns a list of file paths that contain the elevation data for the given bounding box
    The min and max refer to numerical mins and maxes. For example, from -77 to -78, min_lat = -78, max_lat = -77 even though -78 is the westernmost point

    If download is set to True, it will download the file if it does not exist

    WARNING: Does not work if the bounding box crosses hemispheres
    """
    srtm_files = []
    files_to_download = []

    if int(min_lat) != int(max_lat):
        lats_to_read = list(range(int(min_lat), int(max_lat) + 1)) if min_lat < max_lat else list(range(int(max_lat), int(min_lat) - 1))
    else:
        lats_to_read = [int(min_lat)]
    if int(min_lon) != int(max_lon):
        lons_to_read = list(range(int(min_lon), int(max_lon) + 1)) if min_lon < max_lon else list(range(int(max_lon), int(min_lon) - 1))
    else:
        lons_to_read = [int(min_lon)]
    for lon in lons_to_read:
        for lat in lats_to_read[::-1]:
            hgt_file = "%(ns)s%(lat)02d%(ew)s%(lon)03d" % \
            {'lon': abs(lon) if lon >= 0 else abs(lon-1), 'lat': abs(lat) if lat >=0 else abs(lat-1), 'ns': 'N' if lat >= 0 else 'S', 'ew': 'E' if lon >= 0 else 'W'}
            file_path = os.path.join(HGTDIR, hgt_file+".hgt")
            if not os.path.exists(file_path) and download:
                files_to_download.append(hgt_file)
            srtm_files.append(file_path)
    if len(files_to_download) > 0:
        print(f"Need to download {len(files_to_download)} files")
        assert nasa_token is not None, "NASA token is required to download the files"
        download_elevation_data(files_to_download, nasa_token)
    return srtm_files

def get_elevation_data(min_lat, max_lat, min_lon, max_lon, download = False, nasa_token = None):
    """
    Returns the elevation data for the given bounding box via NASA's SRTM data in the form of a numpy array as well as the longitude and latitude values for those points

    If you set download to True, it will download the files to the hgt directory if they do not exist but you need to provide the NASA bearer token from urs.earthdata.nasa.gov

    You can specify the HGT_DIR environment variable to change the directory where the files are stored; default is 'hgt'

    Warning: Does not work if the bounding box crosses hemispheres
    """
    hgt_files = get_file_names(min_lat, max_lat, min_lon, max_lon, download, nasa_token)


    if len(hgt_files) == 0:
        print("No files found for the given bounding box. Make sure you're using the correct min and max latitudes and longitudes. For example, for -77 and -78, min_lat = -78, max_lat = -77 even though -78 is the westernmost point.")
        return None

    return read_elevation_data_from_files(hgt_files, min_lat, max_lat, min_lon, max_lon)

def read_elevation_data_from_files(hgt_files, min_lat, max_lat, min_lon, max_lon):
    """
    Reads the elevation data from the given hgt files and returns a numpy array

    The hgt files must be valid file paths to the hgt files

    WARNING: If you are reading from mulitple files, the files must be ordered from north to south and west to east.

    Since SRTM data uses 30m resolution, the resulting numpy array will include data for each 30m x 30m square in the bounding box

    """
    elevation_data = None
    queue = None
    #We take the files and piece together vertically and then combine horizontally
    v_strip_height = 1 if int(max_lat) == int(min_lat) else int(max_lat) - int(min_lat) + 1
    for count, file_name in enumerate(hgt_files):
        with open(file_name, 'rb') as hgt_data:
            elevations = np.fromfile(
                hgt_data, 
                np.dtype('>i2'),  # data type
                SRTM_SAMPLE_DENSITY * SRTM_SAMPLE_DENSITY  # length
            ).reshape((SRTM_SAMPLE_DENSITY, SRTM_SAMPLE_DENSITY))
            if (count+1) % v_strip_height == 0:
                if queue is not None:
                    queue = np.vstack((queue, elevations))
                else:
                    queue = elevations
                if elevation_data is None:
                    elevation_data = queue
                else:
                    elevation_data = np.hstack((elevation_data, queue))
                queue = None #empty the queue
            else:
                if queue is None:
                    queue = elevations
                else:
                    queue = np.vstack((queue, elevations))
    if len(hgt_files) > 1:

        #We have to subset the data to the bounding box
        min_lat_offset = min_lat - int(min_lat) if min_lat >= 0 else abs(int(min_lat))+1 - abs(min_lat)
        min_lon_offset = min_lon - int(min_lon) if min_lon >= 0 else abs(int(min_lon))+1 - abs(min_lon)
        max_lat_offset = max_lat - int(max_lat) if max_lat >= 0 else abs(int(max_lat))+1 - abs(max_lat)
        max_lon_offset = max_lon - int(max_lon) if max_lon >= 0 else abs(int(max_lon))+1 - abs(max_lon)
        #Now we have to find the rows and columns that correspond to the subset
        start_row = int(min_lat)
        start_col = int(min_lon)
        min_lat_row = round(abs(start_row - int(min_lat)) * SRTM_SAMPLE_DENSITY + min_lat_offset * SRTM_SAMPLE_DENSITY)
        min_lon_row = round(abs(start_col - int(min_lon)) * SRTM_SAMPLE_DENSITY + min_lon_offset * SRTM_SAMPLE_DENSITY)
        max_lat_row = round(abs(start_row - int(max_lat)) * SRTM_SAMPLE_DENSITY + max_lat_offset * SRTM_SAMPLE_DENSITY)
        max_lon_row = round(abs(start_col - int(max_lon)) * SRTM_SAMPLE_DENSITY + max_lon_offset * SRTM_SAMPLE_DENSITY)

        #We need to invert the longitude indexes because longitudes increase as we go up (in northern hemisphere)
        #but the hgt file has the longitudes increasing as we go down
        min_lat_row, max_lat_row = SRTM_SAMPLE_DENSITY * v_strip_height - 1 - max_lat_row, SRTM_SAMPLE_DENSITY * v_strip_height - 1 - min_lat_row + 1

        elevation_subset = elevation_data[min_lat_row:max_lat_row, min_lon_row:max_lon_row]
        lon_vals = np.linspace(min_lon, max_lon, elevation_subset.shape[1])
        lat_vals = np.linspace(max_lat, min_lat, elevation_subset.shape[0])
        return elevation_subset.astype(int), lon_vals, lat_vals
    else:
        min_lat_row = int(round((min_lat - int(min_lat)) * (SRTM_SAMPLE_DENSITY - 1), 0))
        min_lon_row = int(round((min_lon - int(min_lon)) * (SRTM_SAMPLE_DENSITY - 1), 0))
        max_lat_row = int(round((max_lat - int(max_lat)) * (SRTM_SAMPLE_DENSITY - 1), 0))
        max_lon_row = int(round((max_lon - int(max_lon)) * (SRTM_SAMPLE_DENSITY - 1), 0))

        #we have to invert the longitude indexes because longitudes increases as we go up (in northern hemisphere)
        #but the hgt file has the longitudes increasing as we go down
        min_lat_row, max_lat_row = SRTM_SAMPLE_DENSITY - 1 - max_lat_row, SRTM_SAMPLE_DENSITY - 1 - min_lat_row + 1

        elevation_subset = elevations[min_lat_row:max_lat_row, min_lon_row:max_lon_row+1]
        lon_vals = np.linspace(min_lon, max_lon, elevation_subset.shape[1])
        lat_vals = np.linspace(max_lat, min_lat, elevation_subset.shape[0])
        return elevation_subset.astype(int), lon_vals, lat_vals #Unsure why, but numpy is reversing the range