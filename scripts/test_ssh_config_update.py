#!/usr/bin/env python3
"""Offline integration checks for the updater copied into cluster local plays."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).with_name('ssh_config_update.py')
spec = importlib.util.spec_from_file_location('ssh_update', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def request(profile='cluster', keygen=True, state='present'):
    return {'host_alias': profile, 'keygen': keygen, 'block_state': state,
            'ssh_hosts': [{'name': profile, 'ip': '203.0.113.10', 'user': 'ubuntu'},
                          {'name': profile + '-worker-0', 'ip': '203.0.113.11', 'user': 'root'}]}


class Updates(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        (self.home / '.ssh').mkdir()
        self.config = self.home / '.ssh/config'

    def update(self, value):
        return module.update(value, self.home)

    def test_managed_external_delete_and_unrelated_preservation(self):
        original = '# kept\nHost external\n    User other\n'
        self.config.write_text(original)
        self.assertTrue(self.update(request()))
        value = self.config.read_text()
        self.assertTrue(value.startswith('# BEGIN cluster '))
        self.assertIn('IdentityFile ~/.ssh/cluster', value)
        self.assertIn('Host cluster-worker-0\n    HostName 203.0.113.11\n    User root', value)
        self.assertFalse(self.update(request()))
        self.assertTrue(self.update(request(keygen=False)))
        self.assertNotIn('IdentityFile', self.config.read_text())
        self.assertNotIn('IdentitiesOnly', self.config.read_text())
        self.assertTrue(self.update(request(state='absent')))
        self.assertEqual(original, self.config.read_text())
        self.assertFalse(self.update(request(state='absent')))
        self.assertEqual(0o600, self.config.stat().st_mode & 0o777)

    def test_unowned_alias_leading_scope_and_corrupt_marker_refuse(self):
        for original in ['Host cluster-worker-0\n User bob\n', 'Host="cluster"\n User bob\n', 'Host other\n User bob\nHost \"cluster\"\n User root\n', 'ServerAliveInterval 30\nHost *\n',
                         '# BEGIN cluster ANSIBLE MANAGED BLOCK\nHost cluster\n']:
            self.config.write_text(original)
            with self.assertRaises(ValueError):
                self.update(request())
            self.assertEqual(original, self.config.read_text())

    def test_legacy_marker_replaced_atomically(self):
        self.config.write_text('# BEGIN k8s cluster ANSIBLE MANAGED BLOCK\nHost cluster\n User root\n# END k8s cluster ANSIBLE MANAGED BLOCK\nHost other\n User bob\n')
        self.update({**request(), 'legacy_marker_prefix': 'k8s'})
        self.assertNotIn('# BEGIN k8s ', self.config.read_text())
        self.assertIn('Host other\n User bob\n', self.config.read_text())

    def test_directive_injection_and_symlinks_refuse(self):
        for key, value in [('name', 'cluster\nHost stolen'), ('ip', '203.0.113.1\nUser root'), ('user', 'root\nForwardAgent yes')]:
            payload = request()
            payload['ssh_hosts'][0][key] = value
            with self.assertRaises(ValueError):
                self.update(payload)
        target = self.home / 'unrelated'
        target.write_text('keep')
        self.config.symlink_to(target)
        with self.assertRaises(ValueError):
            self.update(request())
        self.assertEqual('keep', target.read_text())

    def test_fifo_config_refuses_without_blocking(self):
        os.mkfifo(self.config)
        result = subprocess.run([sys.executable, str(SOURCE)], input=json.dumps(request()),
                                text=True, capture_output=True, env={**os.environ, 'HOME': str(self.home)}, timeout=3)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('unsafe SSH config file', result.stderr)

    def test_concurrent_processes_preserve_every_deployment(self):
        self.config.write_text('Host unrelated\n User operator\n')
        def execute(index):
            return subprocess.run([sys.executable, str(SOURCE)], input=json.dumps(request('cluster-' + str(index))),
                                  text=True, capture_output=True, env={**os.environ, 'HOME': str(self.home)}, timeout=40)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(execute, range(20)))
        self.assertEqual([0] * 20, [result.returncode for result in results], [result.stderr for result in results])
        text = self.config.read_text()
        for index in range(20):
            self.assertEqual(1, text.count('# BEGIN cluster-' + str(index) + ' ANSIBLE MANAGED BLOCK'))
        self.assertIn('Host unrelated\n User operator\n', text)

    def test_all_copied_programs_are_identical(self):
        root = SOURCE.parent.parent.parent
        for package in ['automq', 'langfuse', 'mysql-agy', 'mysql-ha', 'postgres-agy', 'postgres-ha', 'k8s', 'clickhouse']:
            paths = [* (root / package / 'green/src/resources').glob('io/github/getcolors/*/tools/ansible-local/main.yml'),
                     * (root / package / 'blue/src').glob('*/resources/tools/ansible-local/main.yml'), root / package / 'red/resources/tools/ansible-local/main.yml']
            self.assertEqual(3, len(paths))
            for path in paths:
                play = path.read_text()
                script = play.split('          - |\n', 1)[1].split('        stdin:', 1)[0]
                actual = '\n'.join(line[14:] if line else '' for line in script.splitlines()) + '\n'
                self.assertEqual(SOURCE.read_text(), actual, str(path))


if __name__ == '__main__':
    unittest.main()
