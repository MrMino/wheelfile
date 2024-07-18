from pathlib import Path

import pytest

from wheelfile import WheelFile


@pytest.fixture
def empty_wheel(tmp_path) -> Path:
    with WheelFile(
        tmp_path, "w", distname="wheelfile_test_wheel", version="0.0.0"
    ) as wf:
        pass
    return wf


class TestWheelFileReadMode:
    def test_read_mode_is_the_default_one(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        assert wf.mode == "r"

    def test_close_in_read_mode_does_not_try_to_write(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        try:
            wf.close()
        except ValueError:  # ValueError: write() requires mode 'w', 'x', or 'a'
            pytest.fail("Attempt to write on close() in read mode")

    def test_reads_metadata(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        assert wf.metadata == empty_wheel.metadata

    def test_reads_wheeldata(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        assert wf.wheeldata == empty_wheel.wheeldata

    def test_reads_record(self, empty_wheel):
        wf = WheelFile(empty_wheel.filename)
        assert wf.record == empty_wheel.record
