import pytest


def test_allows_writing_record_files_in_subdirectories(wf):
    try:
        wf.writestr("some/subdir/.dist-info/RECORD", "additional record file")
    except Exception as exc:
        pytest.fail(
            f"Write failed, indicating inability to write RECORD in subdirs: {exc!r}"
        )
