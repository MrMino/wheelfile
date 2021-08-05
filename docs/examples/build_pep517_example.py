import pathlib
from wheelfile import WheelFile


main = """
import subprocess, os, platform
import pathlib

if __name__ == '__main__':
    filepath = pathlib.Path(__file__).parent / 'builder.py'
    if platform.system() == 'Darwin':
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':
        os.startfile(filepath)
    else:
        subprocess.call(('xdg-open', filepath))
"""

with WheelFile(mode='w', distname='pep_517_example', version='1') as wf:
    wf.metadata.requires_dists = ['wheelfile']
    wf.metadata.summary = "Example of PEP-517 builder that uses wheelfile"
    wf.metadata.description = (
        "See "
        "https://wheelfile.readthedocs.io/en/latest/"
        "examples/pep-517-builder.html"
    )
    wf.metadata.description_content_type = 'text/markdown'
    wf.metadata.keywords = ['wheel', 'packaging', 'pip', 'build', 'pep-517']
    wf.metadata.classifiers = [
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ]
    wf.metadata.author = "Błażej Michalik"
    wf.metadata.home_page = 'https://github.com/MrMino/wheelfile'

    wf.write(pathlib.Path(__file__).parent / './pep_517_builder.py',
             'pep_517_example/builder.py')
    wf.writestr('pep_517_example/__main__.py', main)

# 🧀
