import os
import re

def generate_filename_range(start_name, end_name):
    """
    Generate a list of filenames from start_name to end_name.
    Assumes filenames have the same prefix, numeric part, and extension.
    Example: IMG_2201.heic → IMG_2222.heic
    """
    pattern = r"(\D*)(\d+)(\.\w+)$"
    match_start = re.match(pattern, start_name)
    match_end = re.match(pattern, end_name)

    if not (match_start and match_end):
        raise ValueError("Filenames must follow a pattern like IMG_2201.heic")

    prefix, start_num, ext = match_start.groups()
    _, end_num, _ = match_end.groups()

    start_num, end_num = int(start_num), int(end_num)
    width = len(match_start.group(2))  # Preserve zero-padding

    return [f"{prefix}{i:0{width}d}{ext}" for i in range(start_num, end_num + 1)]


def find_files_in_range(base_folder, start_name, end_name):
    """
    Searches for all files within the given name range (case-insensitive).
    Returns all matching paths.
    """
    filenames_to_find = [f.lower() for f in generate_filename_range(start_name, end_name)]
    found_files = []

    for root, dirs, files in os.walk(base_folder):
        for file in files:
            if file.lower() in filenames_to_find:
                found_files.append(os.path.join(root, file))

    return found_files


if __name__ == "__main__":
    
    base_folder = "/Volumes/BhavBlue2TB/Pics/"
    start_name = "IMG_2201.heic"
    end_name = "IMG_2210.heic"
    
    try:
        matches = find_files_in_range(base_folder, start_name, end_name)

        if matches:
            print(f"\nFound {len(matches)} file(s):")
            for path in matches:
                print(" →", path)
        else:
            print("\nNo files found in that range.")
    except ValueError as e:
        print("Error:", e)
