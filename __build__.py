from wheelfile import WheelFile, __version__
from pathlib import Path

spec = {
    'distname': 'wheelfile',
    'version': __version__
}

requirements = Path('./requirements.txt').read_text().splitlines()

with WheelFile(mode='w', **spec) as wf:
    wf.metadata.requires_dists = requirements
    wf.metadata.requires_python = '>=3.6'

    wf.metadata.summary = "API for inspecting and creating .whl files"
    wf.metadata.description = Path('./README.md').read_text()
    wf.metadata.description_content_type = 'text/markdown'

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

    wf.metadata.author = "Błażej Michalik"
    wf.metadata.home_page = 'https://github.com/MrMino/wheelfile'

    wf.write('./wheelfile.py')

# 🧀
