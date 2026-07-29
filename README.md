# 📂 Smart File Organizer

Smart File Organizer is a Python application that automatically sorts files into folders based on their file extension.

The user simply chooses a folder, and the program creates organised folders such as **Pictures**, **Documents**, **Audio**, and **Video**, then moves the files automatically.

---

## ✨ Features

* Organises any folder chosen by the user.
* Automatically creates category folders.
* Detects common file types.
* Moves files into the correct folder.
* Handles unknown file types.
* Ignores subfolders.
* Displays a summary after every run.

---

## 📁 Supported Categories

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

## 🚀 How to Run

Clone the repository:

```bash
git clone https://github.com/antonsec/smart-file-organizer.git
```

Enter the project folder:

```bash
cd smart-file-organizer
```

Run the program:

```bash
python3 organizer.py
```

When prompted, enter the folder you want to organise.

Example:

```text
📂 Smart File Organizer
------------------------------
Enter the folder you want to organize:
/Users/username/Downloads
```

---

## 📸 Example Output

```text
📂 Smart File Organizer
------------------------------

Scanning: /Users/username/Downloads

✅ photo.jpg → Pictures
✅ report.pdf → Documents
✅ notes.txt → Documents
✅ song.mp3 → Audio

Summary
------------------------------
Pictures : 1
Documents: 2
Audio     : 1
Video     : 0
Archive   : 0
Code      : 0
Unknown   : 0
```

---

## 🛠 Built With

* Python 3
* pathlib
* shutil
* Git
* GitHub
* Visual Studio Code

---

## 📚 Skills Demonstrated

* File handling
* Dictionaries
* Loops
* Python modules
* Object-oriented file paths with `pathlib`
* Error handling
* Git version control
* GitHub workflow


---

## 👤 Author

Pierre Anton

GitHub: https://github.com/antonsec
