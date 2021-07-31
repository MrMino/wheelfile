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
