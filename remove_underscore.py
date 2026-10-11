import os

directory = "/Users/bhaveshbhatt/Downloads/Book Photos"

for filename in os.listdir(directory):
    old_path = os.path.join(directory, filename)

    if os.path.isfile(old_path) and "_" in filename:
        new_filename = filename.replace("_", "")
        new_path = os.path.join(directory, new_filename)

        if os.path.exists(new_path):
            print(f"Skipped (destination exists): {new_filename}")
            continue

        os.rename(old_path, new_path)
        print(f"Renamed: {filename} -> {new_filename}")

print("Done!")
