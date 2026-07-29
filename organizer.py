from pathlib import Path
import shutil

# Folders
test_files = Path("test_files")
sorted_files = Path("sorted_files")

print(f"Scanning folder: {test_files}")

# File extension -> category
file_types = {
    ".jpg": "Pictures",
    ".png": "Pictures",
    ".jpeg": "Pictures",
    ".pdf": "Documents",
    ".txt": "Documents",
    ".mp3": "Audio",
    ".mp4": "Video",
    ".zip": "Archive",
    ".py": "Code",
}

# Counter for each category
count = {
    "Pictures": 0,
    "Documents": 0,
    "Audio": 0,
    "Video": 0,
    "Archive": 0,
    "Code": 0,
    "Unknown": 0,
}

# Create output folder
sorted_files.mkdir(exist_ok=True)

# Create category folders
for category in count:
    (sorted_files / category).mkdir(exist_ok=True)

# Scan and organize files
for item in test_files.iterdir():

    # Skip anything that isn't a file
    if not item.is_file():
        continue

    # Find category
    category = file_types.get(item.suffix.lower(), "Unknown")

    # Count it
    count[category] += 1

    # Destination folder
    destination_folder = sorted_files / category

    # Move file
    shutil.move(item, destination_folder / item.name)

    print(f"Moved {item.name} -> {category}")

# Summary
print("\nSummary:")
for category, amount in count.items():
    print(f"{category}: {amount}")