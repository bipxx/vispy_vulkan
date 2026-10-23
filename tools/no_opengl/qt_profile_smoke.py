"""Exercise an installed selected Qt profile; not a native absence receipt."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import zipfile


def run(binding, manifest_path, bundle, output):
    report = {'status': 'FAILED_PROFILE_SMOKE', 'binding': binding,
              'python': sys.executable, 'prefix': sys.prefix,
              'scope': 'Installed byte verification, selected imports and QWidget painting only; native gates require separate observer.'}
    try:
        manifest = json.loads(manifest_path.read_text())
        report['manifest_sha256'] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        package = {'pyqt5': 'PyQt5', 'pyqt6': 'PyQt6', 'pyside6': 'PySide6'}[binding]
        report['installed_members_verified'] = 0
        report['wheels'] = []
        for wheel in sorted(bundle.glob('*.whl')):
            with zipfile.ZipFile(wheel) as archive:
                metadata_path = next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))
                metadata = archive.read(metadata_path).decode().splitlines()
                name = next(line.removeprefix('Name: ') for line in metadata if line.startswith('Name: '))
                distribution = importlib.metadata.distribution(name)
                for member in archive.namelist():
                    if member.endswith('/') or member.endswith('.dist-info/RECORD'):
                        continue
                    if '.data/' in member:
                        raise ValueError('Unmapped wheel data path: ' + member)
                    installed = Path(distribution.locate_file(member))
                    if not installed.is_file() or installed.read_bytes() != archive.read(member):
                        raise ValueError('Installed profile member differs: ' + str(installed))
                    report['installed_members_verified'] += 1
                report['wheels'].append({'name': name, 'version': distribution.version,
                                        'sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()})
        report['modules'] = {}
        for module in manifest['modules']:
            loaded = importlib.import_module(package + '.Qt' + module)
            report['modules'][module] = loaded.__file__
        for module in ('QtOpenGL', 'QtOpenGLWidgets', 'QtQuick', 'QtQml'):
            if importlib.util.find_spec(package + '.' + module) is not None:
                raise ValueError('Unselected module installed: ' + module)
        widgets = importlib.import_module(package + '.QtWidgets')
        app = widgets.QApplication([])
        widget = widgets.QWidget()
        widget.resize(80, 60)
        widget.setStyleSheet('background-color: rgb(17, 193, 53)')
        widget.show()
        app.processEvents()
        image = widget.grab().toImage()
        color = image.pixelColor(image.width() // 2, image.height() // 2)
        report['painted_pixel'] = [color.red(), color.green(), color.blue(), color.alpha()]
        if report['painted_pixel'] != [17, 193, 53, 255]:
            raise ValueError('Visible QWidget capture differs')
        widget.close()
        app.processEvents()
        app.quit()
        report['status'] = 'PASS_PROFILE_SMOKE'
    except BaseException as error:
        report['error'] = repr(error)
    output.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if report['status'] == 'PASS_PROFILE_SMOKE' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', choices=('pyqt5', 'pyqt6', 'pyside6'), required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.binding, args.manifest, args.bundle, args.output))
