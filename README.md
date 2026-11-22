# Smart File Organizer

A Python command-line tool that sorts files by type into `sorted_files/` inside your chosen folder. It previews changes and asks before moving anything.

Built by **Pierre Anton** · [GitHub](https://github.com/antonsec)

## Getting started

Requires **Python 3.9+**. No extra packages are needed.

```bash
git clone https://github.com/antonsec/smart-file-organizer.git
cd smart-file-organizer
python3 organizer.py ~/Downloads --dry-run
```

This previews the changes without moving files. To organize the folder, run:

```bash
python3 organizer.py ~/Downloads
```

Check the preview, then enter `y` to confirm. On Windows, use `python` instead of `python3` and supply your folder path. Put paths with spaces in quotes.

| Option | What it does |
| --- | --- |
| `--dry-run` | Preview without changing anything |
| `--yes` or `-y` | Move files without asking for confirmation |
| `--config PATH` | Use custom sorting rules |

If you leave out the folder path, the tool asks for one. Choose the target folder carefully: project files are eligible too.

## What gets sorted?

Files go into Pictures, Documents, Audio, Video, Archive, Code, or Unknown folders. Only files directly inside the chosen folder are sorted. Hidden files, subfolders, and symbolic links are skipped.

For example:

```text
photo.jpg    → sorted_files/Pictures/photo.jpg
notes.txt    → sorted_files/Documents/notes.txt
backup.zip   → sorted_files/Archive/backup.zip
```

Existing files are never overwritten. If a name is taken, the tool adds a number, such as `notes_1.txt` or `backup_1.tar.gz`.

## Custom rules

Create a JSON file, or edit `rules.example.json`:

```json
{
  ".pdf": "Reading",
  ".blend": "Design"
}
```

Then preview with it:

```bash
python3 organizer.py ~/Downloads --config rules.example.json --dry-run
```

Custom rules extend or replace the defaults. Use plain folder names; paths, hidden names, control characters, and Windows reserved names such as `CON` are rejected. Longer extensions, such as `.tar.gz`, match first.

Keep the config outside the folder being sorted, or give it a hidden name such as `.organizer-rules.json` so it is skipped.

## Safety and limits

Keep backups of important files. There is no undo command.

- Files are copied before the originals are deleted, so extra disk space is needed. Some platform-specific metadata may not be preserved.
- If a move fails, the error is reported and remaining files are attempted. If the original cannot be deleted, both copies remain.
- Incomplete copies are removed when possible. If cleanup fails, the error identifies the leftover file for you to inspect before retrying.
- Ctrl+C stops the run; completed moves stay in place. A forced shutdown can leave a partial copy.
- Avoid editing files or running another organizer on the same folder during a run. Output folders that are symbolic links are rejected.

Exit codes: `0` success, preview, or declined confirmation; `1` file or configuration error; `2` invalid command; `130` cancellation.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests use temporary folders and cover sorting, collisions, custom rules, file errors, and cancellation. GitHub Actions is configured to test Python 3.9 and 3.13 on Linux, macOS, and Windows.

The implementation is in `organizer.py`, with separate functions for planning and moving files. It uses only the Python standard library.
