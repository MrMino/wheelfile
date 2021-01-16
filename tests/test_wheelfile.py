import pytest

from wheelfile import WheelFile, UnnamedDistributionError, BadWheelFileError
from io import BytesIO
from packaging.version import Version
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


def test_can_work_on_in_memory_bufs(buf):
    wf = WheelFile(buf, 'w', distname='_', version='0')
    wf.close()
    assert buf.tell() != 0


class TestyWheelFileInit:

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

    def test_given_buf_and_no_distname_raises_unnamed_distribution(self, buf):
        with pytest.raises(UnnamedDistributionError):
            WheelFile(buf, 'w', version='0')

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
        buf.name = 'random_name'
        wf = WheelFile(buf, 'w', distname='_', version='0')
        assert wf.filename == 'random_name'

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

    def test_calling_close_twice_does_nothing(self, wf):
        wf.close()
        wf.close()

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

    @pytest.mark.xfail
    def test_writestr_writes_proper_path_to_record(self, wf):
        wf.writestr("/////this/should/be/stripped", "_")
        assert "this/should/be/stripped" in wf.record

    @pytest.fixture
    def tmp_file(self, tmp_path):
        fp = tmp_path / 'file'
        fp.touch()
        return fp

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
