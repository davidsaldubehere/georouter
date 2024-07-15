import requests
import os
import zipfile
import io

HGTDIR = os.getenv('HGT_DIR', 'hgt')
def download_elevation_data(srtm_files, nasa_token):
    """
    Downloads the srtm zip files from the NASA server and extracts them to the HGT_DIR directory

    srtm_files: list of file names to download
    nasa_token: NASA Earthdata bearer token from urs.earthdata.nasa.gov
    """

    for srtm_file in srtm_files:
        url = f'https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/{srtm_file}.SRTMGL1.hgt.zip'
        print(f'Downloading {url}')
        response = requests.get(url, headers={'Authorization': f'Bearer {nasa_token}'})
        assert response.status_code == 200, f"Failed to download {url}"

        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        zip_file.extractall(HGTDIR)
        zip_file.close()