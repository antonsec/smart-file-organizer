# 📂 Smart File Organizer

A Python application that automatically organizes files into folders based on their file type.

This project was built to practice Python fundamentals such as file handling, dictionaries, loops, the `pathlib` module, and Git version control.

---

## ✨ Features

* Automatically scans a folder of files.
* Detects file types using file extensions.
* Creates category folders if they don't already exist.
* Moves files into the correct folder.
* Counts how many files belong to each category.
* Displays a summary after organizing.

---

## 📁 Supported File Types

| Category  | Extensions                |
| --------- | ------------------------- |
| Pictures  | `.jpg`, `.jpeg`, `.png`   |
| Documents | `.pdf`, `.txt`            |
| Audio     | `.mp3`                    |
| Video     | `.mp4`                    |
| Archive   | `.zip`                    |
| Code      | `.py`                     |
| Unknown   | Any unsupported extension |

---

## 📂 Project Structure

```text
smart-file-organizer/
│
├── organizer.py
├── README.md
├── requirements.txt
├── test_files/
├── sorted_files/
└── .gitignore
```

---

## 🚀 How to Run

Clone the repository:

```bash
git clone https://github.com/antonsec/smart-file-organizer.git
```

Move into the project folder:

```bash
cd smart-file-organizer
```

Run the program:

```bash
python3 organizer.py
```

---

## 📸 Example

### Before

```text
test_files/
├── photo.jpg
├── report.pdf
├── notes.txt
├── song.mp3
├── movie.mp4
└── script.py
```

### After

```text
sorted_files/
├── Pictures/
│   └── photo.jpg
├── Documents/
│   ├── report.pdf
│   └── notes.txt
├── Audio/
│   └── song.mp3
├── Video/
│   └── movie.mp4
└── Code/
    └── script.py
```

---

## 🛠 Technologies Used

* Python 3
* pathlib
* shutil
* Git
* GitHub
* Visual Studio Code

---

## 📚 What I Learned

While building this project I practiced:

* Working with files and folders
* Using the `pathlib` module
* Python dictionaries
* Loops
* Functions from the `shutil` module
* Git version control
* Creating and managing GitHub repositories

---


## 👤 Author

**Pierre Anton**

GitHub: https://github.com/antonsec
