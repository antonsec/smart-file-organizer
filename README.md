# Smart File Organizer

A dependency-free Python CLI that sorts a folder into categories, previews exact destinations, and handles filename collisions without overwriting existing files.

Built by **Pierre Anton** · [GitHub](https://github.com/antonsec)

## Quick start

Requires **Python 3.9+**. No third-party packages are needed.

```bash
git clone https://github.com/antonsec/smart-file-organizer.git
cd smart-file-organizer
python3 -m venv .venv
source .venv/bin/activate
python organizer.py ~/Downloads --dry-run
```

On Windows, activate with `.venv\Scripts\activate` instead.

To apply, omit `--dry-run`. The program shows its plan and asks for confirmation:

```bash
python organizer.py ~/Downloads
```

No path supplied? The program prompts for one. Quote paths containing spaces.

```bash
python organizer.py
python organizer.py "/path/to/My Files" --dry-run
python organizer.py ~/Downloads --yes
```

`--yes` skips confirmation, making scripted runs possible. Run it only against the folder you intend to organize: project source files are eligible too.

## Example

```text
Smart File Organizer
------------------------------
Preview: notes.txt -> sorted_files/Documents/notes_1.txt
Preview: photo.JPG -> sorted_files/Pictures/photo.JPG

Planned: 2 file(s).
Move these files? [y/N]: y
Moved: notes.txt -> sorted_files/Documents/notes_1.txt
Moved: photo.JPG -> sorted_files/Pictures/photo.JPG

Summary
------------------------------
Documents   : 1
Pictures    : 1
Moved 2 file(s); failed 0.
```

Here `notes.txt` already existed in the destination, so the incoming file was renamed. Compound extensions are preserved: `backup.tar.gz` becomes `backup_1.tar.gz`.

## Features

- Deterministic previews with exact collision-adjusted destinations.
- Dry runs create no files or directories.
- Confirmation before applying; explicit `--yes` for automation.
- Case-insensitive extension matching and collision planning.
- Hidden files, subfolders and symbolic links are skipped.
- Existing output directory symbolic links are rejected.
- Exclusive destination creation prevents overwriting a file that appears after preview.
- Per-file errors are reported; remaining files are still attempted.
- Summary counts include successful moves only.
- Ctrl+C exits cleanly; completed moves remain in place.
- JSON category overrides without third-party dependencies.

## Categories

| Category | Examples |
| --- | --- |
| Pictures | `.jpg`, `.png`, `.heic`, `.svg`, `.raw` |
| Documents | `.pdf`, `.txt`, `.docx`, `.xlsx`, `.md` |
| Audio | `.mp3`, `.wav`, `.flac`, `.m4a` |
| Video | `.mp4`, `.mov`, `.mkv`, `.webm` |
| Archive | `.zip`, `.7z`, `.tar.gz`, `.tar.bz2` |
| Code | `.py`, `.js`, `.html`, `.json`, `.yaml` |
| Unknown | Unrecognized extensions and extensionless files |

See `CATEGORIES` in `organizer.py` for the complete default mapping.

## Custom categories

Copy `rules.example.json`, edit it, and provide its path:

```bash
python organizer.py ~/Downloads --config rules.example.json --dry-run
```

```json
{
  ".pdf": "Reading",
  ".blend": "Design",
  ".fig": "Design"
}
```

Custom rules extend or override defaults. Category values must be plain folder names; paths, hidden names, control characters, and Windows reserved device names (such as `CON`, `NUL`, or `COM1`, including names like `NUL.txt`) are rejected. Extensions cannot contain control characters either. Longest extensions match first. Keep your config outside the folder being organized, or use a hidden filename such as `.organizer-rules.json` so it is skipped.

## How it works

1. Validate the input folder and load rules.
2. Build a move plan, reserving destination filenames.
3. Display the plan and request confirmation.
4. Copy each source into an exclusively created destination, preserve basic metadata, then remove the source.
5. Report successful moves and errors separately.

Planning and execution are separate functions so behavior can be tested without touching personal folders. The core uses `pathlib`, dataclasses, `argparse`, and standard-library file operations.

### Limits and failure behavior

This is a local utility for folders you control, not a background watcher or a security boundary. Avoid editing files or running multiple organizers against the same folder during a run. Files are not locked; hostile or concurrent changes to paths are outside its guarantees.

Copy-then-delete uses additional disk space and is slower than a rename, but allows exclusive destination creation. Basic metadata is copied; ownership and every platform-specific attribute are not guaranteed. If source deletion fails, both copies remain and the error identifies the completed destination. Ordinary copy errors remove the incomplete destination when possible. If cleanup also fails, the error includes both failures and the destination path; the source remains. Inspect that destination and remove any incomplete copy before retrying. Ctrl+C still stops the run if cleanup fails, with a warning identifying the leftover destination. A forced process kill or power loss may leave a partial file. There is no undo command. Keep backups of important files.

Exit codes: `0` success, dry run or declined confirmation; `1` validation/I/O/move failure; `2` invalid command-line arguments; `130` interrupted input or Ctrl+C.

## Tests

All tests use isolated temporary folders:

```bash
python -m unittest discover -s tests -v
```

Tests cover previews, content preservation, collisions, symlinks, custom rules, permission and copy failures, metadata failures, cleanup failures, continuation after a failed move, confirmation, and interruption. Rule validation tests include Windows reserved names and control characters. GitHub Actions is configured to run the suite on Linux, macOS and Windows with Python 3.9 and 3.13 after pushes and pull requests.

## Project layout

```text
organizer.py           CLI, planning, rules and file execution
rules.example.json     Optional custom rules
requirements.txt       Documents the zero-dependency runtime
tests/                 Standard-library unittest suite
.github/workflows/     Cross-platform CI configuration
```
