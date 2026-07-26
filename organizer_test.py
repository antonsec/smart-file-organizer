from pathlib import Path

test_files = Path("test_files")
print("Scanning folder:", test_files)

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

count = { #Using this to count the number of files in each category
    "Pictures": 0,
    "Documents": 0,
    "Audio": 0,
    "Video": 0,
    "Archive": 0,
    "Code": 0,
}  

for item in test_files.iterdir(): #Picking each file in the test_files folder
    category = file_types.get(item.suffix, "Unknown") #Organizing the files based on their extensions   
    
    count[category] += 1 #Adding the count of each file type to the count dictionary



for category, amount in count.items():
    print(f"{category}: {amount}") #Printing the count of each file type in the test_files folder