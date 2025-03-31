import os
import zipfile

def zip_files_in_chunks(folder_path, chunk_size_mb=20):
    # Get all the files in the folder
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    chunk_size_bytes = chunk_size_mb * 1024 * 1024  # Convert MB to bytes
    
    zip_counter = 1
    current_zip = None
    current_zip_size = 0
    
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        
        # Check the size of the file
        file_size = os.path.getsize(file_path)
        
        # If the current zip file is None or the current zip file size exceeds the chunk limit, start a new zip file
        if current_zip is None or current_zip_size + file_size > chunk_size_bytes:
            # Close the current zip file (if any)
            if current_zip:
                current_zip.close()
            
            # Create a new zip file
            zip_file_name = os.path.join(folder_path, f"archive_{zip_counter}.zip")
            current_zip = zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED)
            current_zip_size = 0  # Reset current zip file size
            zip_counter += 1
        
        # Add the current file to the zip file
        current_zip.write(file_path, arcname=file_name)
        current_zip_size += file_size
        
        # Delete the file after adding it to the zip
        os.remove(file_path)
        print(f"Added {file_name} and deleted it.")
    
    # Close the last zip file
    if current_zip:
        current_zip.close()
        print(f"Created {zip_counter-1} zip files in total.")
    
    print("Process completed.")

# Usage
folder_path = "/Users/bhaveshbhatt/Downloads/a1"
zip_files_in_chunks(folder_path)