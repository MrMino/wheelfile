import pytest

from io import BytesIO

from wheelfile import WheelFile


@pytest.fixture
def buf():
    return BytesIO()


@pytest.fixture
def wf(buf):
    wf = WheelFile(buf, 'w', distname='_', version='0')
    yield wf
    wf.close()


@pytest.fixture
def tmp_file(tmp_path):
    fp = tmp_path / 'wheel-0-py3-none-any.whl'
    fp.touch()
    return fp
