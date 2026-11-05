import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import organizer as app


class OrganizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, content=b'test content'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def run_quiet(self, function, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(*args)

    def test_preview_does_not_write(self):
        source = self.file('photo.JPG')
        moves = app.plan_moves(self.root)
        self.assertEqual(moves[0].category, 'Pictures')
        self.assertTrue(source.exists())
        self.assertFalse((self.root / 'sorted_files').exists())

    def test_successful_move_preserves_content(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        result = self.run_quiet(app.execute_plan, moves)
        self.assertEqual(result.counts, {'Documents': 1})
        self.assertFalse(source.exists())
        self.assertEqual(moves[0].destination.read_bytes(), b'test content')

    def test_hidden_and_directories_skipped(self):
        self.file('.hidden.txt')
        self.file('nested/photo.jpg')
        self.assertEqual(app.plan_moves(self.root), [])

    def test_symlink_source_skipped(self):
        source = self.file('.target')
        (self.root / 'link.txt').symlink_to(source)
        self.assertEqual(app.plan_moves(self.root), [])

    def test_output_symlink_rejected(self):
        (self.root / 'sorted_files').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            app.plan_moves(self.root)

    def test_category_symlink_rejected(self):
        self.file('notes.txt')
        (self.root / 'sorted_files').mkdir()
        (self.root / 'sorted_files/Documents').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            app.plan_moves(self.root)

    def test_collision_preserves_compound_extension(self):
        self.file('backup.tar.gz')
        self.file('sorted_files/Archive/backup.tar.gz')
        self.assertEqual(app.plan_moves(self.root)[0].destination.name, 'backup_1.tar.gz')

    def test_case_insensitive_existing_collision(self):
        self.file('notes.txt')
        self.file('sorted_files/Documents/NOTES.TXT')
        self.assertEqual(app.plan_moves(self.root)[0].destination.name, 'notes_1.txt')

    def test_dangling_symlink_is_collision(self):
        self.file('notes.txt')
        target = self.root / 'sorted_files/Documents'
        target.mkdir(parents=True)
        (target / 'notes.txt').symlink_to(self.root / 'missing')
        self.assertEqual(app.plan_moves(self.root)[0].destination.name, 'notes_1.txt')

    def test_new_target_after_preview_not_overwritten(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        self.file('sorted_files/Documents/notes.txt', b'keep me')
        result = self.run_quiet(app.execute_plan, moves)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(sum(result.counts.values()), 0)
        self.assertTrue(source.exists())
        self.assertEqual(moves[0].destination.read_bytes(), b'keep me')

    def test_copy_failure_removes_partial_destination(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with patch('organizer.shutil.copyfileobj', side_effect=OSError('disk full')):
            result = self.run_quiet(app.execute_plan, moves)
        self.assertEqual(len(result.errors), 1)
        self.assertTrue(source.exists())
        self.assertFalse(moves[0].destination.exists())

    def test_mkdir_failure_reported(self):
        self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with patch.object(Path, 'mkdir', side_effect=PermissionError('denied')):
            result = self.run_quiet(app.execute_plan, moves)
        self.assertEqual(len(result.errors), 1)
        self.assertFalse(result.counts)

    def test_source_delete_failure_keeps_both_copies(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with patch.object(Path, 'unlink', side_effect=PermissionError('denied')):
            result = self.run_quiet(app.execute_plan, moves)
        self.assertTrue(source.exists())
        self.assertEqual(moves[0].destination.read_bytes(), source.read_bytes())
        self.assertEqual(len(result.errors), 1)
        self.assertFalse(result.counts)

    def test_interrupted_copy_cleans_partial_destination(self):
        source = self.file('notes.txt')
        moves = app.plan_moves(self.root)
        with patch('organizer.shutil.copyfileobj', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                app.execute_plan(moves)
        self.assertTrue(source.exists())
        self.assertFalse(moves[0].destination.exists())

    def test_planned_collisions_are_reserved(self):
        destination = self.root / 'photo.jpg'
        reserved = set()
        self.assertEqual(app.unique_destination(destination, reserved).name, 'photo.jpg')
        self.assertEqual(app.unique_destination(destination, reserved).name, 'photo_1.jpg')

    def test_custom_rules_and_defaults(self):
        config = self.file('.rules.json', json.dumps({'.blend': 'Design', '.PDF': 'Reading'}).encode())
        rules = app.load_rules(config)
        self.assertEqual(rules['.blend'], 'Design')
        self.assertEqual(rules['.pdf'], 'Reading')
        self.assertEqual(rules['.jpg'], 'Pictures')

    def test_invalid_configs_rejected(self):
        for value in [[], {'.txt': '../escape'}, {'.txt': '/tmp'}, {'txt': 'Docs'}, {'.txt': 1}, {'.txt': '.hidden'}]:
            config = self.file('.config.json', json.dumps(value).encode())
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.load_rules(config)

    def test_unknown_extension(self):
        self.file('LICENSE')
        self.assertEqual(app.plan_moves(self.root)[0].category, 'Unknown')

    def test_confirmation_defaults_to_cancel(self):
        source = self.file('notes.txt')
        with patch('builtins.input', return_value=''):
            code = self.run_quiet(app.main, [str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue(source.exists())
        self.assertFalse((self.root / 'sorted_files').exists())

    def test_dry_run_never_prompts(self):
        self.file('notes.txt')
        with patch('builtins.input', side_effect=AssertionError('unexpected prompt')):
            self.assertEqual(self.run_quiet(app.main, [str(self.root), '--dry-run']), 0)
        self.assertFalse((self.root / 'sorted_files').exists())

    def test_keyboard_interrupt_exit(self):
        with patch('organizer.main', side_effect=KeyboardInterrupt):
            self.assertEqual(self.run_quiet(app.cli), 130)

    def test_missing_folder(self):
        with self.assertRaises(ValueError):
            app.plan_moves(self.root / 'missing')

    def test_empty_folder_creates_nothing(self):
        self.assertEqual(self.run_quiet(app.main, [str(self.root), '--yes']), 0)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_yes_applies_without_prompt(self):
        source = self.file('notes.txt')
        with patch('builtins.input', side_effect=AssertionError('unexpected prompt')):
            self.assertEqual(self.run_quiet(app.main, [str(self.root), '--yes']), 0)
        self.assertFalse(source.exists())


if __name__ == '__main__':
    unittest.main()
