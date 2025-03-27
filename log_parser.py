import os
import re
import json
import pandas as pd
from datetime import datetime
import glob

# Constants for directories

# Function to find all log files in a directory
def find_log_files(directory='logs'):
    # Returns a list of paths to log files in the specified directory
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.log')]

# Function to convert a timestamp string to a datetime object
def convert_timestamp(timestamp_str):
    try:
        # Convert timestamp in the format "HH:MM:SS - DD/MM/YYYY" to a datetime object
        return datetime.strptime(timestamp_str, '%H:%M:%S - %d/%m/%Y')
    except ValueError:
        return None

# Function to extract values from a line of log containing progress data
def extract_values_from_progress_line(line, folder_name):
    # Initialize a dictionary with default None values
    values = {
        'Timestamp': None,
        'SNR': None,
        'Peak_SNR': None,
        'Viterbi': None,
        'BER': None,
        'Deframer': None,
        'folder_name': folder_name
    }

    # Extract timestamp from the line
    timestamp_match = re.match(r'\[(.*?)\]', line)
    if timestamp_match:
        timestamp_str = timestamp_match.group(1)
        values['Timestamp'] = convert_timestamp(timestamp_str)
    
    # Extract SNR, Peak SNR, Viterbi, BER, and Deframer values using regular expressions
    snr_match = re.search(r'SNR\s*:\s*(\d+\.\d+)dB', line)
    peak_snr_match = re.search(r'Peak\s*SNR\s*:\s*(\d+\.\d+)dB', line)
    viterbi_match = re.search(r'Viterbi\s*:\s*(\w+)', line)
    ber_match = re.search(r'BER\s*:\s*(\d+\.\d+)', line)
    deframer_match = re.search(r'Deframer\s*:\s*(\w+)', line)
    
    # Update the dictionary with extracted values
    if snr_match:
        values['SNR'] = snr_match.group(1)
    if peak_snr_match:
        values['Peak_SNR'] = peak_snr_match.group(1)
    if viterbi_match:
        values['Viterbi'] = viterbi_match.group(1)
    if ber_match:
        values['BER'] = ber_match.group(1)
    if deframer_match:
        values['Deframer'] = deframer_match.group(1)
    
    return values

# Function to process all log files and extract relevant data
def process_log_files(files):
    log_entries = []  # List to hold all log entries
    current_entry = None
    folder_name = None

    # Iterate through each file in the list
    for file in files:
        with open(file, 'r') as f:
            for line in f:
                # AOS and LOS support only live decode
                # can be changed to (I) Start processing... and (I) Stop processing
                if '(I) Start processing...' in line:
                    # Start a new entry when 'AOS!!!!!!!!!!!!!!' is found
                    if current_entry:
                        log_entries.append(current_entry)
                    current_entry = {
                        'start': None,
                        'end': None,
                        'logs': []
                    }
                elif '(I) Stop processing' in line:
                    # Close the entry when '(I) Stop processing' is found
                    if current_entry:
                        current_entry['end'] = convert_timestamp(re.match(r'\[(.*?)\]', line).group(1))
                        log_entries.append(current_entry)
                        current_entry = None
                elif 'Generated folder name' in line:
                    # Extract the folder name from the line
                    folder_name = re.search(r'[^/\\]+$', line).group(0).strip()
                elif current_entry and '(I) Progress' in line:
                    # Process lines containing progress data
                    if not current_entry['start']:
                        current_entry['start'] = convert_timestamp(re.match(r'\[(.*?)\]', line).group(1))
                    values = extract_values_from_progress_line(line, folder_name)
                    values['Timestamp'] = convert_timestamp(re.match(r'\[(.*?)\]', line).group(1))
                    current_entry['logs'].append(values)
    
    # Append any remaining current entry to the log entries list
    if current_entry:
        log_entries.append(current_entry)
    
    return log_entries

# Function to create a DataFrame from the log entries
def create_dataframe(log_entries):
    rows = []
    for entry in log_entries:
        for log in entry['logs']:
            rows.append(log)
    
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(rows)
    return df

# Function to merge rows in the DataFrame with the same Timestamp
# Mergeing SNR	Peak_SNR line with BER, SYNC line:
    
# Timestamp	             SNR	Peak_SNR	Viterbi	BER	        Deframer
#2024-07-23 02:38:30			            SYNCED	0.081787	SYNCED
#2024-07-23 02:38:40   8.158834	 8.659492			

def merge_rows(df):
    def merge_group(group):
        merged = {}
        # For each column, pick the first non-null value in the group
        
        for col in group.columns:
            merged[col] = group[col].dropna().iloc[0] if not group[col].dropna().empty else None
        return pd.Series(merged)

    # Apply the merge_group function to each group of rows with the same Timestamp
    merged_df = df.groupby('Timestamp').apply(merge_group).reset_index(drop=True)
    return merged_df

# Function to find the JSON file associated with a specific folder name
def find_json_file(directory, folder_name):
    pattern = os.path.join(directory, folder_name, 'dataset.json')
    files = glob.glob(pattern)
    return files[0] if files else None

# Function to read and extract data from a JSON file
def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        satellite = data.get('satellite')
        timestamp = data.get('timestamp')
        return satellite, timestamp

# Function to add JSON data (satellite name and pass timestamp) to the DataFrame
def add_json_data(df, json_directory='images'):
    df['satellite'] = 'Unknown'
    df['pass_timestamp'] = None

    # Iterate through each row of the DataFrame and add data from the corresponding JSON file
    for index, row in df.iterrows():
        folder_name = row['folder_name']
        json_file = find_json_file(json_directory, folder_name)
        
        #print(json_file)
        
        if json_file:
            satellite, timestamp = read_json_file(json_file)
            df.at[index, 'satellite'] = satellite
            if timestamp==-1:
                timestamp=0
            df.at[index, 'pass_timestamp'] = convert_timestamp_to_datetime(timestamp)
    
    return df

# Function to extract the decoder identifier from the folder name
def extract_decoder_from_folder_name(folder_name):
    parts = folder_name.split('_')
    if len(parts) > 1:
        return parts[-2]  # Assuming the decoder ID is the second last part of the folder name
                          # i.e 2024-07-22_02-55_meteor_m2-x_lrpt_137.9 MHz
    return 'Unknown'

# Function to convert a timestamp (as a float) to a datetime object
def convert_timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)
