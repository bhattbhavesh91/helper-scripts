import os

def find_file(base_folder, target_filename):
    """
    Searches for a file in the given base folder and its subdirectories.
    The search is case-insensitive for both filename and extension.
    
    Args:
        base_folder (str): Path to the starting directory.
        target_filename (str): File name to search for (case-insensitive).
    
    Returns:
        list[str]: List of full paths to matching files.
    """
    found_files = []
    target_filename_lower = target_filename.lower()

    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.lower() == target_filename_lower:
                full_path = os.path.join(root, file)
                found_files.append(full_path)

    return found_files

if __name__ == "__main__":
    base_folder = "/Volumes/BhavBlue2TB/Pics/"
    target_filename = "IMG_2201.heic"

    prefix, number = target_filename.split("_")
    number_part, extension = number.split(".")

    # Convert number part to integer
    start_num = int(number_part)
    end = 20

    # Generate the filenames
    for i in range(end + 1):  # +1 to include the end value
        new_num = start_num + i
        new_file_name = f"{prefix}_{new_num:04d}.{extension}"
        print(new_file_name)

        matches = find_file(base_folder, new_file_name)

        if matches:
            print(f"\nFound {len(matches)} match(es):")
            for path in matches:
                print(" →", path)
        else:
            print("\nFile not found.")
