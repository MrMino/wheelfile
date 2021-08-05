from wheelfile import WheelFile, __version__
from pathlib import Path
from typing import Dict, Any

# For WheelFile.__init__
# Platform, abi, and language tags stay as defaults: "py3-none-any"
spec: Dict[str, Any] = {
    'distname': 'wheelfile',
    'version': __version__
}

# Fetch requirements into a list of strings
requirements = Path('./requirements.txt').read_text().splitlines()

# Open a new wheel file
with WheelFile(mode='w', **spec) as wf:
    # Add requirements to the metadata
    wf.metadata.requires_dists = requirements
    # We target Python 3.6+ only
    wf.metadata.requires_python = '>=3.6'

    # Make sure PyPI page renders nicely
    wf.metadata.summary = "API for inspecting and creating .whl files"
    wf.metadata.description = Path('./README.md').read_text()
    wf.metadata.description_content_type = 'text/markdown'

    # Keywords and trove classifiers, for better searchability
    wf.metadata.keywords = ['wheel', 'packaging', 'pip', 'build', 'distutils']
    wf.metadata.classifiers = [
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Archiving :: Packaging',
        'Topic :: System :: Software Distribution',
        'Topic :: Utilities',
    ]

    # Let the world know who is responsible for this
    wf.metadata.author = "Błażej Michalik"
    wf.metadata.home_page = 'https://github.com/MrMino/wheelfile'

    # Add the code - it will install inside site-packages/wheelfile.py
    wf.write('./wheelfile.py')

# Done!
# 🧀
