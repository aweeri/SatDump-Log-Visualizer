import os
import pandas as pd
from skyfield.api import Loader, Topos, wgs84
from datetime import datetime, timedelta
import requests
from tle_utils import *

TLE_URL = 'https://celestrak.org/NORAD/elements/weather.txt'
TLE_FILE_PATH = 'weather.txt'

def calculate_azimuth_elevation(satellite, observer_lat, observer_lon, observer_elevation, timestamp):
    load = Loader('.')
    ts = load.timescale()
    observer_location = Topos(latitude_degrees=observer_lat, longitude_degrees=observer_lon, elevation_m=observer_elevation)
    time = ts.utc(timestamp.year, timestamp.month, timestamp.day, timestamp.hour, timestamp.minute, timestamp.second)
    difference = satellite - observer_location
    topocentric = difference.at(time)
    alt, az, distance = topocentric.altaz()
    lat, lon = wgs84.latlon_of(satellite.at(time))
    return az.degrees, alt.degrees, distance.km, lat.degrees, lon.degrees


def add_azimuth_elevation_distance(df, satellites,OBSERVER_LAT,OBSERVER_LON,OBSERVER_ELEVATION):


    results = []
    for _, row in df.iterrows():
        try:
            timestamp = row['Timestamp']
            satellite_name = row['satellite']
            # replace last dash with space
            last_dash_index = satellite_name.rfind('-')
            if last_dash_index != -1:
                satellite_name = satellite_name[:last_dash_index] + ' ' + satellite_name[last_dash_index + 1:]
            satellite = next((sat for sat in satellites if sat.name == satellite_name), None)

            if satellite is not None and pd.notna(timestamp):
                azimuth, elevation, distance_km, lat, lon = calculate_azimuth_elevation(satellite, OBSERVER_LAT, OBSERVER_LON, OBSERVER_ELEVATION, timestamp)
            else:
                azimuth = None
                elevation = None
                distance_km = None
                lat = None
                lon = None

            results.append({'Azimuth': azimuth, 'Elevation': elevation, 'Distance': distance_km, 'lat': lat, 'lon': lon})
        except Exception as e:
            print(f"Error calculating azimuth and elevation for row {row}: {e}")
            results.append({'Azimuth': None, 'Elevation': None, 'Distance': None, 'lat': None, 'lon': None})

    return df.assign(**pd.DataFrame(results))
