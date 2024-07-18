import os

from wheelfile import resolved


def test_resolved_func(tmp_path):
    back = os.getcwd()
    os.chdir(tmp_path)

    assert resolved(os.curdir) == str(tmp_path.name)
    assert resolved(tmp_path) == str(tmp_path.name)
    assert resolved("dir/file") == "file"
    assert resolved("dir/../dir2/../file") == "file"

    os.chdir(back)
