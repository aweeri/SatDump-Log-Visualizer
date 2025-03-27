import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from jinja2 import Template
from PIL import Image


# Helper function to create a thumbnail
# This function generates a thumbnail of an image if it doesn't already exist.
def create_thumbnail(image_path, thumb_path, size=(200, 200)):
    #if not os.path.exists(thumb_path):  # Only create thumbnail if it doesn't exist
        try:
            img = Image.open(image_path)
            img.thumbnail(size)
            img.save(thumb_path)
        except Exception as e:
            print(f"Error creating thumbnail for {image_path}: {e}")

# Function to generate HTML for images
# This function generates an HTML file that contains a gallery of images in a given folder.
def generate_images_html(folder_name):
    with open('templates/images_template.html', 'r') as file:
        images_template_str = file.read()

    images_template = Template(images_template_str)
    subfolders = {}

    # Walk through the directory structure to find images and generate thumbnails
    for root, dirs, files in os.walk(os.path.join('images', folder_name)):
        relative_root = os.path.relpath(root, os.path.join('images', folder_name))
        subfolder_images = []

        for file in files:
            # Exclude specific plots from the gallery
            if file.lower().endswith(('.png', '.jpg', '.jpeg')) and not 'thumb' in file and not any(sub in file for sub in ['SNR_and_Elevation_plot', 'satellite_route', 'polar_plot']):
                thumb_path=''
                image_path = os.path.relpath(os.path.join(root, file), os.path.join('images', folder_name))
                if not 'thumb' in image_path:
                    thumb_path = os.path.join(root, 'thumb_' + file)
                else:
                    thumb_path = image_path
                
                create_thumbnail(os.path.join(root, file), thumb_path)
                subfolder_images.append({
                    'path': image_path,
                    'thumb_path': os.path.relpath(thumb_path, os.path.join('images', folder_name)),
                    'name': file
                })

        if subfolder_images:
            subfolders[relative_root] = subfolder_images

    # Render the HTML content using the template and save it
    html_content = images_template.render(folder_name=folder_name, subfolders=subfolders)
    with open(os.path.join('images', folder_name, 'images.html'), 'w') as file:
        file.write(html_content)

# Function to create summary HTML
# This function generates an HTML summary file that includes details about each satellite pass.
def generate_summary_html(df):
    with open('templates/summary_template.html', 'r') as file:
        summary_template_str = file.read()

    summary_template = Template(summary_template_str)
    passes = []

    # Group the dataframe by folder_name to process each pass separately
    for folder_name, folder_df in df.groupby('folder_name'):
        pass_info = {
            'satellite': folder_df['satellite'].iloc[0],
            'pass_start': folder_df['Timestamp'].min().strftime('%Y-%m-%d<BR>%H:%M:%S'),
            'pass_end': folder_df['Timestamp'].max().strftime('%H:%M:%S'),
            'max_snr': round(folder_df['SNR'].astype(float).max(), 2),
            'start_azimuth': round(folder_df['Azimuth'].iloc[0], 2),
            'end_azimuth': round(folder_df['Azimuth'].iloc[-1], 2),
            'max_elevation': round(folder_df['Elevation'].astype(float).max(), 2),
            'decoder': folder_df['decoder'].iloc[0].upper(),
            'snr_elevation_link': None,
            'snr_elevation_thumb': None,
            'satellite_route_link': None,
            'satellite_route_thumb': None,
            'polar_plot_link': None,
            'polar_plot_thumb': None,
            'inverted_polar_plot_link': None,
            'inverted_polar_plot_thumb': None,
            'heatmap_link': None,
            'images_link': os.path.join('images', folder_name, 'images.html')
        }

        # Check if specific plots exist and set their links and thumbnails
        snr_elevation_path = os.path.join('images', folder_name, 'SNR_and_Elevation_plot.png')
        if os.path.exists(snr_elevation_path):
            pass_info['snr_elevation_link'] = snr_elevation_path
            pass_info['snr_elevation_thumb'] = snr_elevation_path.replace('.png', '_thumb.png')

        satellite_route_path = os.path.join('images', folder_name, 'satellite_route.png')
        if os.path.exists(satellite_route_path):
            pass_info['satellite_route_link'] = satellite_route_path
            pass_info['satellite_route_thumb'] = satellite_route_path.replace('.png', '_thumb.png')

        polar_plot_path = os.path.join('images', folder_name, 'polar_plot.png')
        if os.path.exists(polar_plot_path):
            pass_info['polar_plot_link'] = polar_plot_path
            pass_info['polar_plot_thumb'] = polar_plot_path.replace('.png', '_thumb.png')

        inverted_polar_plot_path = os.path.join('images', folder_name, 'polar_plot_inverted.png')
        if os.path.exists(inverted_polar_plot_path):
            pass_info['inverted_polar_plot_link'] = inverted_polar_plot_path
            pass_info['inverted_polar_plot_thumb'] = inverted_polar_plot_path.replace('.png', '_thumb.png')

        heatmap_path = os.path.join('images', folder_name, 'satellite_route.html')
        if os.path.exists(heatmap_path):
            pass_info['heatmap_link'] = heatmap_path

        passes.append(pass_info)

    # Render the summary HTML content and save it
    html_content = summary_template.render(passes=passes)
    with open('summary.html', 'w') as file:
        file.write(html_content)

# Function to create visualization HTML
# This function generates an HTML file that shows visualizations for a given folder.
def generate_visualization_html(df, folder_name):
    with open('templates/visualization_template.html', 'r') as file:
        visualization_template_str = file.read()

    visualization_template = Template(visualization_template_str)
    html_content = visualization_template.render(folder_name=folder_name)

    os.makedirs(os.path.join('images', folder_name), exist_ok=True)
    with open(os.path.join('images', folder_name, 'visualization.html'), 'w') as file:
        file.write(html_content)

# Plot functions
# Function to plot SNR and elevation over time
def plot_snr_and_elevation(df, folder_name):
    df = df[df['SNR'].astype(float) != 0]
    if df.empty:
        print(f"No valid data points for {folder_name}. Skipping SNR plot.")
        return

    fig, ax1 = plt.subplots(figsize=(16, 9))

    color = 'tab:blue'
    ax1.set_xlabel('Timestamp')
    ax1.set_ylabel('SNR (dB)', color=color)
    ax1.plot(df['Timestamp'], df['SNR'].astype(float), marker='o', linestyle='-', color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.tick_params(axis='x', rotation=45)

    ax2 = ax1.twinx()
    color = 'tab:green'
    ax2.set_ylabel('Elevation (degrees)', color=color)
    ax2.plot(df['Timestamp'], df['Elevation'].astype(float), marker='x', linestyle='--', color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    plt.title(f'SNR and Elevation over Time for {folder_name}')
    
    os.makedirs(os.path.join('images', folder_name), exist_ok=True)
    plt.savefig(os.path.join('images', folder_name, 'SNR_and_Elevation_plot.png'), dpi=300)
    plt.close()
    create_thumbnail(os.path.join('images', folder_name, 'SNR_and_Elevation_plot.png'), os.path.join('images', folder_name, 'SNR_and_Elevation_plot_thumb.png'))

# Function to plot the satellite route on a map
def plot_satellite_route(df, folder_name):
    df = df[df['SNR'].astype(float) != 0]
    if df.empty:
        print(f"No valid data points for {folder_name}. Skipping satellite route plot.")
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

    plt.title(f'Satellite Route for {folder_name}')
    
    os.makedirs(os.path.join('images', folder_name), exist_ok=True)
    plt.savefig(os.path.join('images', folder_name, 'satellite_route.png'), dpi=300)
    plt.close()
    create_thumbnail(os.path.join('images', folder_name, 'satellite_route.png'), os.path.join('images', folder_name, 'satellite_route_thumb.png'))

# Function to plot a polar plot showing azimuth and elevation for a specific pass
def plot_polar(df, folder_name, pass_timestamp, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    
    for _, row in df.iterrows():
        azimuth = np.deg2rad(row['Azimuth'])
        elevation = row['Elevation']
        snr = row['SNR']
        
        norm = plt.Normalize(snr_min, snr_max)
        color = cm.jet(norm(snr))
        
        ax.scatter(azimuth, elevation, c=[color], cmap='jet', edgecolors='w', s=50)
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)

    cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap='jet'), ax=ax, pad=0.1)
    cbar.set_label('SNR (dB)')
    cbar.set_ticks(np.linspace(snr_min, snr_max, num=5))
    cbar.ax.set_yticklabels([f'{tick:.2f}' for tick in np.linspace(snr_min, snr_max, num=5)])
    
    plt.title(f'Polar Plot of Azimuth and Elevation for {folder_name}\n(Pass at {pass_timestamp})')
    filename = os.path.join('images', folder_name, 'polar_plot.png')
    plt.savefig(filename)
    plt.close()
    create_thumbnail(filename, filename.replace('.png', '_thumb.png'))

# Function to plot an inverted polar plot
# This shows the azimuth and elevation, but the elevation is inverted for a different perspective
def plot_polar_map(df, folder_name, pass_timestamp, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    
    for _, row in df.iterrows():
        azimuth = np.deg2rad(row['Azimuth'])
        elevation = 90 - row['Elevation']
        snr = row['SNR']
        
        norm = plt.Normalize(snr_min, snr_max)
        color = cm.jet(norm(snr))
        
        ax.scatter(azimuth, elevation, c=[color], cmap='jet', edgecolors='w', s=50)
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    ax.set_yticks(np.arange(0, 91, 15))
    ax.set_yticklabels([str(int(label)) for label in np.arange(90, -1, -15)])

    cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap='jet'), ax=ax, pad=0.1)
    cbar.set_label('SNR (dB)')
    cbar.set_ticks(np.linspace(snr_min, snr_max, num=5))
    cbar.ax.set_yticklabels([f'{tick:.2f}' for tick in np.linspace(snr_min, snr_max, num=5)])
    
    plt.title(f'Inverted Polar Plot of Azimuth and Elevation for {folder_name}\n(Pass at {pass_timestamp})')
    filename = os.path.join('images', folder_name, 'polar_plot_inverted.png')
    plt.savefig(filename)
    plt.close()
    create_thumbnail(filename, filename.replace('.png', '_thumb.png'))

# Function to plot combined polar plots for all passes for a specific decoder
# This shows the azimuth and elevation for multiple passes on the same plot
def plot_polar_all(df, decoder, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    
    for _, row in df.iterrows():
        azimuth = np.deg2rad(row['Azimuth'])
        elevation = row['Elevation']
        snr = row['SNR']
        
        norm = plt.Normalize(snr_min, snr_max)
        color = cm.jet(norm(snr))
        
        ax.scatter(azimuth, elevation, c=[color], cmap='jet', edgecolors='w', s=50)
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)

    cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap='jet'), ax=ax, pad=0.1)
    cbar.set_label('SNR (dB)')
    cbar.set_ticks(np.linspace(snr_min, snr_max, num=5))
    cbar.ax.set_yticklabels([f'{tick:.2f}' for tick in np.linspace(snr_min, snr_max, num=5)])
    
    plt.title(f'Combined Polar Plot of Azimuth and Elevation for Decoder {decoder}')
    filename = os.path.join('images', f'polar_plot_all_{decoder}.png'.replace(':', '-').replace('/', '_'))
    plt.savefig(filename)
    plt.close()

# Function to plot combined inverted polar plots for all passes for a specific decoder
# This shows the azimuth and elevation for multiple passes on the same plot, with elevation inverted
def plot_polar_all_map(df, decoder, snr_min, snr_max):
    fig = plt.figure(figsize=(18, 18))
    ax = fig.add_subplot(111, polar=True)
    
    for _, row in df.iterrows():
        azimuth = np.deg2rad(row['Azimuth'])
        elevation = 90 - row['Elevation']
        snr = row['SNR']
        
        norm = plt.Normalize(snr_min, snr_max)
        color = cm.jet(norm(snr))
        
        ax.scatter(azimuth, elevation, c=[color], cmap='jet', edgecolors='w', s=50)
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 90)
    ax.set_yticks(np.arange(0, 91, 15))
    ax.set_yticklabels([str(int(label)) for label in np.arange(90, -1, -15)])

    cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap='jet'), ax=ax, pad=0.1)
    cbar.set_label('SNR (dB)')
    cbar.set_ticks(np.linspace(snr_min, snr_max, num=5))
    cbar.ax.set_yticklabels([f'{tick:.2f}' for tick in np.linspace(snr_min, snr_max, num=5)])
    
    plt.title(f'Combined Inverted Polar Plot of Azimuth and Elevation for Decoder {decoder}')
    filename = os.path.join('images', f'polar_plot_all_inverted_{decoder}.png'.replace(':', '-').replace('/', '_'))
    plt.savefig(filename)
    plt.close()

