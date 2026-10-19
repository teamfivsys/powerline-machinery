from pathlib import Path
import os
import sqlite3
import tempfile
from unittest import TestCase
from scripts.sqlite_snapshot import REQUIRED, snapshot

class SnapshotTests(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='powerline-snapshot-tests-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); os.chmod(self.root,0o700)
        self.source=self.root/'source.sqlite3'
        with sqlite3.connect(self.source) as conn:
            for t in REQUIRED: conn.execute(f'CREATE TABLE "{t}" (id INTEGER PRIMARY KEY, value TEXT)')
            conn.execute("INSERT INTO operations_employee(value) VALUES ('fictional')")
    def test_backup_restore_integrity_and_private_mode(self):
        result=snapshot(self.source,self.root/'backup.sqlite3')
        self.assertEqual(result['mode'],'0o600'); self.assertEqual(result['integrity'],'ok')
        restored=snapshot(self.root/'backup.sqlite3',self.root/'restored.sqlite3')
        self.assertEqual(result['table_counts'],restored['table_counts'])
    def test_refuses_overwrite(self):
        dest=self.root/'exists'; dest.write_text('keep unchanged')
        with self.assertRaises(FileExistsError): snapshot(self.source,dest)
        self.assertEqual(dest.read_text(),'keep unchanged')
    def test_refuses_symlink_destination(self):
        target=self.root/'keep'; target.write_text('keep unchanged'); link=self.root/'link'; link.symlink_to(target)
        with self.assertRaises(FileExistsError): snapshot(self.source,link)
        self.assertEqual(target.read_text(),'keep unchanged')
    def test_refuses_public_directory(self):
        public=self.root/'public'; public.mkdir(mode=0o755)
        with self.assertRaisesRegex(ValueError,'private'): snapshot(self.source,public/'backup')
    def test_rejects_non_powerline_database_and_cleans_partial(self):
        bad=self.root/'bad';sqlite3.connect(bad).close();dest=self.root/'dest'
        with self.assertRaisesRegex(ValueError,'required tables'): snapshot(bad,dest)
        self.assertFalse(dest.exists())
    def test_no_uncommitted_values_leak_into_snapshot(self):
        writer=sqlite3.connect(self.source)
        writer.execute("INSERT INTO operations_employee(value) VALUES ('uncommitted')")
        try:
            result=snapshot(self.source,self.root/'consistent.sqlite3')
            self.assertEqual(result['table_counts']['operations_employee'],1)
        finally: writer.rollback(); writer.close()
    def test_refuses_source_as_destination(self):
        with self.assertRaisesRegex(ValueError,'differ'): snapshot(self.source,self.source)

    def test_live_location_samples_not_kept_in_snapshot(self):
        with sqlite3.connect(self.source) as c:
            c.execute("CREATE TABLE operations_locationshare (id INTEGER PRIMARY KEY, value TEXT)")
            c.execute("INSERT INTO operations_locationshare(value) VALUES ('fictional-sensitive-location')")
        result=snapshot(self.source,self.root/'location-free.sqlite3')
        self.assertEqual(result['table_counts']['operations_locationshare'],0)
        self.assertNotIn(b'fictional-sensitive-location',(self.root/'location-free.sqlite3').read_bytes())
        with sqlite3.connect(self.source) as c:self.assertEqual(c.execute("SELECT count(*) FROM operations_locationshare").fetchone()[0],1)

    def test_account_recovery_gate_is_preserved(self):
        with sqlite3.connect(self.source) as c:
            c.execute("CREATE TABLE operations_accountsecurity (id INTEGER PRIMARY KEY, must_change_password INTEGER)")
            c.execute("INSERT INTO operations_accountsecurity VALUES (1, 1)")
        dest=self.root/'recovery-gate.sqlite3'
        result=snapshot(self.source,dest)
        self.assertEqual(result['table_counts']['operations_accountsecurity'],1)
        with sqlite3.connect(dest) as c:
            self.assertEqual(c.execute('SELECT must_change_password FROM operations_accountsecurity').fetchone()[0],1)
