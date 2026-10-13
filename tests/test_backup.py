"""
The nightly backup keeps the record once and actually prunes.
=============================================================
D112. The project lives under "My Apps" — a path with a space — and the old
`ls | xargs rm` split every path there, so nothing was ever pruned. Every
night also re-tarred the whole published record, so a year of nights would
have needed many times the disk this Mac has, locally and in iCloud.

These run the real script in a scratch root whose path has a space in it.
"""

# Enforces D124 — see docs/DECISIONS.md.
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), 'scripts', 'backup.sh')


class TheBackupPrunesAndKeepsTheRecordOnce(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base)
        self.root = os.path.join(self.base, 'My Apps', 'Oormani Suddi')
        os.makedirs(os.path.join(self.root, 'scripts'))
        shutil.copy(SCRIPT, os.path.join(self.root, 'scripts', 'backup.sh'))
        day = os.path.join(self.root, 'archive', '2026-10-01')
        os.makedirs(day)
        with open(os.path.join(day, 'APPROVAL.md'), 'w') as fh:
            fh.write('cleared')
        with open(os.path.join(self.root, 'archive', 'ledger.json'), 'w') as fh:
            fh.write('{}')
        self.local = os.path.join(self.root, '.backups')
        self.ext = os.path.join(self.base, 'Second Copy')
        os.makedirs(self.local)
        os.makedirs(self.ext)
        old = time.time() - 30 * 86400
        for i in range(1, 21):
            for folder in (self.local, self.ext):
                p = os.path.join(folder, f'oormani-2026-08-{i:02d}.tar.gz')
                open(p, 'w').close()
                os.utime(p, (old + i * 60, old + i * 60))

    def run_backup(self) -> str:
        env = dict(os.environ, OORMANI_BACKUP_DIR=self.ext,
                   OORMANI_BACKUP_QUIET='1', HOME=self.base)
        env.pop('OORMANI_BACKUP_LOCAL', None)
        out = subprocess.run(['bash', os.path.join(self.root, 'scripts', 'backup.sh')],
                             cwd=self.root, env=env, capture_output=True, text=True)
        return out.stdout + out.stderr

    def dailies(self, folder: str) -> list[str]:
        return [f for f in os.listdir(folder) if f.startswith('oormani-2')]

    def test_old_nightlies_are_pruned_in_both_places_despite_the_space(self):
        self.run_backup()
        self.assertEqual(len(self.dailies(self.local)), 14)
        self.assertEqual(len(self.dailies(self.ext)), 14)

    def test_each_archived_day_is_held_once_and_not_retarred(self):
        first = self.run_backup()
        self.assertIn('1 new or changed', first)
        for folder in (self.local, self.ext):
            self.assertTrue(os.path.exists(
                os.path.join(folder, 'record', '2026-10-01.tar.gz')))
        second = self.run_backup()
        self.assertIn('0 new or changed', second)

    def test_a_changed_day_is_tarred_again(self):
        self.run_backup()
        time.sleep(1.1)
        with open(os.path.join(self.root, 'archive', '2026-10-01', 'SIGNOFF.json'), 'w') as fh:
            fh.write('{}')
        self.assertIn('1 new or changed', self.run_backup())

    def test_the_nightly_holds_the_small_registers_not_the_record(self):
        self.run_backup()
        newest = max((os.path.join(self.local, f) for f in self.dailies(self.local)),
                     key=os.path.getmtime)
        names = subprocess.run(['tar', '-tzf', newest], capture_output=True,
                               text=True).stdout.split()
        self.assertIn('archive/ledger.json', names)
        self.assertFalse([n for n in names if n.startswith('archive/2026-10-01')])


class FailureIsAnExitCodeNotAFootnote(unittest.TestCase):
    """A backup job that always exits 0 is a job that has silently stopped.
    The script must say so in its exit status: a failed copy, a missing
    second medium, or an unpushed offsite all mean fewer than three copies,
    and fewer than three copies is a failure of the thing the script exists
    to do. (The scratch root is not a git repo, so its offsite check reads
    'no upstream' — exit 1 — even when every copy succeeded; that is pinned
    here as the rule, not worked around.)
    """

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base)
        self.root = os.path.join(self.base, 'My Apps', 'Oormani Suddi')
        os.makedirs(os.path.join(self.root, 'scripts'))
        shutil.copy(SCRIPT, os.path.join(self.root, 'scripts', 'backup.sh'))
        os.makedirs(os.path.join(self.root, 'archive', '2026-10-01'))
        self.local = os.path.join(self.root, '.backups')
        self.ext = os.path.join(self.base, 'Second Copy')
        os.makedirs(self.local)
        os.makedirs(self.ext)

    def run_backup(self):
        env = dict(os.environ, OORMANI_BACKUP_DIR=self.ext,
                   OORMANI_BACKUP_QUIET='1', HOME=self.base)
        p = subprocess.run(['bash', os.path.join(self.root, 'scripts', 'backup.sh')],
                           cwd=self.root, env=env, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def test_a_failed_second_copy_exits_1(self):
        os.chmod(self.ext, 0o500)          # cp into it cannot succeed
        self.addCleanup(os.chmod, self.ext, 0o700)
        rc, out = self.run_backup()
        self.assertEqual(rc, 1, out)
        self.assertIn('could not write everything', out)

    def test_every_copy_ok_but_offsite_unknown_is_still_a_failure(self):
        # The scratch root is not a git repo: 'no upstream' → fewer than
        # three copies → exit 1 even though local and second both worked.
        rc, out = self.run_backup()
        self.assertEqual(rc, 1, out)
        self.assertIn('fewer than three copies', out)

    def test_same_size_different_content_in_the_second_medium_is_copied(self):
        # The old dedupe compared byte SIZE. Seed the second copy with a
        # same-length but different file; a correct run copies over it.
        rc, _ = self.run_backup()          # both copies now exist and agree
        self.assertEqual(rc, 1)            # git unknown in scratch — fine
        day = os.path.join(self.root, 'archive', '2026-10-01')
        with open(os.path.join(day, 'SIGNOFF.json'), 'w') as fh:
            fh.write('{}')                 # the day changed → re-tar
        rc, _ = self.run_backup()
        local_rec = os.path.join(self.local, 'record', '2026-10-01.tar.gz')
        ext_rec = os.path.join(self.ext, 'record', '2026-10-01.tar.gz')
        size = os.path.getsize(local_rec)
        stale = os.urandom(size)           # same size, different bytes
        with open(ext_rec, 'wb') as fh:
            fh.write(stale)
        self.assertNotEqual(stale, open(local_rec, 'rb').read())
        rc, out = self.run_backup()
        self.assertEqual(open(ext_rec, 'rb').read(),
                         open(local_rec, 'rb').read(),
                         'same-size stale copy was not refreshed')


if __name__ == '__main__':
    unittest.main()
