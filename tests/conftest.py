import pytest

from io import BytesIO


@pytest.fixture
def buf():
    return BytesIO()
