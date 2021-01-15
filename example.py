"""
Wheelfile: example usage.

We heard you like wheelfiles...

The script below uses wheelfile module to build a wheel for it. It assumes that
it itself is inside the root of wheelfile repository.
"""
from pathlib import Path

from wheelfile import WheelFile, __version__ as wheelfile_version
from packaging.requirements import Requirement


def buildme():
    repo_root = Path(__file__).parent
    requirements = []
    with open(repo_root / 'requirements.txt') as f:
        for line in f.readlines():
            requirements.append(Requirement(line))

    whl_name = f'wheelfile-{wheelfile_version}-py3-none-any.whl'
    with WheelFile(repo_root / whl_name, 'w') as wf:
        wf.write(repo_root / 'wheelfile.py')
        for r in requirements:
            wf.metadata.requires_dists.append(str(r))


if __name__ == '__main__':
    buildme()
