# SPDX-License-Identifier: AGPL-3.0-only
"""Select an explicitly bound retained store; source/origin resolution stays local."""
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

try:
    from .compatibility_inventory import check, file_ref, read_json
except ImportError:
    from compatibility_inventory import check, file_ref, read_json

PROFILE = 'compat/evidence-stores/secondary-v1.json'


def evidence_root(source, reference=None):
    """Return the legacy source root or the selected profile's current-host root.

    Native records place this reference inside their independently reviewed reuse
    edge. Archive records bind it as an explicit record input. This only selects
    produced evidence: candidate, review, source, preparation and SDK references
    keep the caller's original source root and existing validators.
    """
    source = Path(source)
    if reference is None:
        return source
    check(isinstance(reference, dict) and reference.get('path') == PROFILE,
          'unrecognized retained evidence store')
    profile = read_json(file_ref(source, reference))
    check(isinstance(profile, dict) and set(profile) == {'schema', 'kind', 'hosts', 'scope'}
          and type(profile['schema']) is int and profile['schema'] == 1
          and profile['kind'] == 'secondary-evidence-store-v1'
          and isinstance(profile['scope'], str) and profile['scope'].strip(),
          'invalid retained evidence store policy')
    hosts = profile['hosts']
    check(isinstance(hosts, dict) and set(hosts) == {'windows', 'posix'},
          'retained evidence store needs explicit host views')
    for host, path_type in (('windows', PureWindowsPath), ('posix', PurePosixPath)):
        view = hosts[host]
        check(isinstance(view, dict) and set(view) == {'source_workspace', 'storage_workspace'},
              'invalid retained evidence host view')
        check(all(isinstance(v, str) and v for v in view.values()), 'invalid retained evidence root')
        paths = {key: path_type(value) for key, value in view.items()}
        check(all(p.is_absolute() and '..' not in p.parts and p.as_posix() == view[key]
                  and (host != 'windows' or len(p.drive) == 2 and p.drive[1] == ':' and p.drive[0].isalpha())
                  and (host != 'posix' or p.anchor == '/') for key, p in paths.items()),
              'retained evidence roots must be canonical absolute local paths')
        original, retained = paths['source_workspace'], paths['storage_workspace']
        check(not original.is_relative_to(retained) and not retained.is_relative_to(original),
              'retained evidence store overlaps source')
        check(not any(p.parts[i:i+2] == ('build', 'work')
                      for p in paths.values() for i in range(len(p.parts)-1)),
              'retained evidence root cannot be managed scratch')
    selected = hosts['windows' if os.name == 'nt' else 'posix']
    declared = Path(selected['source_workspace'])
    storage = Path(selected['storage_workspace'])
    check(source.resolve() == declared.resolve(), 'retained evidence source workspace changed')
    for directory in (declared, storage):
        check(directory.is_dir(), 'retained evidence workspace unavailable')
        check(all(not p.is_symlink() and not (hasattr(p, 'is_junction') and p.is_junction())
                  for p in (directory, *directory.parents)), 'retained evidence roots cannot use aliases')
    return storage
