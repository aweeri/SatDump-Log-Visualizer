import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from jinja2 import Template
from folium.plugins import HeatMap
import folium
from PIL import Image  # Dodano import dla Image z PIL

# Helper function to create a thumbnail
def create_thumbnail(image_path, thumb_path, size=(200, 200)):
    if not os.path.exists(thumb_path):  # Only create thumbnail if it doesn't exist
        try:
            img = Image.open(image_path)
            img.thumbnail(size)
            img.save(thumb_path)
        except Exception as e:
            print(f"Error creating thumbnail for {image_path}: {e}")

# Generate Folium Heatmap
def generate_folium_heatmap(df, output_path):
    df = df[df['SNR'].astype(float) != 0]  # Filter out rows where SNR is 0
    heatmap_data = df[['lat', 'lon', 'SNR']].dropna().values.tolist()

    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=2)
    HeatMap(heatmap_data, min_opacity=0.2, radius=15).add_to(m)

    m.save(output_path)

# Generate Cartopy Heatmap
def generate_cartopy_heatmap(df, output_path):
    df = df[df['SNR'].astype(float) != 0]  # Filter out rows where SNR is 0
    if df.empty:
        print("No valid data points. Skipping Cartopy heatmap.")
        return

    plt.figure(figsize=(20, 12))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')
    ax.set_global()

    sc = plt.scatter(df['lon'], df['lat'], c=df['SNR'].astype(float), cmap='jet', s=50, edgecolors='k', alpha=0.7, transform=ccrs.PlateCarree())
    plt.colorbar(sc, label='SNR')

    plt.title('Global SNR Heatmap')
    plt.savefig(output_path, dpi=300)
    plt.close()