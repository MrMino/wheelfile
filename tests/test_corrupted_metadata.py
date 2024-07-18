from wheelfile import WheelFile


def test_when_metadata_is_corrupted_sets_metadata_to_none(buf):
    wf = WheelFile(buf, distname="_", version="0", mode="w")
    wf.metadata = "This is not a valid metadata"  # type: ignore
    wf.close()

    with WheelFile(buf, distname="_", version="0", mode="rl") as broken_wf:
        assert broken_wf.metadata is None


def test_when_wheeldata_is_corrupted_sets_wheeldata_to_none(buf):
    wf = WheelFile(buf, distname="_", version="0", mode="w")
    wf.wheeldata = "This is not a valid wheeldata"  # type: ignore
    wf.close()

    with WheelFile(buf, distname="_", version="0", mode="rl") as broken_wf:
        assert broken_wf.wheeldata is None


def test_wheeldata_is_read_even_if_metadata_corrupted(buf):
    wf = WheelFile(buf, distname="_", version="0", mode="w")
    wf.metadata = "This is not a valid metadata"  # type: ignore
    wf.close()

    with WheelFile(buf, distname="_", version="0", mode="rl") as broken_wf:
        assert broken_wf.wheeldata is not None


def test_metadata_is_read_even_if_wheeldata_corrupted(buf):
    wf = WheelFile(buf, distname="_", version="0", mode="w")
    wf.wheeldata = "This is not a valid wheeldata"  # type: ignore
    wf.close()

    with WheelFile(buf, distname="_", version="0", mode="rl") as broken_wf:
        assert broken_wf.metadata is not None
