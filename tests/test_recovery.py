"""Integration and adversarial recovery checks; all files stay in temporary folders."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import organizer as app
from history import MAX_REPORT_BYTES, ReportError, RunReport, load_report


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def file(self, name, content=b'original'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def quiet(self, function, *args, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(*args, **kwargs)

    def organize(self, *args):
        self.assertEqual(self.quiet(app.main, [str(self.root), '--yes', *args]), 0)
        return self.report()

    def report(self):
        return sorted((self.root / '.organizer-reports').glob('*.jsonl'))[-1]

    def events(self, report):
        return [json.loads(line) for line in report.read_text(encoding='utf-8').splitlines()]

    def rewrite(self, report, events):
        report.write_text(''.join(json.dumps(event) + '\n' for event in events), encoding='utf-8')

    def test_exclude_patterns_are_repeatable_and_case_insensitive(self):
        keep = self.file('draft.TMP')
        other = self.file('keep-me.txt')
        photo = self.file('photo.jpg')
        self.organize('--exclude', '*.tmp', '--exclude', 'keep-*.txt')
        self.assertTrue(keep.exists())
        self.assertTrue(other.exists())
        self.assertFalse(photo.exists())

    def test_active_visible_config_is_not_sorted(self):
        config = self.file('rules.json', b'{".txt": "Reading"}')
        self.file('notes.txt')
        self.organize('--config', str(config))
        self.assertEqual(config.read_bytes(), b'{".txt": "Reading"}')
        self.assertTrue((self.root / 'sorted_files/Reading/notes.txt').exists())

    def test_no_reports_for_dry_run_decline_or_excluded_files(self):
        self.file('notes.txt')
        self.quiet(app.main, [str(self.root), '--dry-run'])
        with patch('builtins.input', return_value='n'):
            self.quiet(app.main, [str(self.root)])
        self.quiet(app.main, [str(self.root), '--exclude', '*', '--yes'])
        self.assertEqual([p.name for p in self.root.iterdir()], ['notes.txt'])

    def test_report_records_paths_hashes_and_success(self):
        self.file('notes.txt')
        report = self.organize()
        events = self.events(report)
        self.assertEqual([event['event'] for event in events], ['run', 'planned', 'ready', 'moved'])
        self.assertEqual(events[1]['source'], 'notes.txt')
        self.assertEqual(events[1]['destination'], 'sorted_files/Documents/notes.txt')
        self.assertEqual(events[2]['fingerprint'], app.file_fingerprint(self.root / events[1]['destination']))
        self.assertEqual(load_report(report)[0], self.root)

    def test_undo_round_trip_with_collision_and_repeat(self):
        self.file('backup.tar.gz', b'new')
        existing = self.file('sorted_files/Archive/backup.tar.gz', b'old')
        report = self.organize()
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 0)
        self.assertEqual((self.root / 'backup.tar.gz').read_bytes(), b'new')
        self.assertEqual(existing.read_bytes(), b'old')
        self.assertFalse((existing.parent / 'backup_1.tar.gz').exists())
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 0)
        self.assertEqual(sum(event['event'] == 'restored' for event in self.events(report)), 1)

    def test_undo_preview_and_decline_are_read_only(self):
        self.file('notes.txt')
        report = self.organize()
        before = report.read_bytes()
        self.assertEqual(self.quiet(app.undo_report, report, dry_run=True), 0)
        with patch('builtins.input', return_value=''):
            self.assertEqual(self.quiet(app.undo_report, report), 0)
        self.assertEqual(report.read_bytes(), before)
        self.assertFalse((self.root / 'notes.txt').exists())

    def test_undo_refuses_modified_content_even_with_original_size_and_time(self):
        self.file('notes.txt', b'aaaa')
        report = self.organize()
        destination = self.root / 'sorted_files/Documents/notes.txt'
        stamp = destination.stat().st_mtime_ns
        destination.write_bytes(b'bbbb')
        os.utime(destination, ns=(stamp, stamp))
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual(destination.read_bytes(), b'bbbb')
        self.assertFalse((self.root / 'notes.txt').exists())

    def test_undo_refuses_changed_modification_time(self):
        self.file('notes.txt')
        report = self.organize()
        destination = self.root / 'sorted_files/Documents/notes.txt'
        stamp = destination.stat().st_mtime_ns + 2_000_000_000
        os.utime(destination, ns=(stamp, stamp))
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertTrue(destination.exists())

    def test_undo_never_overwrites_original_or_case_variant(self):
        self.file('notes.txt')
        report = self.organize()
        occupant = self.file('NOTES.TXT', b'new work')
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual(occupant.read_bytes(), b'new work')
        self.assertTrue((self.root / 'sorted_files/Documents/notes.txt').exists())

    def test_undo_continues_past_a_conflict(self):
        self.file('a.txt')
        self.file('b.txt')
        report = self.organize()
        self.file('a.txt', b'occupied')
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual((self.root / 'a.txt').read_bytes(), b'occupied')
        self.assertEqual((self.root / 'b.txt').read_bytes(), b'original')
        self.assertTrue((self.root / 'sorted_files/Documents/a.txt').exists())

    def test_undo_refuses_missing_file(self):
        self.file('notes.txt')
        report = self.organize()
        (self.root / 'sorted_files/Documents/notes.txt').unlink()
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)

    def test_report_failure_before_source_deletion_keeps_source(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with RunReport.create(self.root, moves) as report:
            real_record = report.record
            def record(event, **fields):
                if event == 'ready':
                    raise ReportError('disk full')
                real_record(event, **fields)
            with patch.object(report, 'record', side_effect=record):
                with self.assertRaises(ReportError):
                    self.quiet(app.execute_plan, moves, report)
        self.assertEqual(source.read_bytes(), b'original')
        self.assertFalse(moves[0].destination.exists())

    def test_report_failure_after_move_still_allows_recovery(self):
        self.file('a.txt')
        second = self.file('b.txt')
        moves = app.plan_moves(self.root)
        with RunReport.create(self.root, moves) as report:
            real_record = report.record
            def record(event, **fields):
                if event == 'moved':
                    raise ReportError('report unavailable')
                real_record(event, **fields)
            with patch.object(report, 'record', side_effect=record):
                with self.assertRaises(ReportError):
                    self.quiet(app.execute_plan, moves, report)
            path = report.path
        self.assertTrue(second.exists())
        self.assertFalse(moves[0].source.exists())
        self.assertEqual(self.quiet(app.undo_report, path, yes=True), 0)
        self.assertEqual(moves[0].source.read_bytes(), b'original')

    def test_copy_failure_is_reported_and_not_undoable(self):
        self.file('a.txt')
        self.file('b.txt')
        moves = app.plan_moves(self.root)
        real_copy = app.shutil.copyfileobj
        def copy(src, dst):
            if Path(src.name).name == 'a.txt':
                raise OSError('copy failed')
            real_copy(src, dst)
        with RunReport.create(self.root, moves) as report:
            with patch('organizer.shutil.copyfileobj', side_effect=copy):
                result = self.quiet(app.execute_plan, moves, report)
            path = report.path
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(any(event['event'] == 'failed' for event in self.events(path)))
        self.assertEqual(self.quiet(app.undo_report, path, yes=True), 0)
        self.assertTrue((self.root / 'a.txt').exists())
        self.assertTrue((self.root / 'b.txt').exists())

    def test_source_delete_failure_retains_copies_and_blocks_undo(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with RunReport.create(self.root, moves) as report:
            with patch.object(Path, 'unlink', side_effect=PermissionError('denied')):
                result = self.quiet(app.execute_plan, moves, report)
            path = report.path
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(self.quiet(app.undo_report, path, yes=True), 1)
        self.assertEqual(source.read_bytes(), moves[0].destination.read_bytes())

    def test_interrupted_copy_leaves_report_and_stops_later_moves(self):
        self.file('a.txt')
        second = self.file('b.txt')
        with patch('organizer.shutil.copyfileobj', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.quiet(app.main, [str(self.root), '--yes'])
        self.assertTrue(second.exists())
        events = self.events(self.report())
        self.assertEqual(events[-1]['event'], 'interrupted')
        self.assertFalse(any(event['event'] == 'ready' for event in events))

    def test_unsafe_report_paths_rejected_before_any_restore(self):
        self.file('notes.txt')
        report = self.organize()
        events = self.events(report)
        for field, value in [('source', '../outside.txt'), ('source', '/absolute.txt'),
                             ('source', 'C:outside.txt'), ('source', 'NUL.txt'),
                             ('destination', 'sorted_files/Docs/CON'), ('source', '..\\outside.txt'),
                             ('destination', 'sorted_files/../outside.txt'),
                             ('destination', 'sorted_files/Docs/../../outside.txt'),
                             ('destination', '/tmp/outside.txt')]:
            edited = [dict(event) for event in events]
            edited[1][field] = value
            self.rewrite(report, edited)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.quiet(app.undo_report, report, yes=True)
        self.assertFalse((self.root / 'notes.txt').exists())
        self.assertTrue((self.root / 'sorted_files/Documents/notes.txt').exists())

    def test_report_schema_and_hashes_validated(self):
        self.file('notes.txt')
        report = self.organize()
        events = self.events(report)
        bad_cases = []
        for field, value in [('version', 2), ('folder', str(self.root.parent)), ('version', True)]:
            edited = json.loads(json.dumps(events))
            edited[0][field] = value
            bad_cases.append(edited)
        for fingerprint in [{}, {'size': -1, 'mtime_ns': 1, 'sha256': 'a' * 64},
                            {'size': 1, 'mtime_ns': 1, 'sha256': 'invalid'}]:
            edited = json.loads(json.dumps(events))
            edited[2]['fingerprint'] = fingerprint
            bad_cases.append(edited)
        bad_cases.append(events + [dict(events[1])])
        bad_cases.append(events + [{'event': 'restored', 'id': 999}])
        for edited in bad_cases:
            self.rewrite(report, edited)
            with self.subTest(events=edited), self.assertRaises(ValueError):
                load_report(report)

    def test_truncated_or_oversized_reports_are_refused(self):
        self.file('notes.txt')
        report = self.organize()
        original = report.read_bytes()
        report.write_bytes(original + b'{"event":')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            load_report(report)
        report.write_bytes(b' ' * (MAX_REPORT_BYTES + 1))
        with self.assertRaisesRegex(ValueError, 'too large'):
            load_report(report)

    def test_malformed_event_type_rejected_cleanly(self):
        self.file('notes.txt')
        report = self.organize()
        events = self.events(report)
        events.append({'event': [], 'id': 0})
        self.rewrite(report, events)
        with self.assertRaises(ValueError):
            load_report(report)

    def test_case_sensitive_source_names_can_be_organized(self):
        self.file('a.txt', b'lower')
        try:
            with (self.root / 'A.txt').open('xb') as stream:
                stream.write(b'upper')
        except FileExistsError:
            self.skipTest('Filesystem does not support case-distinct names')
        report = self.organize()
        folder, entries = load_report(report)
        self.assertEqual({entry['source'].name for entry in entries}, {'a.txt', 'A.txt'})
        self.assertEqual({entry['destination'].read_bytes() for entry in entries}, {b'lower', b'upper'})

    def test_report_write_fsync_failure_moves_nothing(self):
        source = self.file('notes.txt')
        with patch('history.os.fsync', side_effect=OSError('sync failed')):
            with self.assertRaises(ReportError):
                self.quiet(app.main, [str(self.root), '--yes'])
        self.assertEqual(source.read_bytes(), b'original')
        self.assertFalse((self.root / 'sorted_files').exists())

    def test_undo_report_failure_before_delete_keeps_sorted_copy(self):
        self.file('notes.txt')
        report = self.organize()
        real_record = RunReport.record
        def record(instance, event, **fields):
            if event == 'restoring':
                raise ReportError('report unavailable')
            real_record(instance, event, **fields)
        with patch.object(RunReport, 'record', new=record):
            with self.assertRaises(ReportError):
                self.quiet(app.undo_report, report, yes=True)
        self.assertFalse((self.root / 'notes.txt').exists())
        self.assertEqual((self.root / 'sorted_files/Documents/notes.txt').read_bytes(), b'original')

    def test_report_failure_and_cleanup_failure_stop_later_files(self):
        self.file('a.txt')
        self.file('b.txt')
        moves = app.plan_moves(self.root)
        with RunReport.create(self.root, moves) as report:
            with patch.object(report, 'record', side_effect=ReportError('report unavailable')), \
                    patch.object(Path, 'unlink', side_effect=PermissionError('cleanup denied')):
                with self.assertRaises(ReportError):
                    self.quiet(app.execute_plan, moves, report)
        self.assertTrue(moves[0].source.exists())
        self.assertTrue(moves[0].destination.exists())
        self.assertTrue(moves[1].source.exists())
        self.assertFalse(moves[1].destination.exists())

    def test_report_outside_history_directory_rejected(self):
        self.file('notes.txt')
        report = self.organize()
        copied = self.file('report.jsonl', report.read_bytes())
        with self.assertRaises(ValueError):
            load_report(copied)

    def test_undo_rechecks_changes_after_confirmation(self):
        self.file('notes.txt')
        report = self.organize()
        destination = self.root / 'sorted_files/Documents/notes.txt'
        def confirm(prompt):
            destination.write_bytes(b'edited during confirmation')
            return 'y'
        with patch('builtins.input', side_effect=confirm):
            self.assertEqual(self.quiet(app.undo_report, report), 1)
        self.assertEqual(destination.read_bytes(), b'edited during confirmation')

    def test_exclusive_restore_refuses_target_appearing_during_copy(self):
        self.file('notes.txt')
        report = self.organize()
        original = self.root / 'notes.txt'
        real_move = app.move_exclusive
        def move(source, destination, **kwargs):
            original.write_bytes(b'new work')
            real_move(source, destination, **kwargs)
        with patch('organizer.move_exclusive', side_effect=move):
            self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual(original.read_bytes(), b'new work')
        self.assertTrue((self.root / 'sorted_files/Documents/notes.txt').exists())

    def test_restore_copy_must_match_record_before_sorted_file_deleted(self):
        self.file('notes.txt')
        report = self.organize()
        destination = self.root / 'sorted_files/Documents/notes.txt'
        def wrong_copy(src, dst):
            dst.write(b'wrong content')
        with patch('organizer.shutil.copyfileobj', side_effect=wrong_copy):
            self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual(destination.read_bytes(), b'original')
        self.assertFalse((self.root / 'notes.txt').exists())

    def test_symlinked_category_blocks_restore(self):
        self.file('notes.txt')
        report = self.organize()
        category = self.root / 'sorted_files/Documents'
        actual = self.root / 'moved-category'
        category.rename(actual)
        category.symlink_to(actual, target_is_directory=True)
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertTrue((actual / 'notes.txt').exists())

    def test_symlinked_original_and_sorted_file_are_refused(self):
        self.file('notes.txt')
        report = self.organize()
        outside = self.file('outside', b'keep')
        original = self.root / 'notes.txt'
        original.symlink_to(outside)
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        original.unlink()
        destination = self.root / 'sorted_files/Documents/notes.txt'
        destination.unlink()
        destination.symlink_to(outside)
        self.assertEqual(self.quiet(app.undo_report, report, yes=True), 1)
        self.assertEqual(outside.read_bytes(), b'keep')

    def test_symlinked_report_and_report_directory_rejected(self):
        self.file('notes.txt')
        report = self.organize()
        alias = report.parent / 'alias.jsonl'
        alias.symlink_to(report)
        with self.assertRaises(ValueError):
            load_report(alias)
        actual = self.root / 'real-reports'
        report.parent.rename(actual)
        (self.root / '.organizer-reports').symlink_to(actual, target_is_directory=True)
        with self.assertRaises(ValueError):
            load_report(report)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='organizer CLI ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.script = Path(app.__file__).resolve()

    def run_cli(self, *args, input=''):
        return subprocess.run([sys.executable, str(self.script), *map(str, args)], input=input,
                              capture_output=True, text=True, encoding='utf-8', timeout=20,
                              cwd=self.root, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                                                     PYTHONIOENCODING='utf-8'))

    def test_help_and_bad_arguments(self):
        self.assertEqual(self.run_cli('--help').returncode, 0)
        self.assertIn('--undo', self.run_cli('--help').stdout)
        self.assertEqual(self.run_cli('--unknown').returncode, 2)
        self.assertEqual(self.run_cli('--undo', 'run.jsonl', self.root).returncode, 2)
        self.assertEqual(self.run_cli(self.root, '--exclude', '../*').returncode, 2)

    def test_dry_run_with_redirected_io_and_unicode_filename(self):
        source = self.root / 'café.txt'
        source.write_bytes(b'data')
        result = self.run_cli(self.root, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('café.txt', result.stdout)
        self.assertTrue(source.exists())
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_invalid_json_and_missing_folder_exit_cleanly(self):
        config = self.root / 'rules.json'
        config.write_text('{bad json', encoding='utf-8')
        for args in [(self.root, '--config', config, '--yes'), (self.root / 'missing', '--yes')]:
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 1)
            self.assertIn('ERROR:', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_eof_and_confirmation(self):
        source = self.root / 'notes.txt'
        source.write_bytes(b'data')
        self.assertEqual(self.run_cli(self.root).returncode, 130)
        self.assertEqual(self.run_cli().returncode, 130)
        self.assertEqual(self.run_cli(self.root, input='n\n').returncode, 0)
        self.assertTrue(source.exists())
        self.assertFalse((self.root / '.organizer-reports').exists())

    def test_cli_sort_report_preview_and_undo_round_trip(self):
        source = self.root / 'notes.txt'
        source.write_bytes(b'data')
        result = self.run_cli(self.root, '--yes')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Run report:', result.stdout)
        report = next((self.root / '.organizer-reports').glob('*.jsonl'))
        preview = self.run_cli('--undo', report, '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(source.exists())
        restored = self.run_cli('--undo', report, '--yes')
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertEqual(source.read_bytes(), b'data')

    def test_cli_undo_conflict_and_malformed_report_exit_one(self):
        source = self.root / 'notes.txt'
        source.write_bytes(b'data')
        self.assertEqual(self.run_cli(self.root, '--yes').returncode, 0)
        report = next((self.root / '.organizer-reports').glob('*.jsonl'))
        source.write_bytes(b'new work')
        result = self.run_cli('--undo', report, '--yes')
        self.assertEqual(result.returncode, 1)
        self.assertIn('occupied', result.stderr)
        report.write_text('not JSON\n', encoding='utf-8')
        result = self.run_cli('--undo', report, '--yes')
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
