🌍 Satdump Log Visualiser

A Python tool that processes and visualizes satellite pass logs from SatDump. It enriches satellite data with elevation, azimuth, and distance information, generates plots and maps, and produces interactive HTML reports for easy analysis.

✨ Features

🛰️ Parses SatDump log files for satellite pass information

📈 Enriches data with azimuth, elevation, distance, and TLE-based calculations

🗺️ Generates:

SNR vs. Elevation plots

Satellite ground tracks

Polar and inverted polar plots

Heatmaps and galleries from decoded image sets

📊 Creates an interactive HTML summary of all satellite passes

⚙️ Auto-downloads and updates TLE files

🚀 Getting Started

1. Clone the repository

git clone https://github.com/yourusername/satdump-log-visualiser.git
cd satdump-log-visualiser

2. Install dependencies

Install the required Python packages using:

pip install -r requirements.txt

Ensure you have Python 3.7+ installed.

3. Configure your setup

On first run, a config.json file will be created with default values:

{
  "DATASETS_DIRECTORY": "datasets",
  "LOG_DIRECTORY": "logs",
  "OUTPUT_DIRECTORY": "visualizations",
  "TLE_FILE_PATH": "weather.txt",
  "OBSERVER_LAT": 50.0,
  "OBSERVER_LON": 20.0,
  "OBSERVER_ELEVATION": 250,
  "UPDATE_DAYS": 1
}

Update OBSERVER_LAT, OBSERVER_LON, and OBSERVER_ELEVATION to your actual location for accurate plots.

📦 How to Use

Start the visualiser:

python3 main.py

Menu options:

Process LogsParses SatDump logs and extracts meaningful information.

Generate VisualizationsEnriches the data and creates plots + HTML reports.

Open Summary HTMLOpens the main summary page in your browser.

Purge Generated FilesRemoves generated plots and reports to clean up.

📁 Folder Structure

After running the visualiser, you'll get a folder like this:

visualizations/
├── NOAA_19_.../
│   ├── SNR_and_Elevation_plot.png
│   ├── satellite_route.png
│   ├── polar_plot.png
│   ├── polar_plot_inverted.png
│   ├── satellite_route.html  ← heatmap
│   ├── images.html           ← decoded image gallery
├── polar_plot_all_NOAA.png
├── summary.html

📡 TLE Handling

The app fetches weather satellite TLEs from Celestrak.If the TLE file is missing or outdated (based on UPDATE_DAYS), it will download the latest one automatically.

🛠 Requirements

Python 3.7+

Libraries:

numpy, pandas, matplotlib, cartopy

skyfield, folium, jinja2

colorama, Pillow, requests

A requirements.txt file can be generated if needed.

📷 Example



Example of an SNR and Elevation Plot

🧑‍💻 Author

Your Name📅 Initial Release: YYYY-MM-DD

📄 License

MIT License — Free for personal and commercial use with attribution.