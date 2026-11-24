# Smart File Organizer

A Python command-line tool that sorts files by type. Preview changes, skip files you want to keep, and undo a run using its saved report.

Built by **Pierre Anton** · [GitHub](https://github.com/antonsec)

## Getting started

Requires **Python 3.9+**. No extra packages are needed.

```bash
git clone https://github.com/antonsec/smart-file-organizer.git
cd smart-file-organizer
python3 organizer.py ~/Downloads --dry-run
```

This previews the changes without writing anything. To apply them:

```bash
python3 organizer.py ~/Downloads
```

Check the preview, then enter `y` to confirm. On Windows, use `python` instead of `python3` and supply your folder path. Quote paths with spaces. If you leave out the folder path, the tool asks for one.

| Option | What it does |
| --- | --- |
| `--dry-run` | Preview without changing files or reports |
| `--yes` or `-y` | Skip confirmation |
| `--exclude PATTERN` | Skip matching filenames; repeat for more patterns |
| `--config PATH` | Use custom sorting rules |
| `--undo REPORT` | Restore files using a saved run report |

## Sorting and exclusions

Files go into `sorted_files/Pictures`, `Documents`, `Audio`, `Video`, `Archive`, `Code`, or `Unknown` inside your chosen folder.

Only top-level files are sorted. Hidden files, subfolders, symbolic links, and the active config file are skipped. Existing files are never overwritten: a name collision becomes `notes_1.txt` or `backup_1.tar.gz`.

To leave certain files in place:

```bash
python3 organizer.py ~/Downloads --exclude '*.tmp' --exclude 'keep-*' --dry-run
```

Patterns match filenames, ignoring case. Use `*` for any text and `?` for one character. Quote patterns so your shell does not expand them. Patterns cannot include folder paths.

Choose the target folder carefully: project source files are eligible too.

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

Custom rules extend or override individual defaults. Longer extensions, such as `.tar.gz`, match first. Use plain folder names; paths, hidden names, control characters, and Windows reserved names such as `CON` are rejected. The config passed with `--config` stays in place even when it is inside the target folder.

## Run reports and undo

Each confirmed sorting run saves a JSON Lines report in the target folder's hidden `.organizer-reports/` directory. Its path is printed before moving files. Reports record planned paths, completed moves, errors, and file hashes. Dry runs, declined confirmations, and empty plans create no reports.

Preview undo using the printed report path, then apply it:

```bash
python3 organizer.py --undo '/path/to/Downloads/.organizer-reports/RUN.jsonl' --dry-run
python3 organizer.py --undo '/path/to/Downloads/.organizer-reports/RUN.jsonl'
```

Replace `RUN.jsonl` with the actual report filename. You can use `--yes` with undo too. Do not supply a target folder, config, or exclusions with `--undo`.

Undo refuses files whose contents or modification times have changed. It also refuses occupied original paths, including case variants, and symbolic links. Other eligible files can still be restored. Repeating a completed undo leaves already restored files alone. Empty category folders remain.

Keep reports in their original location and do not edit them. They contain filenames and paths, so keep them private if those names are sensitive. Reports are local recovery instructions, not authenticated records. Entries are restricted to the original folder, and unsafe paths, reserved device names, and malformed reports are rejected. A truncated final record requires manual inspection. Reports have a 16 MiB size limit.

## Safety and limits

Keep backups of important files. Undo helps with ordinary sorting mistakes; it does not replace a backup.

- Files are copied before originals are deleted, so extra disk space is needed. Some platform-specific metadata may not be preserved.
- A recovery record is flushed before deleting each original. A report failure stops further moves. If the final status write fails after a move, its earlier recovery record can still be used for undo.
- Failed moves leave the original when possible; if original deletion fails, both copies remain. Incomplete copies are cleaned up when possible. Errors identify leftovers for you to inspect.
- Ctrl+C stops the run; completed moves remain. A forced shutdown or power loss can leave partial files or an incomplete report. Recovery is not an all-or-nothing transaction.
- Avoid editing files or running another organizer on the same folder during a run. Files are not locked; hostile or concurrent filesystem changes are outside its guarantees.

Exit codes: `0` success, preview, or declined confirmation; `1` file, report, or configuration error (including blocked undo files); `2` invalid command; `130` cancellation.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests use temporary folders. They cover sorting, exclusions, reports, undo conflicts, malformed paths, file errors, cancellation, and real command-line subprocesses. GitHub Actions is configured to test Python 3.9 and 3.13 on Linux, macOS, and Windows.

`organizer.py` handles planning, moving, and the CLI. `history.py` writes and validates recovery reports. Both use only the Python standard library.
