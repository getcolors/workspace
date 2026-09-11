"""Temporary checkout fixtures for the copy/dependency gate; no real SSH reads."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml

SCRIPT = Path(__file__).with_name('compute-copy-contracts.py')
spec = importlib.util.spec_from_file_location('compute_copy_contracts', SCRIPT)
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)
SOURCE = SCRIPT.with_name('ssh_config_update.py').read_text()
PIN = 'a' * 40
URL = 'github:getcolors/colors-compute#' + PIN


class CopyContracts(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.canonical = self.root/'canonical.py'
        self.canonical.write_text(SOURCE)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def package(self, name='sample', color='blue', code=None, adapter='singleton'):
        repo = self.root/name
        self.write(repo/f'skills/package-{name}-{color}/SKILL.md', 'fixture')
        if color == 'blue':
            self.write(repo/'blue/pyproject.toml', '[project]\nname="sample"\ndependencies=["colors-compute-blue @ git+https://github.com/getcolors/colors-compute.git@' + PIN + '#subdirectory=blue"]\n')
            path = repo/'blue/src/package_sample_blue/resources/tools/ansible-local/main.yml'
        elif color == 'red':
            for manifest in ('red/package.json', 'package.json'):
                self.write(repo/manifest, json.dumps({'dependencies': {'colors-compute-red': URL}}))
            path = repo/'red/resources/tools/ansible-local/main.yml'
        else:
            self.write(repo/'deps.edn', '{:deps {io.github.getcolors/colors-compute {:git/url "https://github.com/getcolors/colors-compute.git" :git/sha "' + PIN + '" :deps/root "green"}}}')
            path = repo/'src/resources/io/github/getcolors/sample/tools/ansible-local/main.yml'
        play = [{'name':'fixture', 'hosts':'local','connection':'local','gather_facts':False,'become':False,
                 'vars':{'colors_keygen':checker.KEYGEN}, 'tasks':[{
                     'name':'update', 'ansible.builtin.command':{'argv':['python3','-c',code or SOURCE], 'stdin':checker.ADAPTERS[adapter]},
                     'environment':{'HOME':"{{ lookup('env', 'HOME') }}"},'register':'colors_ssh_update','changed_when':"colors_ssh_update.stdout == 'changed'"}]}]
        self.write(path, yaml.safe_dump(play, sort_keys=False))
        return repo, path

    def audit(self):
        return checker.audit(self.root, self.canonical)

    def test_all_colors_and_both_connection_adapters(self):
        for color in ('blue','green','red'):
            self.package(color=color, adapter='joined' if color == 'green' else 'singleton')
        report = self.audit()
        self.assertEqual([], report.errors)
        self.assertEqual(3, len(report.checked))

    def test_comments_docstrings_and_formatting_are_presentation(self):
        self.package(code=SOURCE.replace('Reference copied into package-owned Ansible plays; stdin contains connection metadata.', 'Package description.') + '\n# local documentation\n')
        self.assertEqual([], self.audit().errors)

    def test_executable_change_even_outside_update_is_rejected(self):
        for code in (SOURCE.replace('ForwardAgent no', 'ForwardAgent yes'), SOURCE + '\nprint("extra executable")\n', SOURCE.replace('fcntl.LOCK_EX', 'fcntl.LOCK_SH')):
            with self.subTest(code=code[-30:]):
                self.package(code=code)
                self.assertTrue(any('executable AST' in error for error in self.audit().errors))

    def test_dangerous_envelope_changes_are_rejected(self):
        for change in ('remote', 'ignore', 'root', 'extra-task', 'constant-host'):
            with self.subTest(change=change):
                _, path = self.package()
                data = yaml.safe_load(path.read_text()); task = data[0]['tasks'][0]
                if change == 'remote': data[0]['connection'] = 'ssh'
                if change == 'ignore': task['ignore_errors'] = True
                if change == 'root': task['ansible.builtin.command']['stdin'] = checker.ADAPTERS['singleton'].replace("'user': user", "'user': 'root'")
                if change == 'extra-task': data[0]['tasks'].append({'shell':'touch ~/.ssh/config'})
                if change == 'constant-host': data[0]['vars']['ip'] = '192.0.2.4'
                path.write_text(yaml.safe_dump(data))
                self.assertTrue(self.audit().errors)

    def test_duplicate_yaml_keys_fail_closed(self):
        _, path = self.package()
        path.write_text(path.read_text().replace('connection: local', 'connection: local\n  connection: ssh'))
        self.assertTrue(any('duplicate YAML' in error for error in self.audit().errors))

    def test_missing_color_copy_is_not_hidden_by_another_color(self):
        self.package(color='blue')
        _, path = self.package(color='red'); path.unlink()
        self.assertTrue(any('sample/red: expected one' in error for error in self.audit().errors))

    def test_borrowed_play_symlink_is_not_a_package_copy(self):
        _, path = self.package()
        borrowed = self.root/'borrowed.yml'
        borrowed.write_text(path.read_text())
        path.unlink(); path.symlink_to(borrowed)
        self.assertTrue(any('owned package file' in error for error in self.audit().errors))

    def test_managed_and_noncompute_exclusions_do_not_skip_dependencies(self):
        repo, path = self.package('agent-network-k8s'); path.unlink()
        self.package('dotfiles')[1].unlink()
        self.package('colors-compute')[1].unlink()
        self.assertEqual([], self.audit().errors)
        (repo/'blue/pyproject.toml').write_text('[project]\ndependencies=[]')
        self.assertTrue(any('direct colors-compute' in error for error in self.audit().errors))

    def test_dependency_comments_and_transitive_facades_are_not_direct(self):
        repo, _ = self.package(color='green')
        (repo/'deps.edn').write_text('; io.github.getcolors/colors-compute {:git/sha "' + PIN + '"}\n{:deps {io.github.getcolors/once {}}}')
        self.assertTrue(any('Green requires' in error for error in self.audit().errors))
        repo, _ = self.package(color='red')
        (repo/'package.json').write_text(json.dumps({'dependencies': {'package-once-red':'*'}}))
        self.assertTrue(any('Red facade' in error for error in self.audit().errors))

    def test_reusable_red_peer_requires_matching_development_and_launcher_pin(self):
        repo, _ = self.package('neon', 'red')
        facade = {'peerDependencies':{'colors-compute-red':'*'},'peerDependenciesMeta':{'colors-compute-red':{'optional':True}},'devDependencies':{'colors-compute-red':URL}}
        (repo/'package.json').write_text(json.dumps(facade))
        launcher = self.write(repo/'skills/package-neon-red/red', json.dumps({'colors-compute-red':URL}))
        self.assertEqual([], self.audit().errors)
        launcher.write_text(json.dumps({'colors-compute-red':'github:getcolors/colors-compute#main'}))
        self.assertTrue(self.audit().errors)

    def test_reusable_blue_range_requires_standalone_pin(self):
        repo, _ = self.package('once')
        requirement = 'colors-compute-blue @ git+https://github.com/getcolors/colors-compute.git@' + PIN + '#subdirectory=blue'
        (repo/'blue/pyproject.toml').write_text('[project]\ndependencies=["colors-compute-blue>=0.1.0"]\n[dependency-groups]\ndev=[' + json.dumps(requirement) + ']')
        self.assertTrue(self.audit().errors)
        self.write(repo/'skills/package-once-blue/blue', '# dependencies = [' + json.dumps(requirement) + ']')
        self.assertEqual([], self.audit().errors)

    def test_reviewed_variants_do_not_allow_unrelated_drift(self):
        for name in ('alice','walter','automq'):
            code = checker.updater_source(SOURCE, name)
            self.package(name, 'green', code=code, adapter='joined')
        self.assertEqual([], self.audit().errors)
        self.package('walter', 'green', code=checker.updater_source(SOURCE, 'walter').replace('seat_marker.fullmatch(line)', 'seat_marker.search(line)'))
        self.assertTrue(any('walter/green' in error for error in self.audit().errors))

    def test_walter_migrates_only_owned_prefixed_seats_and_removes_retired_seats(self):
        scope={'__name__':'fixture'}
        exec(compile(checker.updater_source(SOURCE, 'walter'), '<fixture-updater>', 'exec'), scope)
        home=self.root/'home'; (home/'.ssh').mkdir(parents=True)
        path=home/'.ssh/config'
        path.write_text('# BEGIN walter demo-retired ANSIBLE MANAGED BLOCK\nHost demo-retired\n User old\n# END walter demo-retired ANSIBLE MANAGED BLOCK\n# BEGIN other demo-foreign ANSIBLE MANAGED BLOCK\nHost unrelated\n User keep\n# END other demo-foreign ANSIBLE MANAGED BLOCK\n')
        payload={'host_alias':'demo','ssh_hosts':[{'name':'demo','ip':'192.0.2.1','user':'ubuntu'}], 'keygen':False,'block_state':'present','legacy_marker_prefix':'walter'}
        self.assertTrue(scope['update'](payload,home))
        self.assertNotIn('demo-retired',path.read_text())
        self.assertIn('other demo-foreign',path.read_text())
        self.assertIn('User ubuntu',path.read_text())
        self.assertNotIn('IdentityFile',path.read_text())
        self.assertFalse(scope['update'](payload,home))


if __name__ == '__main__':
    unittest.main()
