## 🌍 Satdump Log Visualiser

A Python tool that processes and visualizes satellite pass logs from SatDump. It enriches satellite data with elevation, azimuth, and distance information, generates plots and maps, and produces interactive HTML reports for easy analysis of your LOS conditions

![New Project(1)](https://github.com/user-attachments/assets/200d9f9d-bd51-4341-bcfb-84cc3948dc20)


## NOTICE

For the tool to function correctly, you must provide a link to your unaltered `live_output` directory, as it contains the necessary `dataset.json` files. This path should be set as the `DATASETS_DIRECTORY` in your configuration and must point to `live_output` where your named directories with datasets in them are stored.

## Supported Pipelines

- meteor_m2-x_lrpt
- meteor_m2-x_hrpt
- noaa_dsb

## Clone the repository

git clone https://github.com/yourusername/satdump-log-visualiser.git
cd satdump-log-visualiser

## Install dependencies

Ensure you have Python3 installed.
Run `install_requirements.py` by double clicking it or open a terminal and run `pip install -r requirements.txt`.


## Configure your setup

The config file is self-explanatory.
Update the `DATASETS_DIRECTORY`, and `LOG_DIRECTORY` paths.
Update `OBSERVER_LAT`, `OBSERVER_LON`, (and optionally `OBSERVER_ELEVATION`) to your actual location for accurate plots.

## Running the tool

Run `main.py` by simply clicking on it or open a terminal and run `pip install -r requirements.txt` within the tool directory.
