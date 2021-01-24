import pytest

from wheelfile import WheelFile

from pathlib import Path


@pytest.fixture
def empty_wheel(tmp_path) -> Path:
    with WheelFile(tmp_path, 'w',
                   distname='wheelfile_test_wheel', version='0.0.0') as wf:
        pass
    return wf


class TestWheelFileReadMode:

    def test_close_in_read_mode_does_not_try_to_write(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        try:
            wf.close()
        except ValueError:  # ValueError: write() requires mode 'w', 'x', or 'a'
            pytest.fail("Attempt to write on close() in read mode")
