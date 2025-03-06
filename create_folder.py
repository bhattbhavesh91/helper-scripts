import os
import shutil
from datetime import datetime

def create_folders_and_move_files(file_list):
    # Loop through each file in the list
    for file_path in file_list:
        # Extract the file name and extension
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_name)[1]

        # Assuming the format of the file name is IMGyyyyMMddhhmmss or VIDyyyyMMddhhmmss
        # Extract the date part (first 14 characters from IMG/VID)
        date_str = file_name[3:15]
        
        try:
            # Parse the date from the filename (assuming format YYYYMMDDhhmmss)
            date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')

            # Get the month and year
            month = date_obj.strftime('%m')
            year = date_obj.strftime('%Y')

            # Create the folder name in MM YYYY format
            folder_name = f"{month} {year}"

            # Create a folder if it doesn't exist
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)

            # Move the file into the corresponding folder
            shutil.move(file_path, os.path.join(folder_name, file_name))
            print(f"Moved {file_name} to {folder_name}/")
        
        except ValueError as e:
            print(f"Error processing file {file_name}: {e}")

if __name__ == "__main__":
    # List your file paths here (adjust these with your actual file paths)
    files = [
        "IMG20211101113457.jpg",
        "VID20220625214030.mp4"
    ]
    
    create_folders_and_move_files(files)
