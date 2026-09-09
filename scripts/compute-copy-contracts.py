#!/usr/bin/env python3
"""Gate compute dependencies and package-owned SSH updater copies.

Requires Python 3.11+ and PyYAML. Run from anywhere; --workspace supports a
separate checkout tree. No package imports, launchers, cloud calls, or SSH reads.

Allowed copy differences: YAML/Python formatting, comments, docstrings and task
names; singleton stdin builds one host from runtime ip/user, while cluster stdin
passes the joined ssh_hosts list. Everything executable in the updater and the
local-only task envelope is gated. Whole language-specific preflight/compute
modules are adapters, not interchangeable copies; this does not prove their
workflow ordering or runtime inventory correctness (package integration tests do).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NON_COMPUTE = {"dotfiles": "configures the workstation; creates no compute"}
MANAGED_ONLY = {"agent-network-k8s", "agent-network-doks"}
REUSABLE = {"once", "neon"}
SHA = r"[0-9a-f]{40}"
GIT_RED = re.compile(r"github:getcolors/colors-compute#(" + SHA + r")\Z")
GIT_BLUE = re.compile(r"colors-compute-blue\s*@\s*git\+https://github.com/getcolors/colors-compute(?:\.git)?@(" + SHA + r")#subdirectory=blue\Z")
KEYGEN = "<% if ssh-keygen %>true<% else %>false<% endif %>"
STDIN_BASE = "{{ {'host_alias': host_alias, 'ssh_hosts': HOSTS, 'block_state': block_state, 'keygen': colors_keygen, 'legacy_marker_prefix': ssh_legacy_marker_prefix | default('')} | to_json }}"
ADAPTERS = {
    "singleton": STDIN_BASE.replace("HOSTS", "[{'name': host_alias, 'ip': ip, 'user': user}]"),
    "joined": STDIN_BASE.replace("HOSTS", "ssh_hosts"),
}


class StrictLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError("duplicate YAML mapping key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


class WithoutDocstrings(ast.NodeTransformer):
    def strip(self, node):
        self.generic_visit(node)
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        return node
    visit_Module = strip
    visit_FunctionDef = strip
    visit_AsyncFunctionDef = strip
    visit_ClassDef = strip


def python_contract(source):
    return ast.dump(WithoutDocstrings().visit(ast.parse(source)), include_attributes=False)


def compact(expression):
    return ''.join(re.findall(r"'[^']*'|\"[^\"]*\"|\S", expression)) if isinstance(expression, str) else None


def updater_source(source, package):
    # Reviewed explicit variants, never a blanket exemption. Alice preserves its
    # stricter managed-key identity-agent policy. Walter migrates only anchored
    # legacy per-seat markers, including retired seats (SSH standard section 8).
    if package == 'alice':
        old = "block.extend(['    IdentityFile ~/.ssh/' + profile, '    IdentitiesOnly yes'])"
        new = "block.extend(['    IdentityFile ~/.ssh/' + profile, '    IdentitiesOnly yes', '    IdentityAgent none'])"
    elif package == 'walter':
        old = "            pairs['# BEGIN ' + legacy + ' ' + profile + ' ANSIBLE MANAGED BLOCK'] = '# END ' + legacy + ' ' + profile + ' ANSIBLE MANAGED BLOCK'"
        new = old + "\n" + "\n".join([
            "            seat_marker = re.compile(r'# BEGIN ' + re.escape(legacy + ' ' + profile) + r'-[a-z_][a-z0-9_-]{0,31} ANSIBLE MANAGED BLOCK')",
            "            for line in old.splitlines():",
            "                if seat_marker.fullmatch(line):",
            "                    pairs[line] = line.replace('# BEGIN ', '# END ', 1)",
        ])
    else:
        return source
    if source.count(old) != 1:
        raise ValueError('canonical updater changed; review the explicit ' + package + ' variant')
    return source.replace(old, new)


def expected_updater(source, package):
    return python_contract(updater_source(source, package))


def check_play(path: Path, canonical: str) -> str:
    plays = yaml.load(path.read_text(), Loader=StrictLoader)
    if not isinstance(plays, list) or len(plays) != 1 or not isinstance(plays[0], dict):
        raise ValueError("expected one local SSH play")
    play = plays[0]
    if set(play) != {"name", "hosts", "connection", "gather_facts", "become", "vars", "tasks"}:
        raise ValueError("unexpected SSH play fields")
    if not isinstance(play['name'], str) or play['hosts'] != 'local' or play['connection'] != 'local' or play['gather_facts'] is not False or play['become'] is not False:
        raise ValueError("SSH play must run on local without facts or privilege escalation")
    if play['vars'] != {'colors_keygen': KEYGEN}:
        raise ValueError("SSH play may template only the desired keygen boolean")
    tasks = play['tasks']
    if not isinstance(tasks, list) or len(tasks) != 1 or not isinstance(tasks[0], dict):
        raise ValueError("expected exactly one locked SSH updater task")
    task = tasks[0]
    if set(task) != {'name', 'ansible.builtin.command', 'environment', 'register', 'changed_when'} or not isinstance(task['name'], str):
        raise ValueError("unexpected SSH task fields or lifecycle bypass")
    if task['environment'] != {'HOME': "{{ lookup('env', 'HOME') }}"} or task['register'] != 'colors_ssh_update' or task['changed_when'] != "colors_ssh_update.stdout == 'changed'":
        raise ValueError("SSH task HOME or result handling differs")
    command = task['ansible.builtin.command']
    if not isinstance(command, dict) or set(command) != {'argv', 'stdin'}:
        raise ValueError("SSH updater must use argv and metadata stdin only")
    argv = command['argv']
    if not isinstance(argv, list) or len(argv) != 3 or argv[:2] != ['python3', '-c'] or not isinstance(argv[2], str):
        raise ValueError("SSH updater invocation differs")
    if python_contract(argv[2]) != canonical:
        raise ValueError("embedded SSH updater differs from canonical executable AST")
    adapters = [name for name, expected in ADAPTERS.items() if compact(command['stdin']) == compact(expected)]
    if not adapters:
        raise ValueError("SSH stdin is not a documented runtime connection adapter")
    return adapters[0]


def edn(source):
    """Read the literal subset used by deps.edn; reject duplicate/malformed maps.

    This deliberately does not evaluate EDN tags, reader macros, or code.
    Comments and strings cannot masquerade as dependency coordinates.
    """
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|;[^\n]*|[{}\[\]()]|[^\s,{}\[\]();]+', source)
    tokens = [x for x in tokens if not x.startswith(';')]
    position = 0
    def read():
        nonlocal position
        if position >= len(tokens): raise ValueError('truncated deps.edn')
        token = tokens[position]; position += 1
        if token in ('{', '[', '('):
            closing = {'{': '}', '[': ']', '(': ')'}[token]
            values = []
            while position < len(tokens) and tokens[position] != closing:
                values.append(read())
            if position >= len(tokens): raise ValueError('unclosed deps.edn form')
            position += 1
            if token != '{': return values
            if len(values) % 2: raise ValueError('odd deps.edn map')
            result = {}
            for key, value in zip(values[::2], values[1::2]):
                if not isinstance(key, str) or key in result: raise ValueError('invalid deps.edn map key')
                result[key] = value
            return result
        if token in ('}', ']', ')') or token.startswith('#'): raise ValueError('unsupported deps.edn form')
        return json.loads(token) if token.startswith('"') else token
    result = read()
    if position != len(tokens): raise ValueError('extra deps.edn forms')
    return result


def first_file(paths):
    return next((p for p in paths if p.is_file()), paths[0])


def check_dependency(repo: Path, color: str):
    if color == 'green':
        path = first_file([repo/'green/deps.edn', repo/'deps.edn'])
        data = edn(path.read_text())
        coordinate = data.get(':deps', {}).get('io.github.getcolors/colors-compute', {})
        if not isinstance(coordinate, dict) or coordinate.get(':git/url') not in ('https://github.com/getcolors/colors-compute.git', 'https://github.com/getcolors/colors-compute') or not re.fullmatch(SHA, str(coordinate.get(':git/sha', ''))) or coordinate.get(':deps/root') != 'green':
            raise ValueError('Green requires a direct immutable colors-compute Git dependency')
        return
    if color == 'blue':
        path = first_file([repo/'blue/pyproject.toml', repo/'pyproject.toml'])
        data = tomllib.loads(path.read_text())
        requirements = data.get('project', {}).get('dependencies', [])
        if any(GIT_BLUE.fullmatch(x) for x in requirements): return
        names = [x for x in requirements if re.match(r'colors-compute-blue(?:\s*[<>=!~;]|\Z)', x)]
        if not names: raise ValueError('Blue requires a direct colors-compute dependency')
        sources = data.get('tool', {}).get('uv', {}).get('sources', {}).get('colors-compute-blue', {})
        if isinstance(sources, dict) and sources.get('git') in ('https://github.com/getcolors/colors-compute.git', 'https://github.com/getcolors/colors-compute') and re.fullmatch(SHA, str(sources.get('rev', ''))) and sources.get('subdirectory') == 'blue': return
        dev = data.get('dependency-groups', {}).get('dev', [])
        pins = [GIT_BLUE.fullmatch(x)[1] for x in dev if isinstance(x, str) and GIT_BLUE.fullmatch(x)]
        launcher = repo/f'skills/package-{repo.name}-blue/blue'
        if repo.name not in REUSABLE or len(pins) != 1 or not launcher.is_file() or not re.search(r'colors-compute-blue[^\n]*' + pins[0], launcher.read_text()):
            raise ValueError('Blue reusable range requires reviewed dev and standalone immutable pins')
        return
    native = json.loads((repo/'red/package.json').read_text())
    aliases = [name for name in ('colors-compute-red', 'colors-compute') if name in native.get('dependencies', {})]
    if len(aliases) != 1: raise ValueError('Red requires exactly one direct compute dependency coordinate')
    dependency_name = aliases[0]
    selected = native['dependencies'][dependency_name]
    if not GIT_RED.fullmatch(selected): raise ValueError('Red native package requires a direct immutable compute dependency')
    facade = json.loads((repo/'package.json').read_text())
    if facade.get('dependencies', {}).get(dependency_name) == selected: return
    launcher = repo/f'skills/package-{repo.name}-red/red'
    if repo.name not in REUSABLE or facade.get('peerDependencies', {}).get('colors-compute-red') != '*' or facade.get('peerDependenciesMeta', {}).get('colors-compute-red', {}).get('optional') is not True or facade.get('devDependencies', {}).get('colors-compute-red') != selected or not launcher.is_file() or not re.search(r'"colors-compute-red"\s*:\s*"' + re.escape(selected) + '"', launcher.read_text()):
        raise ValueError('Red facade must pin compute directly or use reviewed reusable peer/dev/launcher pins')


def play_paths(repo, color):
    patterns = {
        'green': ['green/src/resources/io/github/getcolors/*/tools/ansible-local/main.yml', 'green/resources/io/github/getcolors/*/tools/ansible-local/main.yml', 'src/resources/io/github/getcolors/*/tools/ansible-local/main.yml'],
        'red': ['red/resources/tools/ansible-local/main.yml'],
        'blue': ['blue/src/package_*_blue/resources/tools/ansible-local/main.yml', 'src/package_*_blue/resources/ansible-local/main.yml'],
    }
    return sorted({p for pattern in patterns[color] for p in repo.glob(pattern) if p.is_file()})


@dataclass
class Report:
    checked: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def audit(workspace: Path, canonical_path: Path | None = None) -> Report:
    canonical_source = (canonical_path or workspace/'workspace/scripts/ssh_config_update.py').read_text()
    python_contract(canonical_source)
    report = Report()
    for repo in sorted(workspace.iterdir()):
        if not repo.is_dir() or repo.name == 'colors-compute': continue
        skills = sorted(repo.glob('skills/package-*/SKILL.md'))
        if not skills: continue
        if repo.name in NON_COMPUTE:
            report.skipped.append(f'{repo.name}: {NON_COMPUTE[repo.name]}'); continue
        for skill in skills:
            match = re.fullmatch(r'package-' + re.escape(repo.name) + r'-(blue|red|green)', skill.parent.name)
            if not match:
                report.errors.append(f'{skill.relative_to(workspace)}: unclassified package skill'); continue
            color = match[1]; label = f'{repo.name}/{color}'
            try:
                check_dependency(repo, color)
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
                report.errors.append(f'{label}: dependency: {error}')
            if repo.name in MANAGED_ONLY:
                report.checked.append(f'{label}: managed cluster; no operator VM SSH'); continue
            paths = play_paths(repo, color)
            if len(paths) != 1:
                report.errors.append(f'{label}: expected one package-owned SSH play, found {len(paths)}'); continue
            try:
                if paths[0].is_symlink() or not paths[0].resolve().is_relative_to(repo.resolve()):
                    raise ValueError('SSH play must be an owned package file, not a borrowed symlink')
                adapter = check_play(paths[0], expected_updater(canonical_source, repo.name))
                variant = f' ({repo.name} reviewed policy/migration variant)' if repo.name in ('alice', 'walter') else ''
                report.checked.append(f'{label}: canonical updater{variant}, {adapter} adapter')
            except (OSError, ValueError, TypeError, KeyError, SyntaxError, yaml.YAMLError) as error:
                report.errors.append(f'{label}: SSH copy: {error}')
    if not report.checked and not report.errors:
        report.errors.append('no compute package skills found')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=ROOT)
    parser.add_argument('--canonical', type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.workspace.resolve(), args.canonical)
    except (OSError, ValueError, SyntaxError) as error:
        print(f'compute-copy-contracts: {error}', file=sys.stderr); return 2
    for entry in report.checked: print('OK ' + entry)
    for entry in report.skipped: print('SKIP ' + entry)
    for entry in report.errors: print('FAIL ' + entry, file=sys.stderr)
    print(f'{len(report.checked)} color contracts checked; {len(report.errors)} failure(s)')
    return int(bool(report.errors))


if __name__ == '__main__':
    raise SystemExit(main())
