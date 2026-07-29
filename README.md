# 📂 Smart File Organizer

Smart File Organizer is a clean and reliable Python tool that automatically sorts files into organised category folders based on their extension.

Just point it at any folder and it will create a `sorted_files/` directory containing subfolders such as **Pictures**, **Documents**, **Audio**, **Video**, **Archive**, **Code**, and **Unknown**.

---

## ✨ Features

* Interactive mode **or** command-line argument
* **Dry-run mode** (`--dry-run`) – preview everything safely
* Automatically creates category folders
* Wide support for common file types
* Skips all hidden/system files (`.DS_Store`, `.localized`, etc.)
* Handles filename collisions gracefully (adds `_1`, `_2`…)
* Ignores all subfolders
* Clear, readable summary after every run
* Robust error handling

---

## 📁 Supported Categories

| Category     | Extensions |
|--------------|------------|
| **Pictures** | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.svg` `.tiff` `.tif` `.heic` `.heif` `.ico` `.raw` `.cr2` `.nef` |
| **Documents**| `.pdf` `.txt` `.rtf` `.doc` `.docx` `.odt` `.xls` `.xlsx` `.ods` `.ppt` `.pptx` `.odp` `.csv` `.md` `.markdown` `.epub` `.mobi` |
| **Audio**    | `.mp3` `.wav` `.flac` `.aac` `.ogg` `.m4a` `.wma` `.aiff` `.opus` |
| **Video**    | `.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpeg` `.mpg` `.3gp` |
| **Archive**  | `.zip` `.rar` `.7z` `.tar` `.gz` `.bz2` `.xz` `.tgz` |
| **Code**     | `.py` `.js` `.ts` `.jsx` `.tsx` `.html` `.css` `.scss` `.java` `.c` `.cpp` `.h` `.hpp` `.cs` `.go` `.rs` `.php` `.rb` `.sh` `.bash` `.json` `.xml` `.yaml` `.yml` `.toml` `.ini` `.cfg` |
| **Unknown**  | Any unsupported extension |

---

## 🚀 How to Run

### 1. Clone the repository
```bash
git clone https://github.com/antonsec/smart-file-organizer.git
cd smart-file-organizer
2. Run the program
Interactive mode (asks for the folder):
Bashpython3 organizer.py
Direct path:
Bashpython3 organizer.py ~/Downloads
Dry-run (recommended first – shows what would happen without moving anything):
Bashpython3 organizer.py ~/Downloads --dry-run

📸 Example Output
text📂 Smart File Organizer
------------------------------

Scanning: /Users/username/Downloads

✅ photo.jpg → Pictures/
✅ report.pdf → Documents/
✅ notes.txt → Documents/
✅ song.mp3 → Audio/
✅ movie.mp4 → Video/
✅ archive.zip → Archive/
✅ script.py → Code/

Summary
------------------------------
Archive     : 1
Audio       : 1
Code        : 1
Documents   : 2
Pictures    : 1
Video       : 1

Moved 7 file(s).
Dry-run example:
text📂 Smart File Organizer
------------------------------

Scanning: /Users/username/Downloads
🔍 DRY-RUN mode – no files will be moved

→ would move  photo.jpg  →  Pictures/
→ would move  report.pdf  →  Documents/
...
