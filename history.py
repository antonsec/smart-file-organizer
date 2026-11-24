"""Durable local run reports and strict parsing for undo.

Reports are recovery instructions within one folder, not authenticated records.
A user who can edit that folder can edit its reports too.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import uuid


# Device paths must never be used as ordinary file recovery destinations.
WINDOWS_RESERVED_NAMES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}
REPORT_DIRECTORY = '.organizer-reports'
MAX_REPORT_BYTES = 16 * 1024 * 1024


class ReportError(OSError):
    """Reporting failed; stop rather than continue without recovery records."""


def validate_report_directory(folder):
    directory = folder / REPORT_DIRECTORY
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError(f'Report directory must be a real directory: {directory}')
    return directory


class RunReport:
    def __init__(self, path, stream):
        self.path = path
        self.stream = stream

    @classmethod
    def create(cls, folder, moves):
        folder = folder.resolve()
        directory = validate_report_directory(folder)
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')
                            + uuid.uuid4().hex + '.jsonl')
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        report = cls(path, os.fdopen(descriptor, 'wb'))
        try:
            report.record('run', version=1, folder=str(folder))
            for index, move in enumerate(moves):
                report.record('planned', id=index, source=move.source.name,
                              destination=move.destination.relative_to(folder).as_posix())
            load_report(path)
        except BaseException:
            report.close()
            raise
        return report

    @classmethod
    def append(cls, path):
        # Parsing and path validation must precede opening an existing report.
        load_report(path)
        return cls(path, path.open('ab'))

    def record(self, event, **fields):
        try:
            data = (json.dumps(dict(event=event, **fields), ensure_ascii=True) + '\n').encode('utf-8')
            if self.stream.tell() + len(data) > MAX_REPORT_BYTES:
                raise OSError('Report reached its 16 MiB size limit')
            self.stream.write(data)
            self.stream.flush()
            os.fsync(self.stream.fileno())
        except OSError as error:
            raise ReportError(f'Could not save report {self.path}: {error}. '
                              'Stopped; inspect the report and files before retrying.') from error

    def close(self):
        self.stream.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _component(value):
    return (isinstance(value, str) and bool(value) and value not in {'.', '..'}
            and '\0' not in value and '/' not in value and '\\' not in value
            and not PureWindowsPath(value).drive
            and value.split('.', 1)[0].rstrip(' ').upper() not in WINDOWS_RESERVED_NAMES
            and len(PurePosixPath(value).parts) == 1)


def _fingerprint(value):
    return (isinstance(value, dict) and set(value) == {'size', 'mtime_ns', 'sha256'}
            and type(value['size']) is int and value['size'] >= 0
            and type(value['mtime_ns']) is int
            and isinstance(value['sha256'], str)
            and re.fullmatch('[0-9a-f]{64}', value['sha256']) is not None)


def load_report(path):
    """Validate the whole report before allowing any filesystem changes.

    Relative entries are constrained to top-level originals and category files.
    Reports must stay in the original folder's hidden report directory.
    """
    path = path.expanduser().absolute()
    if path.parent.name != REPORT_DIRECTORY or path.is_symlink() or not path.is_file():
        raise ValueError('Undo requires a regular report inside .organizer-reports/.')
    folder = path.parent.parent.resolve()
    directory = validate_report_directory(folder)
    if path.parent.is_symlink() or path.parent.resolve() != directory:
        raise ValueError('Report directory must not be a symbolic link.')
    with path.open('rb') as stream:
        raw = stream.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('Report is too large to load safely (maximum 16 MiB).')
    # A torn final write is safe to read, but not safe to append to.
    if not raw or not raw.endswith(b'\n'):
        raise ValueError('Report is empty or has an incomplete final record; inspect it manually.')
    try:
        events = [json.loads(line) for line in raw.decode('utf-8').splitlines()]
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValueError(f'Invalid report JSON: {error}') from error
    header = events[0]
    if (not isinstance(header, dict) or header.get('event') != 'run'
            or type(header.get('version')) is not int or header['version'] != 1
            or header.get('folder') != str(folder)):
        raise ValueError('Unsupported report or folder does not match its original location.')
    entries = {}
    sources, destinations = set(), set()
    for event in events[1:]:
        if (not isinstance(event, dict) or type(event.get('id')) is not int
                or not isinstance(event.get('event'), str)):
            raise ValueError('Invalid report record.')
        index, kind = event['id'], event.get('event')
        if kind == 'planned':
            source, destination = event.get('source'), event.get('destination')
            parts = destination.split('/') if isinstance(destination, str) else []
            if (index < 0 or index in entries or not _component(source)
                    or source.startswith('.') or source == 'sorted_files'
                    or len(parts) != 3 or parts[0] != 'sorted_files'
                    or not all(_component(part) for part in parts)
                    or parts[1].startswith('.') or parts[2].startswith('.')
                    or source in sources or destination.casefold() in destinations):
                raise ValueError('Report contains unsafe or duplicate file paths.')
            sources.add(source)
            destinations.add(destination.casefold())
            entries[index] = dict(id=index, source=folder / source,
                                  destination=folder.joinpath(*parts), fingerprint=None,
                                  restored=False)
        elif index not in entries:
            raise ValueError('Report refers to an unknown file.')
        elif kind == 'ready':
            if entries[index]['fingerprint'] is not None or not _fingerprint(event.get('fingerprint')):
                raise ValueError('Invalid or duplicate file fingerprint.')
            entries[index]['fingerprint'] = event['fingerprint']
        elif kind in {'moved', 'restoring', 'restored'}:
            if entries[index]['fingerprint'] is None:
                raise ValueError('Report operation has no recovery fingerprint.')
            if kind == 'restored':
                entries[index]['restored'] = True
        elif kind not in {'failed', 'interrupted'}:
            raise ValueError('Unknown report event.')
    return folder, list(entries.values())
