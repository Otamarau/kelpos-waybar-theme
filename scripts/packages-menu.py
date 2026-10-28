#!/usr/bin/env python3
"""Package browser for Rofi Quick Menu; installs remain interactive in Kitty."""
import html
import configparser
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

ICON_CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'rofi-package-icons'
ICON_URL = 'https://raw.githubusercontent.com/PapirusDevelopmentTeam/papirus-icon-theme/master/Papirus/48x48/apps/'


def clean(value):
    return ''.join(c if c.isprintable() else ' ' for c in str(value))


def header(key, value):
    print(f'\0{key}\x1f{value}')


def row(label, action, **options):
    fields = ['info', json.dumps(action)]
    for key, value in options.items():
        fields.extend([key, str(value)])
    print(clean(label) + '\0' + '\x1f'.join(fields))


def run(args):
    return subprocess.run(args, capture_output=True, text=True, timeout=35,
                          env={**os.environ, 'LC_ALL': 'C'})


@contextmanager
def loading(message):
    """Keep one transient loading notification while Rofi waits for this script."""
    notification_id = None

    def update(body, finished=False):
        nonlocal notification_id
        args = ['notify-send', '--print-id', '--transient', '--app-name', 'Quick Menu',
                '--expire-time', '1800' if finished else '45000']
        if notification_id:
            args += ['--replace-id', notification_id]
        args += ['Packages' if finished else 'Loading packages…', html.escape(clean(body))]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip().isdigit():
                notification_id = result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass  # Notifications must never prevent package searches.

    update(message)
    try:
        yield update
    except Exception:
        if notification_id:
            update('Could not finish loading. See the package menu for details.', True)
        raise
    else:
        if notification_id:
            update('Loading finished.', True)


@lru_cache(maxsize=1)
def icon_catalog():
    """Resolve local files directly, even when the configured theme is absent."""
    icons = {}
    roots = [Path.home() / '.local/share/icons', Path('/usr/share/icons/hicolor'),
             Path(__file__).resolve().parent / 'package-icons',
             ICON_CACHE,
             Path('/usr/share/pixmaps'), Path('/usr/share/icons/Adwaita'),
             Path('/usr/share/icons/AdwaitaLegacy')]
    for root in roots:
        paths = sorted(root.rglob('*'), key=lambda p: ('scalable' not in p.parts,
                                                     '48x48' not in p.parts, str(p)))
        for path in paths:
            if path.suffix.lower() in {'.svg', '.png', '.xpm'} and path.is_file():
                icons.setdefault(path.stem.casefold(), str(path))
    desktop_icons = {}
    for root in [Path('/usr/share/applications'), Path.home() / '.local/share/applications']:
        for path in sorted(root.glob('*.desktop')):
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                parser.read(path, encoding='utf-8')
                icon = parser.get('Desktop Entry', 'Icon', fallback='')
            except (configparser.Error, UnicodeError, OSError):
                continue
            resolved = icon if Path(icon).is_absolute() and Path(icon).is_file() else icons.get(icon.casefold())
            if resolved:
                desktop_icons[str(path)] = resolved
                icons.setdefault(path.stem.casefold(), resolved)
    packages = {}
    if desktop_icons:
        owners = run(['pacman', '-Qo', '--', *desktop_icons])
        for line in owners.stdout.splitlines():
            path, separator, owner = line.partition(' is owned by ')
            if separator and path in desktop_icons:
                packages.setdefault(owner.split()[0], desktop_icons[path])
    return icons, packages


def icon_names(name):
    base = re.sub(r'-(?:bin|git|nightly|beta|launcher)$', '', name)
    return list(dict.fromkeys([name, base]))


def fetch_icon(name):
    """Download only icons from a fixed public theme; never execute package data."""
    if not re.fullmatch(r'[a-zA-Z0-9_.+-]+', name):
        return None
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    dest = ICON_CACHE / (name + '.svg')
    miss = ICON_CACHE / (name + '.miss')
    if dest.is_file():
        return str(dest)
    if miss.exists() and time.time() - miss.stat().st_mtime < 600:
        return None
    try:
        filename = name + '.svg'
        # Git symlinks in the theme are returned as a target filename.
        for _ in range(3):
            request = urllib.request.Request(ICON_URL + filename,
                                             headers={'User-Agent': 'Rofi-Package-Icons/1.0'})
            with urllib.request.urlopen(request, timeout=1.5) as response:
                data = response.read(262145)
            if len(data) > 262144:
                break
            if not data.lstrip().startswith(b'<'):
                filename = data.decode().strip()
                if not re.fullmatch(r'[a-zA-Z0-9_.+-]+\.svg', filename):
                    break
                continue
            if ET.fromstring(data).tag != '{http://www.w3.org/2000/svg}svg':
                break
            temporary = dest.with_suffix(f'.{os.getpid()}.tmp')
            temporary.write_bytes(data)
            temporary.replace(dest)
            return str(dest)
    except (OSError, ValueError, ET.ParseError):
        pass
    miss.touch()
    return None


def fetch_missing_icons(packages):
    icons, installed = icon_catalog()
    missing = []
    # Bound network work; cached icons remain available for all subsequent searches.
    for package in packages[:24]:
        name = package['name']
        candidates = icon_names(name)
        if name not in installed and not any(c.casefold() in icons for c in candidates):
            missing.extend(candidates)
    names = list(dict.fromkeys(missing))[:24]
    if names:
        with ThreadPoolExecutor(max_workers=12) as pool:
            for name, path in zip(names, pool.map(fetch_icon, names)):
                if path:
                    icons[name.casefold()] = path


def package_icon(name):
    icons, packages = icon_catalog()
    if name in packages:
        return packages[name]
    candidates = icon_names(name)
    for candidate in candidates:
        if candidate.casefold() in icons:
            return icons[candidate.casefold()]
    return icons.get('package-x-generic', 'application-x-executable')


def frame(state, message):
    header('prompt', '󰏖')
    header('markup-rows', 'false')
    header('no-custom', 'false')
    header('data', json.dumps(state))
    header('message', html.escape(clean(message)))


def home(source='all', message=''):
    frame({'source': source}, message or
          f'Search: {source} · type a package or description and press Enter')
    row('Search packages…', {'action': 'search'})
    for value, label in [('all', 'Repositories + AUR'), ('repo', 'Official repositories'),
                         ('aur', 'AUR')]:
        row(('✓ ' if value == source else '') + label,
            {'action': 'source', 'source': value})


def search_prompt(source):
    frame({'source': source},
          f'Search: {source} · type a package or description and press Enter')
    # Rofi 2.0 passes custom text as argv[1], but has no ROFI_INPUT.
    # Keep the mode open initially, but let typing filter this placeholder out.
    # A permanent nonselectable row blocks Enter from accepting custom text.
    row('…', {}, nonselectable='true')


def relevance(package, query):
    name = package['name'].casefold()
    query = query.strip().casefold()
    if name == query:
        return (0, 0, package['repo'] == 'aur')
    # Language packs and extensions should not crowd out the actual apps.
    auxiliary = bool(package.get('addon')
                     or re.search(r'-(?:i18n|l10n|langpack|locale|docs?|debug|extension)(?:-|$)', name)
                     or re.search(r'\b(?:language packs?|extensions?|add-ons?|plugins?|spellchecker)\b',
                                  package['desc'], re.IGNORECASE))
    match = 0 if name.startswith(query) else 1 if query in name else 2
    return (2 if auxiliary else 1, match, package['repo'] == 'aur')


def search(query, source):
    query = query.strip()
    if len(query.strip()) < 2:
        home(source, 'Enter at least two characters to search.')
        return
    with loading(f'Searching {source} for “{query}”…') as progress:
        search_packages(query, source, progress)


def search_packages(query, source, progress):
    args = ['pacman', '-Ss', '--color', 'never'] if source == 'repo' else [
        'yay', '-Ss', '--color', 'never', '--sortby', 'popularity',
        '--topdown', '--doublelineresults'] + (['--aur'] if source == 'aur' else [])
    result = run(args + ['--', query])
    packages = []
    for line in result.stdout.splitlines():
        match = re.match(r'^([\w.-]+)/([\w@+.:-]+)\s+(\S+)', line)
        if match:
            repo, name, version = match.groups()
            packages.append({'repo': repo, 'name': name, 'version': version, 'desc': '',
                             'addon': bool(re.search(r'\([^)]*-addons\b', line))})
        elif line.startswith(' ') and packages:
            packages[-1]['desc'] += ' ' + line.strip()
    # Stable sorting preserves yay's popularity order among equally relevant AUR hits.
    packages.sort(key=lambda package: relevance(package, query))
    state = {'source': source, 'query': query, 'packages': packages[:100]}
    message = f'{len(packages)} matches for “{query}” · best matches first · select for details'
    if len(packages) > 100:
        message += ' · showing first 100; narrow your search'
    if result.stderr.strip():
        message += ' · ' + clean(result.stderr.strip())[:250]
    elif result.returncode and not packages:
        message = 'No matches. Try another search.'
    progress(f'{len(packages)} matches · loading app icons…')
    show_results(state, message)


def show_results(state, message=''):
    fetch_missing_icons(state.get('packages', []))
    frame(state, message or f'Results for “{state.get("query", "")}" · select for details')
    row('New search / change source', {'action': 'home'})
    installed = set(run(['pacman', '-Qq']).stdout.splitlines())
    for package in state.get('packages', []):
        suffix = ' ✓ installed' if package['name'] in installed else ''
        row(f'{package["name"]} [{package["repo"]}] {package["version"]}{suffix}'
            f' — {package["desc"].strip()}', {'action': 'details', 'package': package},
            icon=package_icon(package['name']))


def target(package):
    value = package['repo'] + '/' + package['name']
    if not re.fullmatch(r'[\w.-]+/[\w@+.:-]+', value):
        raise ValueError('Invalid package name')
    return value


def details(state, package):
    with loading(f'Fetching details for {package["name"]}…'):
        show_details(state, package)


def show_details(state, package):
    tool = 'yay' if package['repo'] == 'aur' else 'pacman'
    result = run([tool, '-Si', '--color', 'never', '--', target(package)])
    fields = []
    for line in result.stdout.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            if key.strip() in {'Description', 'Version', 'Repository', 'URL',
                               'Download Size', 'Installed Size', 'Depends On', 'Votes'}:
                fields.append(f'{key.strip()}: {value.strip()}')
    message = ' · '.join(fields) or package['desc']
    if result.returncode:
        message += ' · Details unavailable: ' + result.stderr[:200]
    frame(state, message)
    header('no-custom', 'true')
    row('New search / change source', {'action': 'home'})
    row('Install ' + package['name'] + ' in terminal',
        {'action': 'install', 'package': package}, icon=package_icon(package['name']))
    row('Back to results', {'action': 'results'})


def install(package):
    name = target(package)
    command = ['yay', '-S', '--needed', '--', name] if package['repo'] == 'aur' else [
        'sudo', 'pacman', '-S', '--needed', '--', name]
    print('Installing ' + name, flush=True)
    status = subprocess.run(command).returncode
    print('\n' + ('Finished.' if status == 0 else f'Installation exited with status {status}.'))
    input('Press Enter to close…')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--install':
        install(json.loads(sys.argv[2]))
        return
    state = json.loads(os.environ.get('ROFI_DATA') or '{}')
    source = state.get('source', 'all')
    retv = os.environ.get('ROFI_RETV', '0')
    if retv == '0':
        home()
        return
    if retv == '2':
        search(sys.argv[1] if len(sys.argv) > 1 else '', source)
        return
    action = json.loads(os.environ.get('ROFI_INFO') or '{}')
    kind = action.get('action')
    if kind == 'search':
        search_prompt(source)
    elif kind == 'source':
        search_prompt(action['source'])
    elif kind == 'details':
        details(state, action['package'])
    elif kind == 'results':
        show_results(state)
    elif kind == 'install':
        target(action['package'])
        subprocess.Popen(['kitty', '--title', 'Package installation', sys.executable,
                          str(Path(__file__).resolve()), '--install',
                          json.dumps(action['package'])], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    else:
        home(source)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        home(message=f'Package browser: {error}')
