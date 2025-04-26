#!/usr/bin/env python3
"""
Satdump Log Visualiser

Processes satellite log files, enriches them with azimuth, elevation, and distance data,
updates TLE data as needed, and creates interactive visualizations and HTML reports.

Usage:
  1. Process Logs
  2. Generate Visualizations
  3. Open Summary HTML
  4. Purge Generated Files
  5. Exit

Author: Your Name
Date: YYYY-MM-DD
"""

import os
import sys
import re
import json
import glob
import webbrowser
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
from skyfield.api import Loader, Topos, wgs84
from jinja2 import Template
from folium.plugins import HeatMap
import folium
from PIL import Image
import shutil
from colorama import init, Fore, Style

# Change working directory to the script's location
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
init(autoreset=True)

# Global objects for Skyfield
SKYFIELD_LOADER = Loader('.')
TIMESCALE = SKYFIELD_LOADER.timescale()

# Global variable for output directory (to be set from config)
OUTPUT_DIR = None

# HTML Templates remain unchanged
IMAGES_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Images for {{ folder_name }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    .gallery { display: flex; flex-wrap: wrap; }
    .gallery-item { width: 33%; padding: 5px; box-sizing: border-box; }
    .gallery-item img { width: 100%; height: auto; }
    h1, h2 { text-align: center; }
  </style>
</head>
<body>
  <h1>Images for {{ folder_name }}</h1>
  {% for subfolder, images in subfolders.items() %}
    <h2>{{ subfolder }}</h2>
    <div class="gallery">
      {% for image in images %}
      <div class="gallery-item">
        <a href="{{ image.path }}"><img src="{{ image.thumb_path }}" alt="{{ image.name }}"></a>
      </div>
      {% endfor %}
    </div>
  {% endfor %}
</body>
</html>
"""
SUMMARY_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Satellite Passes Summary</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
    th, td { padding: 8px 12px; border: 1px solid #ccc; text-align: left; }
    th { background-color: #f4f4f4; cursor: pointer; }
    a { text-decoration: none; color: #007bff; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>Satellite Passes Summary</h1>
  <table id="summaryTable">
    <thead>
      <tr>
        <th onclick="sortTable(0)">Satellite<BR>Name</th>
        <th onclick="sortTable(1)">Pass<BR>Start</th>
        <th onclick="sortTable(2)">Pass<BR>End</th>
        <th onclick="sortTable(3, 'num')">Max<BR>SNR</th>
        <th onclick="sortTable(4, 'num')">Start<BR>Azimuth</th>
        <th onclick="sortTable(5, 'num')">End<BR>Azimuth</th>
        <th onclick="sortTable(6, 'num')">Max<BR>Elevation</th>
        <th onclick="sortTable(7)">Decoder</th>
        <th>SNR & Elevation</th>
        <th>Satellite Route</th>
        <th>Polar Plot</th>
        <th>Inverted Polar Plot</th>
        <th>Heatmap</th>
        <th>Images</th>
      </tr>
    </thead>
    <tbody>
      {% for pass in passes %}
      <tr>
        <td>{{ pass.satellite }}</td>
        <td>{{ pass.pass_start }}</td>
        <td>{{ pass.pass_end }}</td>
        <td style="text-align:right">{{ pass.max_snr }}</td>
        <td style="text-align:right">{{ pass.start_azimuth }}</td>
        <td style="text-align:right">{{ pass.end_azimuth }}</td>
        <td style="text-align:right">{{ pass.max_elevation }}</td>
        <td>{{ pass.decoder }}</td>
        <td>{% if pass.snr_elevation_link %}<a href="{{ pass.snr_elevation_link }}"><img src="{{ pass.snr_elevation_thumb }}" alt="SNR & Elevation"></a>{% else %}-{% endif %}</td>
        <td>{% if pass.satellite_route_link %}<a href="{{ pass.satellite_route_link }}"><img src="{{ pass.satellite_route_thumb }}" alt="Satellite Route"></a>{% else %}-{% endif %}</td>
        <td>{% if pass.polar_plot_link %}<a href="{{ pass.polar_plot_link }}"><img src="{{ pass.polar_plot_thumb }}" alt="Polar Plot"></a>{% else %}-{% endif %}</td>
        <td>{% if pass.inverted_polar_plot_link %}<a href="{{ pass.inverted_polar_plot_link }}"><img src="{{ pass.inverted_polar_plot_thumb }}" alt="Inverted Polar Plot"></a>{% else %}-{% endif %}</td>
        <td>{% if pass.heatmap_link %}<a href="{{ pass.heatmap_link }}">Heatmap</a>{% else %}-{% endif %}</td>
        <td><a href="{{ pass.images_link }}">Images</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  <script>
    function sortTable(n, type = 'str') {
      var table = document.getElementById("summaryTable"), switching = true, dir = "asc", switchcount = 0;
      while (switching) {
        switching = false;
        var rows = table.rows;
        for (var i = 1; i < (rows.length - 1); i++) {
          var shouldSwitch = false, x = rows[i].getElementsByTagName("TD")[n],
              y = rows[i + 1].getElementsByTagName("TD")[n];
          if (dir == "asc") {
            if (type === 'num') {
              if (parseFloat(x.textContent) > parseFloat(y.textContent)) { shouldSwitch = true; break; }
            } else {
              if (x.textContent.toLowerCase() > y.textContent.toLowerCase()) { shouldSwitch = true; break; }
            }
          } else if (dir == "desc") {
            if (type === 'num') {
              if (parseFloat(x.textContent) < parseFloat(y.textContent)) { shouldSwitch = true; break; }
            } else {
              if (x.textContent.toLowerCase() < y.textContent.toLowerCase()) { shouldSwitch = true; break; }
            }
          }
        }
        if (shouldSwitch) {
          rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
          switching = true; switchcount++;
        } else {
          if (switchcount == 0 && dir == "asc") { dir = "desc"; switching = true; }
        }
      }
    }
  </script>
</body>
</html>
"""

VISUALIZATION_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualization for {{ folder_name }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    img { max-width: 100%; height: auto; }
    h1, h2 { text-align: center; }
  </style>
</head>
<body>
  <h1>Visualization for {{ folder_name }}</h1>
  <h2>SNR and Elevation Plot</h2>
  <img src="SNR_and_Elevation_plot.png" alt="SNR and Elevation Plot">
  <h2>Satellite Route</h2>
  <img src="satellite_route.png" alt="Satellite Route">
  <h2>Satellite Route (Heatmap)</h2>
  <iframe src="satellite_route.html" width="100%" height="600px"></iframe>
  <h2>Polar Plot</h2>
  <img src="polar_plot.png" alt="Polar Plot">
  <h2>Inverted Polar Plot</h2>
  <img src="polar_plot_inverted.png" alt="Inverted Polar Plot">
</body>
</html>
"""

def load_config():
    config_path = "config.json"
    default_config = {
        "description_1": "The path to your live_output directory where correctly named live decode folders are stored",
        "DATASETS_DIRECTORY": "datasets",
        "description_2": "The path to your log files. Win: 'C:/Users/[USER]/AppData/Roaming/satdump' on linux, '~/.config/satdump/'",
        "LOG_DIRECTORY": "logs",
        "description_3": "The path where visualizations will be stored. This will be created if it doesn't exist",
        "OUTPUT_DIRECTORY": "visualizations",
        "description_4": "The path to the TLE file. This will be created if it doesn't exist",
        "TLE_FILE_PATH": "weather.txt",
        "description_5": "The latitude of the observer in decimal degrees",
        "OBSERVER_LAT": 0,
        "description_6": "The longitude of the observer in decimal degrees",
        "OBSERVER_LON": 0,
        "description_7": "The elevation of the observer in meters",
        "OBSERVER_ELEVATION": 0,
        "description_8": "The number of days before the TLE file is considered old",
        "UPDATE_DAYS": 1
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            print(f"Failed to open '{config_path}': {e}")
            input("Press Enter to exit.")
            exit(1)
    try:
        print(f"'{config_path}' not found. Creating with default values. Please adjust them to your needs and run main.py again.")
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(default_config, file, indent=4)
    except Exception as e:
        print(f"Failed to write to '{config_path}': {e}")
        input("Press Enter to exit.")
        exit(1)
    return default_config

def find_log_files(directory):
    if not os.path.exists(directory):
        return []
    return [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".log")]

def convert_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str, "%H:%M:%S - %d/%m/%Y")
    except ValueError:
        return None

def extract_values_from_progress_line(line, folder_name):
    values = {"Timestamp": None, "SNR": None, "Peak_SNR": None,
              "Viterbi": None, "BER": None, "Deframer": None, "folder_name": folder_name}
    ts_match = re.match(r"\[(.*?)\]", line)
    if ts_match:
        values["Timestamp"] = convert_timestamp(ts_match.group(1))
    if (snr_match := re.search(r"SNR\s*:\s*(\d+\.\d+)dB", line)):
        values["SNR"] = snr_match.group(1)
    if (peak_match := re.search(r"Peak\s*SNR\s*:\s*(\d+\.\d+)dB", line)):
        values["Peak_SNR"] = peak_match.group(1)
    if (viterbi_match := re.search(r"Viterbi\s*:\s*(\w+)", line)):
        values["Viterbi"] = viterbi_match.group(1)
    if (ber_match := re.search(r"BER\s*:\s*(\d+\.\d+)", line)):
        values["BER"] = ber_match.group(1)
    if (deframer_match := re.search(r"Deframer\s*:\s*(\w+)", line)):
        values["Deframer"] = deframer_match.group(1)
    return values

def process_log_files(files):
    log_entries, current_entry, folder_name = [], None, None
    for file in files:
        with open(file, "r") as f:
            for line in f:
                if "(I) Start processing..." in line:
                    if current_entry:
                        log_entries.append(current_entry)
                    current_entry = {"start": None, "end": None, "logs": []}
                elif "(I) Stop processing" in line:
                    if current_entry:
                        ts_match = re.match(r"\[(.*?)\]", line)
                        if ts_match:
                            current_entry["end"] = convert_timestamp(ts_match.group(1))
                        log_entries.append(current_entry)
                        current_entry = None
                elif "Generated folder name" in line:
                    folder_name = re.search(r"[^/\\]+$", line).group(0).strip()
                elif current_entry and "(I) Progress" in line:
                    if not current_entry["start"]:
                        ts_match = re.match(r"\[(.*?)\]", line)
                        if ts_match:
                            current_entry["start"] = convert_timestamp(ts_match.group(1))
                    vals = extract_values_from_progress_line(line, folder_name)
                    current_entry["logs"].append(vals)
    if current_entry:
        log_entries.append(current_entry)
    return log_entries

def create_dataframe(entries):
    rows = [log for entry in entries for log in entry["logs"]]
    return pd.DataFrame(rows)

def merge_rows(df):
    def merge_group(group):
        return group.apply(lambda col: group[col.name].dropna().iloc[0] if not group[col.name].dropna().empty else None)
    try:
        grouped = df.groupby("Timestamp", group_keys=False, include_groups=False)
    except TypeError:
        grouped = df.groupby("Timestamp", group_keys=False)
    return grouped.apply(merge_group).reset_index(drop=True)

def find_json_file(directory, folder_name):
    files = glob.glob(os.path.join(directory, folder_name, "dataset.json"))
    return files[0] if files else None

def read_dataset_json_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data.get("satellite"), data.get("timestamp")

def add_dataset_json_data(df, json_directory):
    df["satellite"] = "Unknown"
    df["pass_timestamp"] = None
    for i, row in df.iterrows():
        folder_name = row.get("folder_name") or "default"
        json_file = find_json_file(json_directory, folder_name)
        if json_file:
            satellite, timestamp = read_dataset_json_file(json_file)
            df.at[i, "satellite"] = satellite
            df.at[i, "pass_timestamp"] = convert_timestamp_to_datetime(timestamp) if timestamp != -1 else None
    return df

def extract_decoder_from_folder_name(folder_name):
    if not folder_name:
        return "Unknown"
    parts = folder_name.split("_")
    return parts[-2] if len(parts) > 1 else "Unknown"

def convert_timestamp_to_datetime(timestamp):
    try:
        return datetime.fromtimestamp(float(timestamp))
    except Exception:
        return None

def calculate_azimuth_elevation(satellite, obs_lat, obs_lon, obs_elev, timestamp):
    t = TIMESCALE.utc(timestamp.year, timestamp.month, timestamp.day,
                      timestamp.hour, timestamp.minute, timestamp.second)
    topo = (satellite - Topos(latitude_degrees=obs_lat, longitude_degrees=obs_lon, elevation_m=obs_elev)).at(t)
    alt, az, distance = topo.altaz()
    lat, lon = wgs84.latlon_of(satellite.at(t))
    return az.degrees, alt.degrees, distance.km, lat.degrees, lon.degrees

def add_azimuth_elevation_distance(df, satellites, obs_lat, obs_lon, obs_elev):
    results = []
    for _, row in df.iterrows():
        try:
            ts_val = row["Timestamp"]
            sat_name = row["satellite"]
            idx = sat_name.rfind("-")
            if idx != -1:
                sat_name = sat_name[:idx] + " " + sat_name[idx+1:]
            satellite = next((s for s in satellites if s.name == sat_name), None)
            if satellite and pd.notna(ts_val):
                az, el, dist, lat, lon = calculate_azimuth_elevation(satellite, obs_lat, obs_lon, obs_elev, ts_val)
            else:
                az = el = dist = lat = lon = None
            results.append({"Azimuth": az, "Elevation": el, "Distance": dist, "lat": lat, "lon": lon})
        except Exception as e:
            print(f"Error calculating az/el for row {row}: {e}")
            results.append({"Azimuth": None, "Elevation": None, "Distance": None, "lat": None, "lon": None})
    results_df = pd.DataFrame(results, index=df.index)
    for col in ["Azimuth", "Elevation", "Distance", "lat", "lon"]:
        if col not in results_df.columns:
            results_df[col] = None
    return pd.concat([df, results_df], axis=1)

def create_thumbnail(image_path, thumb_path, size=(200, 200)):
    if not os.path.exists(thumb_path):
        try:
            img = Image.open(image_path)
            img.thumbnail(size)
            img.save(thumb_path)
        except Exception as e:
            print(f"Error creating thumbnail for {image_path}: {e}")

def generate_images_html(folder_name):
    template = Template(IMAGES_TEMPLATE)
    subfolders = {}
    base_dir = os.path.join(OUTPUT_DIR, folder_name)
    for root, dirs, files in os.walk(base_dir):
        rel_root = os.path.relpath(root, base_dir)
        images_list = []
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')) and "thumb" not in file and \
               all(x not in file for x in ["SNR_and_Elevation_plot", "satellite_route", "polar_plot"]):
                thumb = os.path.join(root, "thumb_" + file)
                image = os.path.relpath(os.path.join(root, file), base_dir)
                create_thumbnail(os.path.join(root, file), thumb)
                images_list.append({"path": image, "thumb_path": os.path.relpath(thumb, base_dir), "name": file})
        if images_list:
            subfolders[rel_root] = images_list
    html_content = template.render(folder_name=folder_name, subfolders=subfolders)
    out_path = os.path.join(OUTPUT_DIR, folder_name, "images.html")
    with open(out_path, "w") as f:
        f.write(html_content)
    print(f"Images HTML generated for {folder_name}")

def generate_summary_html(df):
    template = Template(SUMMARY_TEMPLATE)
    passes = []
    df["folder_name"] = df["folder_name"].fillna("default")
    for folder_name, group in df.groupby("folder_name"):
        info = {
            "satellite": group["satellite"].iloc[0],
            "pass_start": group["Timestamp"].min().strftime("%Y-%m-%d<BR>%H:%M:%S") if pd.notnull(group["Timestamp"].min()) else "N/A",
            "pass_end": group["Timestamp"].max().strftime("%H:%M:%S") if pd.notnull(group["Timestamp"].max()) else "N/A",
            "max_snr": round(group["SNR"].astype(float).max(), 2) if not group["SNR"].isnull().all() else None,
            "start_azimuth": round(group["Azimuth"].iloc[0], 2) if pd.notna(group["Azimuth"].iloc[0]) else None,
            "end_azimuth": round(group["Azimuth"].iloc[-1], 2) if pd.notna(group["Azimuth"].iloc[-1]) else None,
            "max_elevation": round(group["Elevation"].astype(float).max(), 2) if not group["Elevation"].isnull().all() else None,
            "decoder": group["decoder"].iloc[0].upper() if "decoder" in group.columns else "UNKNOWN",
            "snr_elevation_link": None,
            "snr_elevation_thumb": None,
            "satellite_route_link": None,
            "satellite_route_thumb": None,
            "polar_plot_link": None,
            "polar_plot_thumb": None,
            "inverted_polar_plot_link": None,
            "inverted_polar_plot_thumb": None,
            "heatmap_link": None,
            "images_link": os.path.join(OUTPUT_DIR, folder_name, "images.html")
        }
        se_path = os.path.join(OUTPUT_DIR, folder_name, "SNR_and_Elevation_plot.png")
        if os.path.exists(se_path):
            info["snr_elevation_link"] = se_path
            info["snr_elevation_thumb"] = se_path.replace(".png", "_thumb.png")
        sr_path = os.path.join(OUTPUT_DIR, folder_name, "satellite_route.png")
        if os.path.exists(sr_path):
            info["satellite_route_link"] = sr_path
            info["satellite_route_thumb"] = sr_path.replace(".png", "_thumb.png")
        pp_path = os.path.join(OUTPUT_DIR, folder_name, "polar_plot.png")
        if os.path.exists(pp_path):
            info["polar_plot_link"] = pp_path
            info["polar_plot_thumb"] = pp_path.replace(".png", "_thumb.png")
        ipp_path = os.path.join(OUTPUT_DIR, folder_name, "polar_plot_inverted.png")
        if os.path.exists(ipp_path):
            info["inverted_polar_plot_link"] = ipp_path
            info["inverted_polar_plot_thumb"] = ipp_path.replace(".png", "_thumb.png")
        hm_path = os.path.join(OUTPUT_DIR, folder_name, "satellite_route.html")
        if os.path.exists(hm_path):
            info["heatmap_link"] = hm_path
        passes.append(info)
    html_content = template.render(passes=passes)
    with open("summary.html", "w") as f:
        f.write(html_content)
    print("Summary HTML generated.")

def generate_visualization_html(folder_name):
    template = Template(VISUALIZATION_TEMPLATE)
    html_content = template.render(folder_name=folder_name)
    out_dir = os.path.join(OUTPUT_DIR, folder_name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "visualization.html")
    with open(out_path, "w") as f:
        f.write(html_content)
    print(f"Visualization HTML generated for {folder_name}")

def plot_snr_and_elevation(df, folder_name):
    df = df[df["SNR"].astype(float) != 0]
    if df.empty:
        print(f"No valid data in {folder_name} for SNR/Elevation plot.")
        return
    os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(16, 9))
    ax1.set_xlabel("Timestamp")
    ax1.set_ylabel("SNR (dB)", color="tab:blue")
    ax1.plot(df["Timestamp"], df["SNR"].astype(float), marker="o", linestyle="-", color="tab:blue")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    ax1.tick_params(axis="x", rotation=45)
    ax2 = ax1.twinx()
    ax2.set_ylabel("Elevation (deg)", color="tab:green")
    ax2.plot(df["Timestamp"], df["Elevation"].astype(float), marker="x", linestyle="--", color="tab:green")
    ax2.tick_params(axis="y", labelcolor="tab:green")
    plt.title(f"SNR and Elevation over Time for {folder_name}")
    plot_path = os.path.join(OUTPUT_DIR, folder_name, "SNR_and_Elevation_plot.png")
    plt.savefig(plot_path, dpi=300)
    plt.close()
    create_thumbnail(plot_path, plot_path.replace(".png", "_thumb.png"))
    print(f"SNR/Elevation plot generated for {folder_name}")

def plot_satellite_route(df, folder_name):
    try:
        df = df[df["SNR"].astype(float) != 0]
        if df.empty:
            print(f"No valid data in {folder_name} for Satellite Route plot.")
            return
        os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)
        plt.figure(figsize=(20, 12))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND)
        ax.add_feature(cfeature.OCEAN)
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=":")

        ax.set_global()
        sc = plt.scatter(df["lon"], df["lat"], c=df["SNR"].astype(float), cmap="jet",
                        s=50, edgecolors="k", alpha=0.7, transform=ccrs.PlateCarree())
        plt.colorbar(sc, label="SNR")
        plt.title(f"Satellite Route for {folder_name}")
        plot_path = os.path.join(OUTPUT_DIR, folder_name, "satellite_route.png")
        plt.savefig(plot_path, dpi=300)
        plt.close()
        create_thumbnail(plot_path, plot_path.replace(".png", "_thumb.png"))
        print(f"Satellite Route plot generated for {folder_name}")
    except:
        print(f"Error generating Satellite Route plot for {folder_name}")

def generate_combined_route(df):
    # Make sure lon/lat/SNR are numeric
    df = df[pd.notnull(df["lon"]) & pd.notnull(df["lat"]) & pd.notnull(df["SNR"])]
    if df.empty:
        print("No data for combined route.")
        return

    fig = plt.figure(figsize=(20, 12))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=":")
    ax.set_global()

    sc = ax.scatter(
        df["lon"],
        df["lat"],
        c=df["SNR"].astype(float),
        cmap="jet",
        s=10,
        edgecolors="k",
        alpha=0.7,
        transform=ccrs.PlateCarree()
    )
    plt.colorbar(sc, label="SNR")
    plt.title("Combined Satellite Route for All Passes")

    out_path = os.path.join(OUTPUT_DIR, "combined_satellite_route.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"Combined satellite route saved to {out_path}")


def generate_heatmap(df, folder_name):
    # Prepare data for heatmap: [lat, lon, weight]
    heat_data = []
    for _, row in df.iterrows():
        lat = row.get('lat')
        lon = row.get('lon')
        snr = row.get('SNR')
        if pd.notnull(lat) and pd.notnull(lon) and pd.notnull(snr):
            heat_data.append([lat, lon, float(snr)])
    if not heat_data:
        print(f"No data for heatmap for {folder_name}.")
        return

    # Center map on mean coords
    center_lat = np.mean([pt[0] for pt in heat_data])
    center_lon = np.mean([pt[1] for pt in heat_data])

    m = folium.Map(location=[center_lat, center_lon], zoom_start=2)
    HeatMap(heat_data).add_to(m)

    out_path = os.path.join(OUTPUT_DIR, folder_name, "satellite_route.html")
    m.save(out_path)
    print(f"Heatmap generated for {folder_name} at {out_path}")

def generate_combined_heatmap(df):
    # Prepare data for combined heatmap: [lat, lon, weight]
    heat_data = []
    for _, row in df.iterrows():
        lat = row.get('lat')
        lon = row.get('lon')
        snr = row.get('SNR')
        if pd.notnull(lat) and pd.notnull(lon) and pd.notnull(snr):
            heat_data.append([lat, lon, float(snr)])
    if not heat_data:
        print("No data for combined heatmap.")
        return

    # Center on mean of all points
    center_lat = np.mean([pt[0] for pt in heat_data])
    center_lon = np.mean([pt[1] for pt in heat_data])

    m = folium.Map(location=[center_lat, center_lon], zoom_start=2)
    HeatMap(
        heat_data,
        radius=18,       # smaller point radius
        blur=15,         # less blur = tighter clustering
        max_zoom=6,     # more detail when zoomed in
        min_opacity=0.2 # keep faint points visible
    ).add_to(m)

    out_path = os.path.join(OUTPUT_DIR, "combined_heatmap.html")
    m.save(out_path)
    print(f"Combined heatmap generated at {out_path}")


def plot_polar(df, folder_name, pass_timestamp, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    for _, row in df.iterrows():
        ax.scatter(np.deg2rad(row["Azimuth"]), row["Elevation"],
                   c=[cm.jet(plt.Normalize(snr_min, snr_max)(row["SNR"]))], edgecolors="w", s=50)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    plt.title(f"Polar Plot for {folder_name}\n(Pass at {pass_timestamp})")
    filename = os.path.join(OUTPUT_DIR, folder_name, "polar_plot.png")
    plt.savefig(filename)
    plt.close()
    create_thumbnail(filename, filename.replace(".png", "_thumb.png"))
    print(f"Polar Plot generated for {folder_name}")

def plot_polar_map(df, folder_name, pass_timestamp, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    for _, row in df.iterrows():
        ax.scatter(np.deg2rad(row["Azimuth"]), 90 - row["Elevation"],
                   c=[cm.jet(plt.Normalize(snr_min, snr_max)(row["SNR"]))], edgecolors="w", s=50)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    ax.set_yticks(np.arange(0, 91, 15))
    ax.set_yticklabels([str(int(l)) for l in np.arange(90, -1, -15)])
    plt.title(f"Inverted Polar Plot for {folder_name}\n(Pass at {pass_timestamp})")
    filename = os.path.join(OUTPUT_DIR, folder_name, "polar_plot_inverted.png")
    plt.savefig(filename)
    plt.close()
    create_thumbnail(filename, filename.replace(".png", "_thumb.png"))
    print(f"Inverted Polar Plot generated for {folder_name}")

def plot_polar_all(df, decoder, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    for _, row in df.iterrows():
        ax.scatter(np.deg2rad(row["Azimuth"]), row["Elevation"],
                   c=[cm.jet(plt.Normalize(snr_min, snr_max)(row["SNR"]))], edgecolors="w", s=50)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    plt.title(f"Combined Polar Plot for Decoder {decoder}")
    filename = os.path.join(OUTPUT_DIR, f"polar_plot_all_{decoder}".replace(":", "-").replace("/", "_") + ".png")
    plt.savefig(filename)
    plt.close()
    print(f"Combined Polar Plot generated for Decoder {decoder}")

def plot_polar_all_map(df, decoder, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    for _, row in df.iterrows():
        ax.scatter(np.deg2rad(row["Azimuth"]), 90 - row["Elevation"],
                   c=[cm.jet(plt.Normalize(snr_min, snr_max)(row["SNR"]))], edgecolors="w", s=50)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    ax.set_yticks(np.arange(0, 91, 15))
    ax.set_yticklabels([str(int(l)) for l in np.arange(90, -1, -15)])
    plt.title(f"Combined Inverted Polar Plot for Decoder {decoder}")
    filename = os.path.join(OUTPUT_DIR, f"polar_plot_all_inverted_{decoder}".replace(":", "-").replace("/", "_") + ".png")
    plt.savefig(filename)
    plt.close()
    print(f"Combined Inverted Polar Plot generated for Decoder {decoder}")

TLE_URL = "https://celestrak.org/NORAD/elements/weather.txt"
TLE_FILE_PATH_GLOBAL = None

def download_tle():
    try:
        response = requests.get(TLE_URL)
        response.raise_for_status()
        with open(TLE_FILE_PATH_GLOBAL, "w") as f:
            f.write(response.text)
        print("TLE data downloaded.")
    except Exception as e:
        print(f"Error downloading TLE: {e}")

def download_tle_if_necessary(update_days):
    if not os.path.exists(TLE_FILE_PATH_GLOBAL):
        print("TLE file not found; downloading...")
        download_tle()
    else:
        mod_time = datetime.fromtimestamp(os.path.getmtime(TLE_FILE_PATH_GLOBAL))
        if (datetime.now() - mod_time).days >= update_days:
            print("TLE file outdated; downloading new data...")
            download_tle()
        else:
            print("TLE file is up-to-date.")

def process_logs(config):
    log_dir = config["LOG_DIRECTORY"]
    datset_dir = config["DATASETS_DIRECTORY"]
    tle_file = config["TLE_FILE_PATH"]
    obs_lat = config["OBSERVER_LAT"]
    obs_lon = config["OBSERVER_LON"]
    obs_elev = config["OBSERVER_ELEVATION"]

    global TLE_FILE_PATH_GLOBAL
    TLE_FILE_PATH_GLOBAL = tle_file

    if not os.path.exists(datset_dir):
        print(f"Error: Input directory '{datset_dir}' not found.")
        return
    if not os.path.exists(log_dir):
        print(f"Error: Log directory '{log_dir}' not found.")
        return

    files = find_log_files(log_dir)
    if not files:
        print("No log files found.")
        return

    entries = process_log_files(files)
    df = merge_rows(create_dataframe(entries))
    df["folder_name"] = df["folder_name"].fillna("default")
    df = add_dataset_json_data(df, json_directory=datset_dir)
    df["decoder"] = df["folder_name"].apply(extract_decoder_from_folder_name)
    df = df[~df["satellite"].str.contains("Unknown", na=False)]

    df.to_csv("parsed_log_data.csv", index=False)
    print("Parsed log data saved.")

    if not os.path.exists(tle_file):
        print("TLE file not found; downloading...")
        download_tle()

    satellites = SKYFIELD_LOADER.tle_file(tle_file)
    enriched_df = add_azimuth_elevation_distance(df, satellites, obs_lat, obs_lon, obs_elev)
    enriched_df.to_csv("final_processed_log_data_enriched.csv", index=False)
    print("Enriched log data saved.")

def visualize_data(config):
    global TLE_FILE_PATH_GLOBAL
    if TLE_FILE_PATH_GLOBAL is None:
        TLE_FILE_PATH_GLOBAL = config["TLE_FILE_PATH"]
    obs_lat = config["OBSERVER_LAT"]
    obs_lon = config["OBSERVER_LON"]
    obs_elev = config["OBSERVER_ELEVATION"]
    update_days = config["UPDATE_DAYS"]

    if not os.path.exists("final_processed_log_data_enriched.csv"):
        print("Enriched data not found. Process logs first or place the enriched CSV in this directory.")
        return

    download_tle_if_necessary(update_days)

    df = pd.read_csv("final_processed_log_data_enriched.csv", parse_dates=["Timestamp", "pass_timestamp"])
    df["SNR"] = pd.to_numeric(df["SNR"], errors="coerce")
    df["Azimuth"] = pd.to_numeric(df["Azimuth"], errors="coerce")
    df["Elevation"] = pd.to_numeric(df["Elevation"], errors="coerce")

    df = df[df["decoder"] != "apt"]
    df = df[pd.notna(df["Azimuth"]) & pd.notna(df["Elevation"]) & pd.notna(df["SNR"])]
    df = df[np.isfinite(df["Azimuth"]) & np.isfinite(df["Elevation"]) & np.isfinite(df["SNR"])]
    df["satellite"] = df["satellite"].str.replace("-", " ", 1)

    for folder_name, group in df.groupby("folder_name"):
        print(f"Generating visualizations for {folder_name}")
        os.makedirs(os.path.join(OUTPUT_DIR, folder_name), exist_ok=True)
        generate_combined_heatmap(df)
        generate_combined_route(df)
        plot_snr_and_elevation(group, folder_name)
        plot_satellite_route(group, folder_name)
        generate_heatmap(group, folder_name)
        generate_visualization_html(folder_name)
        generate_images_html(folder_name)
        snr_min = group["SNR"].min()
        snr_max = group["SNR"].max()
        for pass_ts in group["pass_timestamp"].unique():
            pass_df = group[group["pass_timestamp"] == pass_ts]
            plot_polar(pass_df, folder_name, pass_ts, snr_min, snr_max)
            plot_polar_map(pass_df, folder_name, pass_ts, snr_min, snr_max)
    for decoder in df["decoder"].unique():
        ddf = df[df["decoder"] == decoder]
        snr_min = ddf["SNR"].min()
        snr_max = ddf["SNR"].max()
        plot_polar_all(ddf, decoder, snr_min, snr_max)
        plot_polar_all_map(ddf, decoder, snr_min, snr_max)
    generate_summary_html(df)
    print("Visualization generation complete.")

def open_summary():
    if os.path.exists("summary.html"):
        webbrowser.open("file://" + os.path.realpath("summary.html"))
        print("Opening summary...")
    else:
        print("Summary not found. Generate visualizations first.")

def purge_generated_files():
    for f in ["parsed_log_data.csv", "final_processed_log_data_enriched.csv", "summary.html"]:
        if os.path.exists(f):
            os.remove(f)
    if OUTPUT_DIR and os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    print("Generated files purged.")

def main_menu():
    config = load_config()
    global OUTPUT_DIR
    OUTPUT_DIR = config.get("OUTPUT_DIRECTORY", "visualizations")

    # Warn about default location
    if config.get("OBSERVER_LAT", 0) == 0 and config.get("OBSERVER_LON", 0) == 0:
        print(Fore.RED + "WARNING: Your location is set to 0,0 in config.json. "
              "This WILL ruin your graphs. Change it to your actual coordinates, "
              "unless you live in the Gulf of Guinea." + Style.RESET_ALL)

    # Determine what features are available
    log_files = find_log_files(config["LOG_DIRECTORY"])
    has_logs = bool(log_files)
    has_datasets = os.path.exists(config["DATASETS_DIRECTORY"])
    logs_enabled = has_logs and has_datasets

    parsed_exists = os.path.exists("parsed_log_data.csv")
    enriched_exists = os.path.exists("final_processed_log_data_enriched.csv")
    summary_exists = os.path.exists("summary.html")

    while True:
        print("\n" + Fore.CYAN + Style.BRIGHT + "----- Satdump Log Visualiser -----" + Style.RESET_ALL)

        # Option 1: Process Logs
        if logs_enabled:
            print(Fore.YELLOW + Style.BRIGHT + "1. Process Logs" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + "1. [Disabled] Process Logs (missing log files or datasets)" + Style.RESET_ALL)

        # Option 2: Generate Visualizations
        if enriched_exists:
            print(Fore.YELLOW + Style.BRIGHT + "2. Generate Visualizations" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + "2. [Disabled] Generate Visualizations (no enriched CSV)" + Style.RESET_ALL)

        # Option 3: Open Summary HTML
        if summary_exists:
            print(Fore.YELLOW + Style.BRIGHT + "3. Open Summary HTML" + Style.RESET_ALL)
        else:
            print(Fore.RED + Style.BRIGHT + "3. [Disabled] Open Summary HTML (summary.html missing)" + Style.RESET_ALL)

        # Option 4 and 5 always available
        print(Fore.YELLOW + Style.BRIGHT + "4. Purge Generated Files" + Style.RESET_ALL)
        print(Fore.YELLOW + Style.BRIGHT + "5. Exit" + Style.RESET_ALL)

        choice = input("Choice (1-5): ").strip()
        if choice == "1":
            if logs_enabled:
                process_logs(config)
                # Refresh flags
                parsed_exists = os.path.exists("parsed_log_data.csv")
                enriched_exists = os.path.exists("final_processed_log_data_enriched.csv")
                summary_exists = os.path.exists("summary.html")
            else:
                print("Process Logs is disabled: missing log files or datasets directory.")
        elif choice == "2":
            if enriched_exists:
                visualize_data(config)
                summary_exists = os.path.exists("summary.html")
            else:
                print("Generate Visualizations is disabled: no enriched data found. "
                      "Please process logs or place 'final_processed_log_data_enriched.csv' in this directory.")
        elif choice == "3":
            if summary_exists:
                open_summary()
            else:
                print("Open Summary HTML is disabled: summary.html not found.")
        elif choice == "4":
            purge_generated_files()
            # Refresh everything
            parsed_exists = os.path.exists("parsed_log_data.csv")
            enriched_exists = os.path.exists("final_processed_log_data_enriched.csv")
            summary_exists = os.path.exists("summary.html")
            log_files = find_log_files(config["LOG_DIRECTORY"])
            has_logs = bool(log_files)
            has_datasets = os.path.exists(config["DATASETS_DIRECTORY"])
            logs_enabled = has_logs and has_datasets
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()
