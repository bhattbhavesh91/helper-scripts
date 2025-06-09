import os
import shutil

def organize_folders_by_letter(base_path):
    # List everything in the base path
    items = os.listdir(base_path)

    for item in items:
        item_path = os.path.join(base_path, item)

        # Process only directories (ignore files)
        if os.path.isdir(item_path):
            first_letter = item[0].upper()
            target_folder = os.path.join(base_path, first_letter)

            # Create letter folder if it doesn't exist
            os.makedirs(target_folder, exist_ok=True)

            # Move the folder into the letter folder
            target_path = os.path.join(target_folder, item)

            # Avoid overwriting or recursive move
            if not os.path.exists(target_path):
                shutil.move(item_path, target_path)
            else:
                print(f"Skipping: {item} - target already exists.")

if __name__ == "__main__":
    base_directory = "/Volumes/BhavBlue2TB/Movies/2020 - 2029/U - Z/"  # Change this to your actual base path
    organize_folders_by_letter(base_directory)
