import pytest

from wheelfile import WheelFile


@pytest.mark.filterwarnings("ignore:Lazy mode is not fully implemented yet.")
def test_lazy_mode_is_available(buf):
    WheelFile(buf, mode="wl", distname="dist", version="0")


class TestLazyModeRecord:

    @pytest.mark.skip
    def test_suppresses_record_containing_directory_entries(self):
        raise NotImplementedError
