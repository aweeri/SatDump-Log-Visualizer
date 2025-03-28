# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 11:07:41 2024

@author: kslawek
"""

from log_parser import *
from add_azel import *
from generate_summary import *
from tle_utils import *
import json

LIVE_OUTPUT_DIRECTORY = ""
LOG_DIRECTORY         = ""
TLE_FILE_PATH         = ""
PROCESS_TYPE          = ""

OBSERVER_LAT = 0
OBSERVER_LON = 0
OBSERVER_ELEVATION = 0


# Main function to process log files and generate an Excel file
def main():
    
    # Wczytywanie konfiguracji z pliku JSON
    with open('config.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
    
    # read config
    LIVE_OUTPUT_DIRECTORY = config['LIVE_OUTPUT_DIRECTORY']
    LOG_DIRECTORY         = config['LOG_DIRECTORY']
    TLE_FILE_PATH         = config['TLE_FILE_PATH']
    
    OBSERVER_LAT       = config['OBSERVER_LAT']
    OBSERVER_LON       = config['OBSERVER_LON']
    OBSERVER_ELEVATION = config['OBSERVER_ELEVATION']
    PROCESS_TYPE       = config['PROCESS_TYPE']
    UPDATE_DAYS        = config['UPDATE_DAYS']

    
    #DUMP
    ###############################################################################################    
    if(PROCESS_TYPE in ['both','dump']):
            
        # Find all log files in the specified directory
        log_files = find_log_files(directory=LOG_DIRECTORY)
    
        # Process the log files and extract relevant data
        log_entries = process_log_files(log_files)
    
        # Create a DataFrame from the log entries
        log_df = create_dataframe(log_entries)
    
        # Merge rows with the same Timestamp
        merged_log_df = merge_rows(log_df)
    
    
        # Add data from JSON files to the DataFrame
        merged_log_df = add__dataset_json_data(merged_log_df,json_directory=LIVE_OUTPUT_DIRECTORY)
    
    
        # Extract decoder information from the folder names
        merged_log_df['decoder'] = merged_log_df['folder_name'].apply(extract_decoder_from_folder_name)
    
        # Filter out rows where the satellite name is 'Unknown'
        merged_log_df = merged_log_df[~merged_log_df['satellite'].str.contains('Unknown')]
    
        load = Loader('.')
        ts = load.timescale()
        
    
        # Save the processed data to an Excel file
        merged_log_df.to_excel('parsed_log_data.xlsx', index=False)
        
        df = pd.read_excel('parsed_log_data.xlsx')
        satellites = load.tle_file(TLE_FILE_PATH)

        #weird error when trying to remove apt decoders before adding azimuth, elevation and distance
        #df = df[df["decoder"]!="apt"] #remove apt decoders

         
        enriched_df = add_azimuth_elevation_distance(df, satellites,OBSERVER_LAT, OBSERVER_LON, OBSERVER_ELEVATION)
        enriched_df.to_excel('final_processed_log_data_enriched.xlsx', index=False)
    
    #end of dump section
    ###############################################################################################
    
    #start of visualize section
    ###############################################################################################
    
    if(PROCESS_TYPE in ['both','visualize']):
        download_tle_if_necessary(UPDATE_DAYS)  # Ensure that TLE data is up to date
    
        # Load the processed log data
        df = pd.read_excel('final_processed_log_data_enriched.xlsx')

        df = df[df["decoder"]!="apt"] #remove apt decoders
        
        
        #remove broken rows with infinite values
        df = df[
            pd.notna(df['Azimuth']) &
            pd.notna(df['Elevation']) &
            pd.notna(df['SNR']) &
            np.isfinite(df['Azimuth']) &
            np.isfinite(df['Elevation']) &
            np.isfinite(df['SNR'])
        ]

        
        df['satellite'] = df['satellite'].str.replace('-', ' ', 1)
    
        # Process each folder in the data
        for folder_name, folder_df in df.groupby('folder_name'):
            plot_snr_and_elevation(folder_df, folder_name)  # Plot SNR and elevation
            plot_satellite_route(folder_df, folder_name)  # Plot satellite route
            generate_visualization_html(folder_df, folder_name)  # Generate visualization HTML
            generate_images_html(folder_name)  # Generate images HTML
    
            snr_min = folder_df['SNR'].min()
            snr_max = folder_df['SNR'].max()
    
            # Process each pass within the folder
            for pass_timestamp in folder_df['pass_timestamp'].unique():
                pass_df = folder_df[folder_df['pass_timestamp'] == pass_timestamp]
    
                plot_polar(pass_df, folder_name, pass_timestamp, snr_min, snr_max)  # Plot polar plot
                plot_polar_map(pass_df, folder_name, pass_timestamp, snr_min, snr_max)  # Plot inverted polar plot
    
        # Generate combined plots for each decoder
        for decoder in df['decoder'].unique():
            decoder_df = df[df['decoder'] == decoder]
    
            snr_min = decoder_df['SNR'].min()
            snr_max = decoder_df['SNR'].max()
    
            plot_polar_all(decoder_df, decoder, snr_min, snr_max)  # Plot combined polar plot
            plot_polar_all_map(decoder_df, decoder, snr_min, snr_max)  # Plot combined inverted polar plot
    
        generate_summary_html(df)  # Generate the summary HTML
    
    #end of visualize section
    ###############################################################################################
    
if __name__ == '__main__':
     main()