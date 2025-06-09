import os
import shutil

# Set the directory you want to scan (use "." for current directory)
directory = "."

# Loop through files in the directory
for filename in os.listdir(directory):
    if filename.lower().endswith(".mkv"):
        file_path = os.path.join(directory, filename)
        folder_name = os.path.splitext(filename)[0]
        new_folder_path = os.path.join(directory, folder_name)

        # Create new folder if it doesn't exist
        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)
            print(f"Created folder: {new_folder_path}")

        # Move the MKV file into the new folder
        new_file_path = os.path.join(new_folder_path, filename)
        shutil.move(file_path, new_file_path)
        print(f"Moved '{filename}' to '{new_folder_path}'")
