import pytest

import os

from functools import partial
from wheelfile import WheelFile, UnnamedDistributionError, BadWheelFileError
from io import BytesIO
from packaging.version import Version
from pathlib import Path
from zipfile import ZipFile, Path as ZipPath, ZipInfo


def test_UnnamedDistributionError_is_BadWheelFileError():
    assert issubclass(UnnamedDistributionError, BadWheelFileError)


def test_BadWheelFileError_is_ValueError():
    assert issubclass(BadWheelFileError, ValueError)


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


def test_can_work_on_in_memory_bufs(buf):
    wf = WheelFile(buf, 'w', distname='_', version='0')
    wf.close()
    assert buf.tell() != 0


class TestyWheelFileInit:
    def empty_wheel_bytes(self, name, version):
        buf = BytesIO()
        with WheelFile(buf, 'w', name, version):
            pass

    @pytest.fixture
    def real_path(self, tmp_path):
        return tmp_path / 'test-0-py2.py3-none-any.whl'

    def test_target_can_be_pathlib_path(self, real_path):
        WheelFile(real_path, 'w').close()

    def test_target_can_be_str_path(self, real_path):
        path = str(real_path)
        WheelFile(path, 'w').close()

    def test_target_can_be_binary_rwb_file_obj(self, real_path):
        file_obj = open(real_path, 'wb+')
        WheelFile(file_obj, 'w').close()

    @pytest.mark.skip  # Because WheelFile.__del__ shows tb
    @pytest.mark.xfail
    def test_target_can_be_binary_wb_file_obj(self, real_path):
        file_obj = open(real_path, 'wb')
        WheelFile(file_obj, 'w').close()

    def test_on_bufs_x_mode_behaves_same_as_w(self):
        f1, f2 = BytesIO(), BytesIO()
        wf1 = WheelFile(f1, 'w', distname='_', version='0')
        wf1.close()
        wf2 = WheelFile(f2, 'w', distname='_', version='0')
        wf2.close()

        assert f1.getvalue() == f2.getvalue()

    def test_metadata_is_created(self, wf):
        assert wf.metadata is not None

    def test_created_metadata_contains_given_name(self, buf):
        wf = WheelFile(buf, 'w', distname='given_name', version='0')
        assert wf.metadata.name == 'given_name'

    def test_created_metadata_contains_given_version(self, buf):
        v = Version('1.2.3.4.5')
        wf = WheelFile(buf, 'w', distname='_', version=v)
        assert wf.metadata.version == v

    def test_wheeldata_is_created(self, wf):
        assert wf.wheeldata is not None

    def test_record_is_created(self, wf):
        assert wf.record is not None

    def test_record_is_empty_after_creation(self, wf):
        assert str(wf.record) == ''

    def test_if_given_empty_distname_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, 'w', distname='', version='0')

    def test_if_given_distname_with_wrong_chars_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, 'w', distname='!@#%^&*', version='0')

    def test_wont_raise_on_distname_with_periods_and_underscores(self, buf):
        try:
            WheelFile(buf, 'w', distname='_._._._', version='0')
        except ValueError:
            pytest.fail("Raised unexpectedly.")

    def test_if_given_empty_version_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, 'w', distname='_', version='')

    def test_if_given_bogus_version_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, 'w', distname='_', version='BOGUS')


class TestWheelFileAttributes:

    def test_zipfile_attribute_returns_ZipFile(self, buf, wf):
        assert isinstance(wf.zipfile, ZipFile)

    def test_zipfile_attribute_is_read_only(self, buf):
        with pytest.raises(AttributeError):
            WheelFile(buf, 'w', distname='_', version='0').zipfile = None

    def test_object_under_zipfile_uses_given_buf(self, wf, buf):
        assert wf.zipfile.fp is buf

    def test_filename_returns_buf_name(self, buf):
        buf.name = 'random_name-0-py3-none-any.whl'
        wf = WheelFile(buf, 'w', distname='_', version='0')
        assert wf.filename == buf.name

    def test_given_distname_is_stored_in_distname_attr(self, buf):
        distname = 'random_name'
        wf = WheelFile(buf, 'w', distname=distname, version='0')
        assert wf.distname == distname

    def test_given_version_is_stored_in_version_attr(self, buf):
        version = Version('1.2.3')
        wf = WheelFile(buf, 'w', distname='_', version=version)
        assert wf.version == version


class TestWheelFileClose:

    def test_closes_wheelfiles_zipfile(self, wf):
        wf.close()
        assert wf.zipfile.fp is None

    def test_adds_metadata_to_record(self, wf):
        wf.close()
        assert '_-0.dist-info/METADATA' in wf.record

    def test_adds_wheeldata_to_record(self, wf):
        wf.close()
        assert '_-0.dist-info/WHEEL' in wf.record

    def test_sets_closed(self, wf):
        assert not wf.closed
        wf.close()
        assert wf.closed

    def test_gets_called_on_del(self, wf):
        zf = wf.zipfile
        wf.__del__()
        assert zf.fp is None

    def test_calling_close_second_time_nothing(self, wf):
        wf.close()
        assert wf.closed
        wf.close()
        assert wf.closed

    @pytest.mark.xfail
    def test_refreshes_record(self, wf):
        path = 'unrecorded/file/in/wheel'
        wf.zipfile.writestr(path, "_")
        assert path not in wf.record
        wf.close()
        assert path in wf.record


class TestWheelFileContext:

    def test_is_not_closed_after_entry(self, buf):
        with WheelFile(buf, 'w', distname='_', version='0') as wf:
            assert not wf.closed

    def test_is_closed_after_exit(self, buf):
        with WheelFile(buf, 'w', distname='_', version='0') as wf:
            pass
        assert wf.closed


class TestWheelFileWrites:

    @pytest.fixture
    def arcpath(self, wf):
        path = '/some/archive/path'
        return ZipPath(wf.zipfile, path)

    def test_writestr_writes_text(self, wf, arcpath):
        text = "Random text."
        wf.writestr(arcpath.at, text)
        assert arcpath.read_text() == text

    def test_writestr_writes_bytes(self, wf, arcpath):
        bytestr = b'random bytestr'
        wf.writestr(arcpath.at, bytestr)
        assert arcpath.read_bytes() == bytestr

    def test_writestr_written_file_to_record(self, wf, arcpath):
        assert arcpath.at not in wf.record
        wf.writestr(arcpath.at, "_")
        assert arcpath.at in wf.record

    def test_writestr_can_take_zipinfo(self, wf, arcpath):
        zi = ZipInfo(arcpath.at)
        wf.writestr(zi, "_")
        assert wf.zipfile.getinfo(arcpath.at) == zi

    def test_writestr_writes_path_to_record_as_is(self, wf):
        wf.writestr("/////this/should/be/stripped", "_")
        assert "/////this/should/be/stripped" in wf.record

    def test_write_adds_file_to_archive(self, wf, tmp_file):
        tmp_file.write_text("contents")
        wf.write(tmp_file)
        arc_file = ZipPath(wf.zipfile, str(tmp_file).lstrip('/'))

        assert arc_file.read_text() == tmp_file.read_text()

    def test_write_puts_files_at_arcname(self, wf, tmp_file):
        wf.write(tmp_file, arcname='arcname/path')
        assert 'arcname/path' in wf.zipfile.namelist()

    def test_write_writes_proper_path_to_record(self, wf, tmp_file):
        wf.write(tmp_file, "/////this/should/be/stripped")
        assert "this/should/be/stripped" in wf.record


def named_bytesio(name: str) -> BytesIO:
    bio = BytesIO()
    bio.name = str(name)
    return bio


rwb_open = partial(open, mode='wb+')


@pytest.mark.parametrize("target_type", [str, Path, rwb_open, named_bytesio])
class TestWheelFileAttributeInference:
    """Tests how WheelFile infers metadata from the name of its target file"""

    def test_infers_from_given_path(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel-4.2.0-py3-none-any.whl")
        wf = WheelFile(path, 'w')
        assert wf.distname == "my_awesome.wheel" and str(wf.version) == '4.2.0'

    def test_if_distname_part_is_empty_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "-4.2.0-py3-none-any.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, 'w')

    def test_if_given_distname_only_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, 'w')

    def test_if_version_part_is_empty_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel--py3-none-any.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, 'w')

    def test_if_bad_chars_in_distname_raises_VE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_@wesome.wheel-4.2.0-py3-none-any.whl")
        with pytest.raises(ValueError):
            WheelFile(path, 'w')

    def test_if_invalid_version_raises_VE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel-nice-py3-none-any.whl")
        with pytest.raises(ValueError):
            WheelFile(path, 'w')


def test_given_unnamed_buf_and_no_distname_raises_UDE(buf):
    with pytest.raises(UnnamedDistributionError):
        WheelFile(buf, 'w', version='0')


def test_given_unnamed_buf_and_no_version_raises_UDE(buf):
    with pytest.raises(UnnamedDistributionError):
        WheelFile(buf, 'w', distname='_')


# TODO: as soon as there are __init__ args for the name segments, make sure
# theres a single test for "missing arg" situation.
# TODO: tag arguments will be optional - test it
class TestWheelFileDirectoryTarget:
    """Tests how WheelFile.__init__() behaves when given a directory"""

    def test_if_version_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, 'w', distname='my_dist')

    def test_if_distname_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, 'w', version='0')

    def test_given_directory_and_all_args__sets_filename(self, tmp_path):
        expected_name = 'my_dist-1.0.0-py3-none-any.whl'
        with WheelFile(
            tmp_path, 'w', distname='my_dist', version='1.0.0'
        ) as wf:
            # XXX: all tags are hardcoded for now
            assert wf.filename == str(tmp_path / expected_name)

    def test_given_no_target_assumes_curdir(self, tmp_path):
        expected_name = 'my_dist-1.0.0-py3-none-any.whl'
        old_path = Path.cwd()
        os.chdir(tmp_path)
        with WheelFile(
            mode='w', distname='my_dist', version='1.0.0'
        ) as wf:
            # XXX: all tags are hardcoded for now
            assert wf.filename == str(Path('./') / expected_name)
        os.chdir(old_path)


class TestWheelFileDistDataWrite:

    def test_write__if_section_is_empty_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.write_data('_', '')

    def test_write__if_section_contains_slashes_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.write_data('_', 'section/path/')

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_write__writes_given_str_path(self, wf, tmp_file, path_type):
        contents = "Contents of the file to write"
        expected_arcpath = f'_-0.data/section/{tmp_file.name}'
        tmp_file.write_text(contents)
        wf.write_data(path_type(tmp_file), 'section')

        assert wf.zipfile.read(expected_arcpath) == tmp_file.read_bytes()

    def test_writestr__if_section_is_empty_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.writestr_data('', '_', b'data')

    def test_writestr__if_section_contains_slashes_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.writestr_data('section/path/', '_', 'data')

    def test_writestr__writes_given_str_path(self, wf):
        contents = b"Contents of to write"
        filename = "file"
        expected_arcpath = f'_-0.data/section/{filename}'
        wf.writestr_data('section', filename, contents)

        assert wf.zipfile.read(expected_arcpath) == contents
