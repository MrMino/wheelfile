import toml
import tarfile
from pathlib import Path
from wheelfile import WheelFile


def get_config(cls):
    """Read pyproject.toml"""
    project_config = toml.load('pyproject.toml')
    config = project_config['tool']['pep_517_example']
    return config


# See https://www.python.org/dev/peps/pep-0517/#get-requires-for-build-wheel
def get_requires_for_build_wheel(cls, config_settings):
    return []


# See https://www.python.org/dev/peps/pep-0517/#build-sdist
def build_sdist(sdist_directory, config_settings=None):
    config = get_config()
    distname = config['name']
    version = config['version']

    with tarfile.open(
        f'{distname}-{version}.tar.gz', 'w:gz', format=tarfile.PAX_FORMAT
    ) as sdist:
        sdist.add('./')


# See https://www.python.org/dev/peps/pep-0517/#build-wheel
def build_wheel(wheel_directory,
                config_settings=None, metadata_directory=None):
    config = get_config()

    maintainers = config['maintainers']
    if isinstance(maintainers, list):
        maintainers = ', '.join(maintainers)

    maintainers_emails = config['maintainers_emails']
    if isinstance(maintainers_emails, list):
        maintainers_emails = ', '.join(config['maintainers_emails'])

    requirements = Path('requirements.txt').read_text().splitlines()

    spec = {
        'distname': config['name'],
        'version': config['version'],
    }

    with WheelFile(wheel_directory, 'w', **spec) as wf:
        wf.metadata.maintainer = maintainers
        wf.metadata.maintainer_email = maintainers_emails
        wf.metadata.requires_dists = requirements

        wf.write('src/')

    return wf.filename  # 🧀
