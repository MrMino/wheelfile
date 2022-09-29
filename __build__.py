import tarfile
from pathlib import Path
from typing import Any, Dict, Optional

import toml
from wheelfile import WheelFile


def get_config() -> Dict[str, Any]:
    """Read pyproject.toml"""
    project_config = toml.load('pyproject.toml')
    config = project_config['project']
    return config


def build_sdist(
    sdist_directory: str, config_settings: Dict[str, Any] = None
) -> str:
    config = get_config()
    name = config['name']
    version = config['version']
    distname = f'{name}-{version}'
    filename = f'{distname}.tar.gz'
    filepath = Path(sdist_directory) / filename

    with tarfile.open(filepath, 'w:gz', format=tarfile.PAX_FORMAT) as sdist:
        sdist.add('./', arcname=distname, filter=None)
        return filename


def build_wheel(
    wheel_directory: str,
    config_settings: Optional[Dict[str, Any]] = None,
    metadata_directory: Optional[str] = None
) -> str:
    config = get_config()

    # For WheelFile.__init__
    # Platform, abi, and language tags stay as defaults: "py3-none-any"
    spec: Dict[str, Any] = {
        'distname': config['name'],
        'version': config['version']
    }

    # Open a new wheel file
    with WheelFile(mode='w', **spec) as wf:
        # Add requirements to the metadata
        wf.metadata.requires_dists = config['dependencies']
        # We target Python 3.6+ only
        wf.metadata.requires_python = config['requires-python']

        # Make sure PyPI page renders nicely
        wf.metadata.summary = config['description']
        wf.metadata.description = Path(config['readme']).read_text()
        wf.metadata.description_content_type = 'text/markdown'

        # Keywords and trove classifiers, for better searchability
        wf.metadata.keywords = config['keywords']
        wf.metadata.classifiers = config['classifiers']

        # Let the world know who is responsible for this
        wf.metadata.author = config['authors'][0]['name']
        wf.metadata.home_page = config['urls']['repository']

        # Add the code - it will install inside site-packages/wheelfile.py
        wf.write('./wheelfile.py')
        return wf.filename

# Done!
# 🧀
