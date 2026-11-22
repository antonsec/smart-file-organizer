#!/usr/bin/env python3
"""Sort a folder by extension, with previews and exclusive destination creation."""

import argparse
from collections import Counter
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Dict, List, Optional


CATEGORIES = {
    "Pictures": "jpg jpeg png gif bmp webp svg tiff tif heic heif ico raw cr2 nef",
    "Documents": "pdf txt rtf doc docx odt xls xlsx ods ppt pptx odp csv md markdown epub mobi",
    "Audio": "mp3 wav flac aac ogg m4a wma aiff opus",
    "Video": "mp4 mkv avi mov wmv flv webm m4v mpeg mpg 3gp",
    "Archive": "zip rar 7z tar gz bz2 xz tgz tar.gz tar.bz2 tar.xz",
    "Code": "py js ts jsx tsx html css scss java c cpp h hpp cs go rs php rb sh bash json xml yaml yml toml ini cfg",
}
FILE_TYPES = {"." + ext: category for category, extensions in CATEGORIES.items()
              for ext in extensions.split()}

# Windows also reserves device names when followed by an extension.
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}


def has_control_characters(value: str) -> bool:
    return any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value)


@dataclass(frozen=True)
class Move:
    source: Path
    destination: Path
    category: str


@dataclass
class Result:
    counts: Counter = field(default_factory=Counter)
    errors: List[str] = field(default_factory=list)


def load_rules(path: Optional[Path] = None) -> Dict[str, str]:
    """Merge a JSON extension-to-category mapping into the built-in rules."""
    rules = dict(FILE_TYPES)
    if path is None:
        return rules
    custom = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(custom, dict):
        raise ValueError("Config must be a JSON object mapping extensions to categories.")
    for extension, category in custom.items():
        if (not isinstance(extension, str) or not extension.startswith(".")
                or len(extension) < 2 or has_control_characters(extension)
                or any(c in extension for c in "/\\\0")):
            raise ValueError("Each extension must start with a dot and contain no path separators or control characters.")
        if (not isinstance(category, str) or not category.strip()
                or category.startswith(".") or category != category.strip()
                or has_control_characters(category)
                or category.split(".", 1)[0].rstrip(" ").upper() in WINDOWS_RESERVED_NAMES
                or any(c in category for c in '/\\\0<>:"|?*') or category.endswith(".")):
            raise ValueError("Categories must be plain, non-hidden folder names without control characters or Windows reserved device names.")
        rules[extension.lower()] = category
    return rules


def matched_extension(path: Path, rules: Dict[str, str]) -> str:
    name = path.name.lower()
    return next((ext for ext in sorted(rules, key=len, reverse=True)
                 if name.endswith(ext)), "")


def unique_destination(destination: Path, reserved=None, extension: str = "") -> Path:
    """Reserve names case-insensitively for consistent macOS/Windows previews."""
    reserved = reserved if reserved is not None else set()
    suffix = destination.name[-len(extension):] if extension else destination.suffix
    stem = destination.name[:-len(suffix)] if suffix else destination.name
    existing = {p.name.casefold() for p in destination.parent.iterdir()} if destination.parent.is_dir() else set()
    candidate = destination
    counter = 1
    while (os.path.lexists(candidate) or candidate.name.casefold() in existing
           or str(candidate).casefold() in reserved):
        candidate = destination.with_name(f"{stem}_{counter}{suffix}")
        counter += 1
    reserved.add(str(candidate).casefold())
    return candidate


def validate_directory(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Output directory must not be a symbolic link: {path}")
    if path.exists() and not path.is_dir():
        raise ValueError(f"Output path is not a directory: {path}")


def plan_moves(folder: Path, rules=None) -> List[Move]:
    """Build a deterministic plan without creating any files or directories."""
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"Folder does not exist or is not a directory: {folder}")
    rules = FILE_TYPES if rules is None else rules
    output = folder / "sorted_files"
    validate_directory(output)
    reserved = set()
    moves = []
    for source in sorted(folder.iterdir(), key=lambda p: (p.name.casefold(), p.name)):
        if source.name.startswith(".") or source.is_symlink() or not source.is_file():
            continue
        extension = matched_extension(source, rules)
        category = rules.get(extension, "Unknown")
        category_dir = output / category
        validate_directory(category_dir)
        destination = unique_destination(category_dir / source.name, reserved, extension)
        moves.append(Move(source, destination, category))
    return moves


def move_exclusive(source: Path, destination: Path) -> None:
    """Copy to a new file, then remove the source; never overwrite a target.

    Uses more disk space than rename, but works across filesystems. If deletion
    fails, retain both copies and report the error rather than risk data loss.
    """
    if source.is_symlink() or not source.is_file():
        raise OSError(f"Source is no longer a regular file: {source}")
    created = False
    try:
        with source.open("rb") as src:
            with destination.open("xb") as dst:
                created = True
                shutil.copyfileobj(src, dst)
                dst.flush()
                os.fsync(dst.fileno())
        shutil.copystat(source, destination)
    except BaseException as error:
        if created:
            try:
                destination.unlink(missing_ok=True)
            except OSError as cleanup_error:
                message = (
                    f"Could not remove incomplete destination '{destination}': {cleanup_error}. "
                    "Source retained; inspect the destination before retrying."
                )
                if isinstance(error, Exception):
                    raise OSError(f"{error}. {message}") from error
                # A cleanup failure must never turn cancellation into a file error.
                print(f"WARNING: {message}", file=sys.stderr)
        raise
    try:
        source.unlink()
    except OSError as error:
        raise OSError(
            f"Copy completed at '{destination}', but could not remove source '{source}': "
            f"{error}. Both copies retained."
        ) from error


def execute_plan(moves: List[Move]) -> Result:
    result = Result()
    for move in moves:
        try:
            validate_directory(move.destination.parent.parent)
            validate_directory(move.destination.parent)
            move.destination.parent.mkdir(parents=True, exist_ok=True)
            move_exclusive(move.source, move.destination)
        except (OSError, ValueError) as error:
            message = f"{move.source.name}: {error}"
            result.errors.append(message)
            print(f"ERROR: {message}", file=sys.stderr)
        else:
            result.counts[move.category] += 1
            print(f"Moved: {move.source.name} -> {move.destination.relative_to(move.source.parent)}")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sort files by extension into sorted_files/.")
    parser.add_argument("folder", nargs="?", help="Folder to organize (prompts if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing anything")
    parser.add_argument("--yes", "-y", action="store_true", help="Apply without the confirmation prompt")
    parser.add_argument("--config", type=Path, help="JSON extension-to-category overrides")
    args = parser.parse_args(argv)
    print("Smart File Organizer\n" + "-" * 30)
    raw = args.folder if args.folder is not None else input("Folder to organize: ").strip()
    if not raw.strip():
        raise ValueError("No folder provided.")
    rules = load_rules(args.config)
    moves = plan_moves(Path(raw), rules)
    if not moves:
        print("No eligible files found. Hidden files, symbolic links and folders are skipped.")
        return 0
    for move in moves:
        print(f"Preview: {move.source.name} -> {move.destination.relative_to(move.source.parent)}")
    print(f"\nPlanned: {len(moves)} file(s).")
    if args.dry_run:
        print("Dry run: no files or folders changed.")
        return 0
    if not args.yes and input("Move these files? [y/N]: ").strip().lower() not in {"y", "yes"}:
        print("Cancelled. No files moved.")
        return 0
    result = execute_plan(moves)
    print("\nSummary\n" + "-" * 30)
    for category, count in sorted(result.counts.items()):
        print(f"{category:<12}: {count}")
    print(f"Moved {sum(result.counts.values())} file(s); failed {len(result.errors)}.")
    return 1 if result.errors else 0


def cli() -> int:
    try:
        return main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Any completed moves remain in place.", file=sys.stderr)
        return 130
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(cli())
