print ("Welcome to Smart File Organizer!")
from pathlib import Path

current_folders = Path.cwd()

print ("Current folders:")
print(current_folders)
print()
print("Contents:")

for item in current_folders.iterdir():
    if item.is_file():
        print (item.name,"-> File")
    else:
        print(item.name,"-> Folder")