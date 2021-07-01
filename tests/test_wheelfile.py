import pytest

import os
import sys

from functools import partial
from wheelfile import (
    WheelFile,
    UnnamedDistributionError,
    BadWheelFileError,
    ProhibitedWriteError
)
from io import BytesIO
from packaging.version import Version
from pathlib import Path

if sys.version_info >= (3, 8):
    from zipfile import ZipFile, ZipInfo, Path as ZipPath
else:
    from zipfile38 import ZipFile, ZipInfo, Path as ZipPath


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

    # This one fails because refresh_record() reads from the zipfile.
    # The only way it could work is if the record calculation is performed on
    # the data passed directly to the method, not from the zipfile.
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

    def test_default_language_tag_is_py3(self, wf):
        assert wf.language_tag == 'py3'

    def test_default_abi_tag_is_none(self, wf):
        assert wf.abi_tag == 'none'

    def test_default_platform_tag_is_any(self, wf):
        assert wf.platform_tag == 'any'

    def test_if_given_build_number_passes_it_to_wheeldata(self, buf):
        build_tag = 123
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       build_tag=build_tag)
        assert wf.wheeldata.build == build_tag

    def test_build_number_can_be_str(self, buf):
        build_tag = '123'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       build_tag=build_tag)
        assert wf.wheeldata.build == int(build_tag)

    def test_if_given_language_tag_passes_it_to_wheeldata_tags(self, buf):
        language_tag = 'ip2'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       language_tag=language_tag)
        assert wf.wheeldata.tags == ['ip2-none-any']

    def test_if_given_abi_tag_passes_it_to_wheeldata_tags(self, buf):
        abi_tag = 'cp38d'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       abi_tag=abi_tag)
        assert wf.wheeldata.tags == ['py3-cp38d-any']

    def test_if_given_platform_tag_passes_it_to_wheeldata_tags(self, buf):
        platform_tag = 'linux_x84_64'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       platform_tag=platform_tag)
        assert wf.wheeldata.tags == ['py3-none-linux_x84_64']

    def test_wheeldata_tag_defaults_to_py3_none_any(self, wf):
        assert wf.wheeldata.tags == ['py3-none-any']

    def test_can_be_given_version_as_int(self, buf):
        with pytest.raises(TypeError):
            WheelFile(buf, mode='w', distname='wheel', version=1)

    def test_given_an_int_version_raises_type_error_on_buf(self, tmp_path):
        with pytest.raises(TypeError):
            WheelFile(tmp_path, mode='w', distname='wheel', version=1)


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

    def test_given_build_tag_is_stored_in_build_tag_attr(self, buf):
        build_tag = 123
        wf = WheelFile(buf, 'w', distname='_', version='0', build_tag=build_tag)
        assert wf.build_tag == build_tag

    def test_given_str_build_tag_stores_int_in_build_tag_attr(self, buf):
        build_tag = '123'
        wf = WheelFile(buf, 'w', distname='_', version='0', build_tag=build_tag)
        assert wf.build_tag == int(build_tag)

    def test_given_language_tag_is_stored_in_language_tag_attr(self, buf):
        language_tag = 'cp3'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       language_tag=language_tag)
        assert wf.language_tag == language_tag

    def test_given_abi_tag_is_stored_in_abi_tag_attr(self, buf):
        abi_tag = 'abi3'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       abi_tag=abi_tag)
        assert wf.abi_tag == abi_tag

    def test_given_platform_tag_is_stored_in_abi_tag_attr(self, buf):
        platform_tag = 'win32'
        wf = WheelFile(buf, 'w', distname='_', version='0',
                       platform_tag=platform_tag)
        assert wf.platform_tag == platform_tag


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
        arc_file = ZipPath(wf.zipfile, str(tmp_file.name).lstrip('/'))

        assert arc_file.read_text() == tmp_file.read_text()

    def test_write_puts_files_at_arcname(self, wf, tmp_file):
        wf.write(tmp_file, arcname='arcname/path')
        assert 'arcname/path' in wf.zipfile.namelist()

    def test_write_writes_proper_path_to_record(self, wf, tmp_file):
        wf.write(tmp_file, "/////this/should/be/stripped")
        assert "this/should/be/stripped" in wf.record

    def test_writes_preserve_mtime(self, wf, tmp_file):
        tmp_file.touch()
        # 1600000000 is September 2020
        os.utime(tmp_file, (1600000000, 1600000000))

        wf.write(tmp_file, arcname='file')
        wf.zipfile.getinfo('file')

    def test_write_has_resolve_arg(self, wf, tmp_file):
        wf.write(tmp_file, resolve=True)

    def test_write_data_has_resolve_arg(self, wf, tmp_file):
        wf.write_data(tmp_file, section='test', resolve=True)

    @pytest.fixture
    def spaghetti_path(self, tmp_path):
        (tmp_path/'s'/'p'/'a'/'g'/'h'/'e'/'t'/'t'/'i').mkdir(parents=True)
        return tmp_path

    def test_write_resolves_paths(self, wf, spaghetti_path):
        path = (spaghetti_path / 's/p/a/g/h/e/t/t/i/../../../t/t/i/file')
        path.touch()
        wf.write(path, resolve=True)
        assert wf.zipfile.namelist() == ['file']

    def test_write_data_resolves_paths(self, wf, spaghetti_path):
        path = (spaghetti_path / 's/p/a/g/h/e/t/t/i/../../../t/t/i/file')
        path.touch()
        wf.write_data(path, 'section', resolve=True)
        data_path = wf.distname + '-' + str(wf.version) + '.data'
        assert wf.zipfile.namelist() == [data_path + '/section/file']

    def test_write_doesnt_resolve_when_given_arcname(self, wf, tmp_file):
        wf.write(tmp_file, arcname='not_resolved', resolve=True)
        assert wf.zipfile.namelist() == ['not_resolved']

    def test_write_data_doesnt_resolve_when_given_arcname(self, wf, tmp_file):
        wf.write_data(tmp_file, 'section', arcname='not_resolved', resolve=True)
        data_path = wf.distname + '-' + str(wf.version) + '.data'
        assert wf.zipfile.namelist() == [data_path + '/section/not_resolved']

    def test_write_distinfo_writes_to_the_right_arcname(self, wf, tmp_file):
        wf.write_distinfo(tmp_file)
        di_arcpath = wf.distname + '-' + str(wf.version) + '.dist-info'
        assert wf.zipfile.namelist() == [di_arcpath + '/' + tmp_file.name]

    def test_write_distinfo_resolve_arg(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, resolve=False)
        di_arcpath = wf.distname + '-' + str(wf.version) + '.dist-info'
        assert wf.zipfile.namelist() == [di_arcpath + str(tmp_file)]

    def test_write_distinfo_recursive(self, wf, tmp_path):
        (tmp_path / 'file').touch()
        wf.write_distinfo(tmp_path, recursive=True)
        di_arcpath = wf.distname + '-' + str(wf.version) + '.dist-info'
        assert set(wf.zipfile.namelist()) == {
            di_arcpath + '/' + tmp_path.name + '/',
            di_arcpath + '/' + tmp_path.name + '/file'
        }

    def test_write_distinfo_non_recursive(self, wf, tmp_path):
        (tmp_path / 'file').touch()
        wf.write_distinfo(tmp_path, recursive=False)
        di_arcpath = wf.distname + '-' + str(wf.version) + '.dist-info'
        assert wf.zipfile.namelist() == [di_arcpath + '/' + tmp_path.name + '/']

    def test_write_distinfo_arcpath(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, arcname='custom_filename')
        di_arcpath = wf.distname + '-' + str(wf.version) + '.dist-info'
        assert wf.zipfile.namelist() == [di_arcpath + '/custom_filename']

    @pytest.mark.parametrize('filename', ('WHEEL', 'METADATA', 'RECORD'))
    def test_write_distinfo_doesnt_permit_writing_metadata(self, wf,
                                                           tmp_path, filename):
        (tmp_path/filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.write_distinfo(tmp_path/filename)

    def test_write_distinfo_doesnt_permit_empty_arcname(self, wf, tmp_file):
        with pytest.raises(ProhibitedWriteError):
            wf.write_distinfo(tmp_file, arcname='')

    @pytest.mark.xfail
    def test_write_distinfo_doesnt_permit_backing_out(self, wf, tmp_file):
        with pytest.raises(ValueError):
            wf.write_distinfo(tmp_file, arcname='../file')

    @pytest.mark.xfail
    @pytest.mark.parametrize('filename', ('WHEEL', 'METADATA', 'RECORD'))
    def test_write_doesnt_permit_writing_metadata(self, wf, tmp_path, filename):
        (tmp_path/filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.write(tmp_path/filename)

    @pytest.mark.xfail
    @pytest.mark.parametrize('filename', ('WHEEL', 'METADATA', 'RECORD'))
    def test_writestr_doesnt_permit_writing_metadata(self, wf, tmp_path,
                                                     filename):
        (tmp_path/filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.writestr(tmp_path/filename, b'')

    @pytest.mark.xfail
    def test_writestr_distinfo(self, wf):
        wf.writestr_distinfo()

    @pytest.mark.xfail
    @pytest.mark.parametrize('filename', ('WHEEL', 'METADATA', 'RECORD'))
    def test_writestr_distinfo_doesnt_permit_writing_metadata(
        self, wf, tmp_path, filename
    ):
        (tmp_path/filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.writestr(tmp_path/filename, b'')


def named_bytesio(name: str) -> BytesIO:
    bio = BytesIO()
    bio.name = str(name)
    return bio


rwb_open = partial(open, mode='wb+')


# TODO: when lazy mode is ready, test arguments priority over inference
# TODO: when lazy mode is ready, test build number degeneration
# TODO: when lazy mode is ready, test version degeneration
@pytest.mark.parametrize("target_type", [str, Path, rwb_open, named_bytesio])
class TestWheelFileAttributeInference:
    """Tests how WheelFile infers metadata from the name of its target file"""

    def test_infers_from_given_path(self, tmp_path, target_type):
        path = target_type(
            tmp_path / "my_awesome.wheel-4.2.0-py38-cp38d-linux_x84_64.whl"
        )
        wf = WheelFile(path, 'w')
        assert (wf.distname == "my_awesome.wheel"
                and str(wf.version) == '4.2.0'
                and wf.language_tag == 'py38'
                and wf.abi_tag == 'cp38d'
                and wf.platform_tag == 'linux_x84_64')

    def test_infers_from_given_path_with_build_tag(self, tmp_path, target_type):
        path = target_type(
            tmp_path / "my_awesome.wheel-1.2.3.dev0-5-ip37-cp38d-win32.whl"
        )
        wf = WheelFile(path, 'w')
        assert (wf.distname == "my_awesome.wheel"
                and str(wf.version) == '1.2.3.dev0'
                and wf.build_tag == 5
                and wf.language_tag == 'ip37'
                and wf.abi_tag == 'cp38d'
                and wf.platform_tag == 'win32')

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


class TestWheelFileDirectoryTarget:
    """Tests how WheelFile.__init__() behaves when given a directory"""

    def test_if_version_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, 'w', distname='my_dist')

    def test_if_distname_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, 'w', version='0')

    def test_given_directory_and_all_args__sets_filename(self, tmp_path):
        with WheelFile(
            tmp_path, 'w', distname='my_dist', version='1.0.0'
        ) as wf:
            expected_name = '-'.join((wf.distname,
                                      str(wf.version),
                                      wf.language_tag,
                                      wf.abi_tag,
                                      wf.platform_tag)) + '.whl'
            assert wf.filename == str(tmp_path / expected_name)

    def test_given_no_target_assumes_curdir(self, tmp_path):
        old_path = Path.cwd()
        os.chdir(tmp_path)
        with WheelFile(
            mode='w', distname='my_dist', version='1.0.0'
        ) as wf:
            expected_name = '-'.join((wf.distname,
                                      str(wf.version),
                                      wf.language_tag,
                                      wf.abi_tag,
                                      wf.platform_tag)) + '.whl'
            assert wf.filename == str(Path('./') / expected_name)
        os.chdir(old_path)

    def test_given_no_target_creates_file_from_args(self, tmp_path):
        old_path = Path.cwd()
        os.chdir(tmp_path)
        with WheelFile(
            mode='w', distname='my_dist', version='1.2.alpha1', build_tag=123,
            language_tag='jp2', abi_tag='jre8', platform_tag='win32'
        ) as wf:
            expected_name = 'my_dist-1.2a1-123-jp2-jre8-win32.whl'
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

    def test_mode_is_written_to_mode_attribute(self, wf):
        assert wf.mode == 'w'


class TestWheelFileRecursiveWrite:
    def test_write_has_recursive_arg(self, wf, tmp_path):
        wf.write(tmp_path, recursive=True)

    def test_recursive_write_does_not_break_on_files(self, wf, tmp_file):
        wf.write(tmp_file, recursive=True)

    def test_write_data_has_recursive_arg(self, wf, tmp_path):
        wf.write_data(tmp_path, 'section', recursive=True)

    def test_recursive_write_data_does_not_break_on_files(self, wf, tmp_file):
        wf.write_data(tmp_file, 'section', recursive=True)

    @pytest.fixture
    def path_tree(self, tmp_path):
        """The directory tree root is the first item in the list."""
        d = tmp_path
        tree = [
            d / 'file',
            d / 'empty_dir' / '',

            d / 'dir_a' / '',
            d / 'dir_a' / 'subdir_a',
            d / 'dir_a' / 'subdir_a' / '1_file',
            d / 'dir_a' / 'subdir_a' / '2_file',

            d / 'dir_b',
            d / 'dir_b' / 'subdir_b_1' / '',
            d / 'dir_b' / 'subdir_b_1' / 'file',
            d / 'dir_b' / 'subdir_b_2' / '',
            d / 'dir_b' / 'subdir_b_2' / 'file',
        ]

        for path in tree:
            if path.stem.endswith('file'):
                path.write_text('contents')
            else:
                path.mkdir()

        tree = [d] + tree

        return [str(p) + '/' if p.is_dir() else str(p) for p in tree]

    def test_write_recursive_writes_all_files_in_the_tree(self, wf, path_tree):
        directory = path_tree[0]
        wf.write(directory, recursive=True, resolve=False)
        expected_tree = [pth.lstrip('/') for pth in path_tree]
        assert set(wf.zipfile.namelist()) == set(expected_tree)

    def test_write_recursive_writes_with_proper_arcname(self, wf, path_tree):
        directory = path_tree[0]
        custom_arcname = "something/different"
        wf.write(directory, arcname=custom_arcname, recursive=True)
        assert all(
            path.startswith(custom_arcname) for path in wf.zipfile.namelist()
        )

    def test_write_data_writes_recursively_when_asked(self, wf, path_tree):
        directory = path_tree[0]
        directory_name = os.path.basename(directory.rstrip('/'))
        archive_root = '_-0.data/test/' + directory_name + '/'

        wf.write_data(directory, section="test", recursive=True)

        expected_tree = [archive_root + pth[len(directory):]
                         for pth in path_tree]
        assert set(wf.zipfile.namelist()) == set(expected_tree)

    def test_write_data_writes_non_recursively_when_asked(self, wf, path_tree):
        directory = path_tree[0]
        directory_name = os.path.basename(directory.rstrip('/'))
        archive_root = '_-0.data/test/' + directory_name + '/'

        wf.write_data(directory, section="test", recursive=False)

        expected_tree = [archive_root]
        assert wf.zipfile.namelist() == expected_tree
