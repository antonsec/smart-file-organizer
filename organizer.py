from pathlib import Path

test_folder = Path("test_files")
print("Scanning folder:", test_folder)

file_types = {
    ".jpg": "Picture",
    ".png": "Picture",
    ".jpeg": "Picture",
    ".pdf": "Document",
    ".txt": "Document",
    ".mp3": "Audio",
    ".mp4": "Video",
    ".zip": "Archive",
    ".py": "Code",
}

for item in test_folder.iterdir():
    category = file_types.get(item.suffix, "Unknown")
    print(f"{item.name} → {category}")