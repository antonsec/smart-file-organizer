#!/usr/bin/env python3
"""
Smart File Organizer
--------------------
Automatically sorts files into category folders based on extension.

Features:
- Interactive or command-line usage
- Dry-run mode (--dry-run)
- Skips hidden/system files (names starting with .)
- Handles filename collisions safely
- Wide range of common file types
- Clean, readable summary
"""

from pathlib import Path
import shutil
import argparse
import sys
from collections import defaultdict
from typing import Dict


# ─────────────────────────────────────────────────────────────
# Extension → Category mapping
# ─────────────────────────────────────────────────────────────
FILE_TYPES: Dict[str, str] = {
    # Pictures
    ".jpg": "Pictures", ".jpeg": "Pictures", ".png": "Pictures",
    ".gif": "Pictures", ".bmp": "Pictures", ".webp": "Pictures",
    ".svg": "Pictures", ".tiff": "Pictures", ".tif": "Pictures",
    ".heic": "Pictures", ".heif": "Pictures", ".ico": "Pictures",
    ".raw": "Pictures", ".cr2": "Pictures", ".nef": "Pictures",

    # Documents
    ".pdf": "Documents", ".txt": "Documents", ".rtf": "Documents",
    ".doc": "Documents", ".docx": "Documents", ".odt": "Documents",
    ".xls": "Documents", ".xlsx": "Documents", ".ods": "Documents",
    ".ppt": "Documents", ".pptx": "Documents", ".odp": "Documents",
    ".csv": "Documents", ".md": "Documents", ".markdown": "Documents",
    ".epub": "Documents", ".mobi": "Documents",

    # Audio
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
    ".aac": "Audio", ".ogg": "Audio", ".m4a": "Audio",
    ".wma": "Audio", ".aiff": "Audio", ".opus": "Audio",

    # Video
    ".mp4": "Video", ".mkv": "Video", ".avi": "Video",
    ".mov": "Video", ".wmv": "Video", ".flv": "Video",
    ".webm": "Video", ".m4v": "Video", ".mpeg": "Video",
    ".mpg": "Video", ".3gp": "Video",

    # Archives
    ".zip": "Archive", ".rar": "Archive", ".7z": "Archive",
    ".tar": "Archive", ".gz": "Archive", ".bz2": "Archive",
    ".xz": "Archive", ".tgz": "Archive",

    # Code / Scripts / Data
    ".py": "Code", ".js": "Code", ".ts": "Code", ".jsx": "Code",
    ".tsx": "Code", ".html": "Code", ".css": "Code", ".scss": "Code",
    ".java": "Code", ".c": "Code", ".cpp": "Code", ".h": "Code",
    ".hpp": "Code", ".cs": "Code", ".go": "Code", ".rs": "Code",
    ".php": "Code", ".rb": "Code", ".sh": "Code", ".bash": "Code",
    ".json": "Code", ".xml": "Code", ".yaml": "Code", ".yml": "Code",
    ".toml": "Code", ".ini": "Code", ".cfg": "Code",
}


def unique_destination(destination: Path) -> Path:
    """If the target already exists, return a unique name with _1, _2, etc."""
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    parent = destination.parent
    counter = 1

    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def organize(folder: Path, dry_run: bool = False) -> None:
    """Move files from `folder` into category subfolders inside sorted_files/."""
    if not folder.exists():
        print(f"❌ Folder does not exist: {folder}")
        sys.exit(1)
    if not folder.is_dir():
        print(f"❌ Not a folder: {folder}")
        sys.exit(1)

    sorted_dir = folder / "sorted_files"
    if not dry_run:
        sorted_dir.mkdir(exist_ok=True)

    counts: Dict[str, int] = defaultdict(int)
    moved = 0

    print(f"\nScanning: {folder}")
    if dry_run:
        print("🔍 DRY-RUN mode – no files will be moved\n")
    else:
        print()

    for item in folder.iterdir():
        # Skip directories + hidden/system files (.DS_Store, .localized, etc.)
        if not item.is_file() or item.name.startswith("."):
            continue

        category = FILE_TYPES.get(item.suffix.lower(), "Unknown")
        counts[category] += 1

        if dry_run:
            print(f"→ would move  {item.name}  →  {category}/")
            continue

        category_dir = sorted_dir / category
        category_dir.mkdir(exist_ok=True)

        destination = unique_destination(category_dir / item.name)

        try:
            shutil.move(str(item), str(destination))
            print(f"✅ {item.name} → {category}/")
            moved += 1
        except PermissionError:
            print(f"❌ Permission denied: {item.name}")
        except Exception as e:
            print(f"❌ Failed to move {item.name}: {e}")

    # Summary
    print("\nSummary")
    print("-" * 30)
    if not counts:
        print("No files found to organize.")
    else:
        for category, amount in sorted(counts.items()):
            print(f"{category:<12}: {amount}")
        if not dry_run:
            print(f"\nMoved {moved} file(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smart File Organizer – sort files by extension"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder to organize (prompts if omitted)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without actually moving files",
    )
    args = parser.parse_args()

    print("📂 Smart File Organizer")
    print("-" * 30)

    if args.folder:
        target = Path(args.folder).expanduser().resolve()
    else:
        user_input = input("Enter the folder you want to organize: ").strip()
        if not user_input:
            print("❌ No folder provided.")
            sys.exit(1)
        target = Path(user_input).expanduser().resolve()

    organize(target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()