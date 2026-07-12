from pathlib import Path
import shutil
from datetime import datetime

# Base folder containing your files
BASE_DIR = Path(r"/Users/bhaveshbhatt/Downloads/Dhairya")  # <-- Change this

# File extensions to process (add/remove as needed)
FILE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
    ".heic", ".mp4", ".mov", ".avi", ".mkv",
    ".pdf", ".doc", ".docx", ".txt"
}


def ordinal(n: int) -> str:
    """Return ordinal string (1st, 2nd, 3rd...)."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


for item in BASE_DIR.iterdir():
    if not item.is_file():
        continue

    if item.suffix.lower() not in FILE_EXTENSIONS:
        continue

    # Use the file's modified time
    modified = datetime.fromtimestamp(item.stat().st_mtime)

    # Folder names
    month_folder = modified.strftime("%m %Y")            # e.g. "06 2026"
    day_folder = f"{ordinal(modified.day)} {modified.strftime('%B')}"  # e.g. "11th June"

    destination = BASE_DIR / month_folder / day_folder
    destination.mkdir(parents=True, exist_ok=True)

    target = destination / item.name

    # Avoid overwriting existing files
    if target.exists():
        stem = item.stem
        suffix = item.suffix
        counter = 1
        while True:
            new_target = destination / f"{stem}_{counter}{suffix}"
            if not new_target.exists():
                target = new_target
                break
            counter += 1

    print(f"Moving {item.name} -> {target.relative_to(BASE_DIR)}")
    shutil.move(str(item), str(target))

print("Done.")