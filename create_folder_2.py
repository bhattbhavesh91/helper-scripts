import os
import shutil
from datetime import datetime

def create_folders_and_move_files(directory):
    # Loop through all files in the specified directory
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        
        # Skip directories, only process files
        if os.path.isdir(file_path):
            continue

        # Extract the file extension
        file_extension = os.path.splitext(file_name)[1]

        # Process only image or video files with the expected naming format
        if file_extension.lower() in ['.jpg', '.mp4']:

            # Assuming the format of the file name is "yyyyMMdd_hhmmss_SSS"
            # Extract the date part (first 8 characters from the file name)
            date_str = file_name[:8]  # Get the first 8 characters (yyyyMMdd)

            try:
                # Parse the date from the filename (assuming format YYYYMMDD)
                date_obj = datetime.strptime(date_str, '%Y%m%d')

                # Get the month and year
                month = date_obj.strftime('%m')
                year = date_obj.strftime('%Y')

                # Create the folder name in MM YYYY format
                folder_name = f"{month} {year}"

                # Create the folder if it doesn't exist
                folder_path = os.path.join(directory, folder_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)

                # Move the file into the corresponding folder
                shutil.move(file_path, os.path.join(folder_path, file_name))
                print(f"Moved {file_name} to {folder_name}/")
            
            except ValueError as e:
                print(f"Error processing file {file_name}: {e}")

if __name__ == "__main__":
    # Provide the path to your directory containing the files
    directory_path = "/Volumes/T5_2/S20 FE Videos/Camera"
    
    create_folders_and_move_files(directory_path)