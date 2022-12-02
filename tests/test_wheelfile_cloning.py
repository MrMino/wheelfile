import io
import os
import sys
import pytest

from wheelfile import WheelFile, __version__, MetaData
from pathlib import Path

from packaging.version import Version

if sys.version_info >= (3, 8):
    from zipfile import ZIP_DEFLATED, ZIP_BZIP2, ZIP_STORED, ZipInfo
else:
    from zipfile38 import ZIP_DEFLATED, ZIP_BZIP2, ZIP_STORED, ZipInfo

from .test_metas import TestMetadata as MetaDataTests


@pytest.fixture
def wf():
    buf = io.BytesIO()  # Cannot be the same as the one from buf fixture
    wf = WheelFile(buf, 'w',
                   distname='dist',
                   version='123', build_tag='321',
                   language_tag='lang', abi_tag='abi', platform_tag='win32',
                   compression=ZIP_STORED, compresslevel=1)
    yield wf
    wf.close()


class TestCloneInit:

    def test_returns_wheelfile(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        assert isinstance(cwf, WheelFile)

    def test_is_open_after_cloning(self, wf, buf):
        wf.close()
        cwf = WheelFile.from_wheelfile(wf, buf)
        assert cwf.closed is False

    def test_mode_is_set_to_w_by_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        assert cwf.mode == "w"

    @pytest.mark.parametrize("disallowed_mode", ['r', 'rl'])
    def test_read_mode_is_not_allowed(self, wf, buf, disallowed_mode):
        with pytest.raises(ValueError):
            WheelFile.from_wheelfile(wf, buf, mode=disallowed_mode)


class TestUnspecifiedArgs:

    def test_copies_distname(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.distname == wf.distname

    def test_copies_version(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.version == wf.version

    def test_copies_build_tag(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.version == wf.version

    def test_copies_language(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.language_tag == wf.language_tag

    def test_copies_abi(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.abi_tag == wf.abi_tag

    def test_copies_platform(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        cwf.platform_tag == wf.platform_tag

    def test_none_build_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       build_tag=None)
        assert cwf.build_tag is None

    def test_none_language_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       language_tag=None)
        assert cwf.language_tag == 'py3'

    def test_none_abi_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       abi_tag=None)
        assert cwf.abi_tag == 'none'

    def test_none_platform_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       platform_tag=None)
        assert cwf.platform_tag == 'any'


class TestZipFileRelatedArgs:

    # These tests are more or less the same tests as those in test_wheelfile.

    def test_passes_compression_arg_to_zipfile(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       compression=ZIP_BZIP2)
        assert cwf.zipfile.compression == ZIP_BZIP2

    def test_passes_allowzip64_arg_to_zipfile(self, wf, buf, tmp_file):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       allowZip64=False)
        # ZipFile.open trips when allowZip64 is forced in a zipfile that does
        # not allow it.
        #
        # Exception message:
        # "force_zip64 is True, but allowZip64 was False when opening the ZIP
        # file."
        with pytest.raises(ValueError, match="allowZip64 was False"):
            assert cwf.zipfile.open('file', mode='w', force_zip64=True)

    def test_passes_compresslevel_arg_to_init(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       compresslevel=7)
        assert cwf.zipfile.compresslevel == 7

    def test_passes_strict_timestamps_arg_to_zipfile(self, wf, buf, tmp_file):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0',
                                       strict_timestamps=False)
        # strict_timestamps will be propagated into ZipInfo objects created by
        # ZipFile.
        # Given very old timestamp, ZipInfo will set itself to 01-01-1980
        os.utime(tmp_file, (10000000, 100000000))
        cwf.write(tmp_file, resolve=False)
        zinfo = cwf.zipfile.getinfo(Path(*tmp_file.parts[1:]).as_posix())
        assert zinfo.date_time == (1980, 1, 1, 0, 0, 0)

    def test_when_not_given_uses_default_compression(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0')
        assert cwf.zipfile.compression == ZIP_DEFLATED

    def test_when_not_given_uses_default_allowzip64_flag(self, wf, buf,
                                                         tmp_file):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0')
        # ZipFile.open trips when allowZip64 is forced in a zipfile that does
        # not allow it. Here it should have allowZip64 == True, since True is
        # the zipfile.ZipFile default for this argument
        assert cwf.zipfile.open('file', mode='w', force_zip64=True)

    def test_when_not_given_uses_default_compresslevel(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0')
        assert cwf.zipfile.compresslevel is None

    def test_when_not_given_uses_default_timestamps_flag(self, wf, buf,
                                                         tmp_file):

        cwf = WheelFile.from_wheelfile(wf, buf, distname='_', version='0')
        # Given very old timestamp, if strict_timestamps=True (which is the
        # default of zipfile.ZipFile), writing a file with mtime before 1980
        # will raise a ValueError:
        #
        # "ValueError: ZIP does not support timestamps before 1980"
        #
        os.utime(tmp_file, (10000000, 100000000))
        with pytest.raises(ValueError, match="ZIP does not support timestamps"):
            cwf.write(tmp_file, resolve=False)


class TestCloneTypes:

    def test_buf_to_buf(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, buf)
        assert cwf.zipfile.fp is buf

    def test_buf_to_file_obj(self, wf, tmp_path):
        tmp_file = tmp_path / '_-0-py3-none-any.whl'
        with open(tmp_file, mode='bw+') as f:
            with WheelFile.from_wheelfile(wf, f) as cwf:
                assert cwf.zipfile.fp is f

    def test_buf_to_dir(self, wf, tmp_path):
        cwf = WheelFile.from_wheelfile(wf, tmp_path)
        expected_name = wf.filename
        assert cwf.filename == str(tmp_path / expected_name)

    def test_buf_to_path(self, wf, tmp_path):
        tmp_file = tmp_path / '_-0-py3-none-any.whl'
        cwf = WheelFile.from_wheelfile(wf, tmp_file)
        assert cwf.filename == str(tmp_file)

    def test_buf_to_buf_changed_tags(self, wf, buf):
        cwf = WheelFile.from_wheelfile(
            wf, buf,
            distname='copy', version='123', build_tag="321",
            language_tag="rustpy4", abi_tag="someabi2000",
            platform_tag="ibm500"
        )
        assert cwf.filename == "copy-123-321-rustpy4-someabi2000-ibm500.whl"


class TestRegularFilesCloning:

    def test_files_are_recreated(self, wf, buf):
        wf.writestr('file1', '')
        wf.writestr('file2', '')
        wf.writestr('file3', '')

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            assert cwf.namelist() == wf.namelist()

    def test_data_is_copied(self, wf, buf):
        archive = {'file1': b'data1', 'file2': b'data2', 'file3': b'data3'}

        for arcname, data in archive.items():
            wf.writestr(arcname, data)

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            for arcname, data in archive.items():
                assert cwf.zipfile.read(arcname) == data

    PRESERVED_ZIPINFO_ATTRS = ['date_time', 'compress_type', 'comment',
                               'extra', 'create_system', 'create_version',
                               'extract_version', 'flag_bits', 'volume',
                               'internal_attr', 'external_attr']

    def custom_zipinfo(self):
        zf = ZipInfo('file', date_time=(1984, 6, 8, 1, 2, 3))
        zf.compress_type = ZIP_BZIP2
        zf.comment = b"comment"
        zf.extra = b"extra"
        zf.create_system = 2
        zf.create_version = 21
        zf.extract_version = 19
        zf.flag_bits = 0o123
        zf.volume = 7
        zf.internal_attr = 123
        zf.external_attr = 321
        return zf

    @pytest.mark.parametrize("attr", PRESERVED_ZIPINFO_ATTRS)
    def test_zip_attributes_are_preserved_writestr(self, wf, buf, attr):
        zf = self.custom_zipinfo()
        wf.writestr(zf, b'data')

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            czf = cwf.infolist()[0]

        assert getattr(czf, attr) == getattr(zf, attr)

    @pytest.mark.xfail(reason="writestr_data does not propagate zinfo yet")
    @pytest.mark.parametrize("attr", PRESERVED_ZIPINFO_ATTRS)
    def test_zip_attributes_are_preserved_writestr_data(self, wf, buf, attr):
        zf = self.custom_zipinfo()
        wf.writestr_data('section', zf, b'data')

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            czf = cwf.infolist()[0]

        assert getattr(czf, attr) == getattr(zf, attr)

    # writestr_data does not propagate zinfo yet
    # skipped because it generates lots of warnings
    @pytest.mark.xfail(reason="writestr_distinfo does not propagate zinfo yet")
    @pytest.mark.parametrize("attr", PRESERVED_ZIPINFO_ATTRS)
    def test_zip_attributes_are_preserved_writestr_distinfo(self, wf, buf,
                                                            attr):
        zf = self.custom_zipinfo()
        wf.writestr_distinfo(zf, b'data')

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            czf = cwf.infolist()[0]

        assert getattr(czf, attr) == getattr(zf, attr)

    def test_data_directory_is_renamed(self, wf, buf):
        wf.writestr_data('section_xyz', 'file', b'data')

        with WheelFile.from_wheelfile(
            wf, buf, distname="new_distname", version="123"
        ) as cwf:
            assert cwf.namelist()[0] == 'new_distname-123.data/section_xyz/file'

    def test_dist_info_directory_is_renamed(self, wf, buf):
        wf.writestr_distinfo('file', b'data')

        with WheelFile.from_wheelfile(
            wf, buf, distname="new_distname", version="123"
        ) as cwf:
            assert cwf.namelist()[0] == 'new_distname-123.dist-info/file'


class TestMetadataCloning:

    def test_wheeldata_build_tag_is_kept_by_default(self, buf):
        buf1 = io.BytesIO()
        buf2 = io.BytesIO()
        wf = WheelFile(buf1, 'w', distname="_", version="0", build_tag=321)

        with WheelFile.from_wheelfile(
            wf, buf2, distname="new_distname", version="123"
        ) as cwf:
            assert cwf.wheeldata.build == 321

    # TODO: also implement tests for .tags
    # TODO: also implement tests for MetaData.distname and MetaData.version
    @pytest.mark.xfail(reason="Not implemented yet")
    def test_wheeldata_build_tag_is_kept_if_wf_changed(self, wf):
        buf1 = io.BytesIO()
        buf2 = io.BytesIO()
        with WheelFile(
            buf1, 'w', distname="_", version="0", build_tag=321
        ) as wf:
            wf.wheeldata.build = 12345

            with WheelFile.from_wheelfile(
                wf, buf2, distname="new_distname", version="123"
            ) as cwf:
                assert cwf.wheeldata.build == 12345

    def test_wheeldata_build_tag_is_not_kept_if_new_given(self, wf):
        buf1 = io.BytesIO()
        buf2 = io.BytesIO()
        wf = WheelFile(buf1, 'w', distname="_", version="0", build_tag=321)
        wf.wheeldata.build = 12345

        with WheelFile.from_wheelfile(
            wf, buf2, distname="new_distname", version="123", build_tag=999
        ) as cwf:
            assert cwf.wheeldata.build == 999

    def test_generator_is_marked_as_wheeldfile(self, wf, buf):
        wf.wheeldata.generator = "something else"

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            assert cwf.wheeldata.generator == "wheelfile " + __version__

    def test_explicit_tags_are_put_into_wheeldata(self, wf, buf):
        wf.wheeldata.tags = ["something-completely-different"]
        with WheelFile.from_wheelfile(
            wf, buf,
            language_tag="expected", abi_tag="expected", platform_tag="expected"
        ) as cwf:
            assert cwf.wheeldata.tags == ["expected-expected-expected"]

    # Fully customized MetaData args
    full_metadata = MetaDataTests.full_usage

    def test_metadata_stays_the_same(self, wf, buf, full_metadata):
        # ...apart from distname and version

        wf.metadata = MetaData(**full_metadata)

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            wf.metadata.name = cwf.distname
            wf.metadata.version = cwf.version
            assert cwf.metadata == wf.metadata

        # Get back the old values so that wf.validate doesn't complain
        wf.metadata.name = wf.distname
        wf.metadata.version = wf.version

    def test_metadata_gets_new_distname(self, wf, buf, full_metadata):
        wf.metadata = MetaData(**full_metadata)

        new_distname = "cloned_dist_123"
        with WheelFile.from_wheelfile(wf, buf, distname=new_distname) as cwf:
            assert cwf.metadata.name == new_distname

    def test_metadata_gets_new_version(self, wf, buf, full_metadata):
        wf.metadata = MetaData(**full_metadata)

        new_version = str(wf.version) + '+myversion'
        with WheelFile.from_wheelfile(wf, buf, version=new_version) as cwf:
            assert cwf.metadata.version == Version(new_version)

    def test_when_metadata_is_missing_uses_defaults(self, buf):
        with WheelFile(io.BytesIO(), 'w', distname='_', version='0') as wf:
            wf.wheeldata = None

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            assert str(cwf.metadata) == (
                'Metadata-Version: 2.1\n'
                'Name: _\n'
                'Version: 0\n\n'
            )

    def test_when_wheeldata_is_missing_uses_defaults(self, buf):
        with WheelFile(io.BytesIO(), 'w', distname='_', version='0') as wf:
            wf.wheeldata = None

            with WheelFile.from_wheelfile(wf, buf) as cwf:
                assert str(cwf.wheeldata) == (
                    'Wheel-Version: 1.0\n'
                    'Generator: wheelfile ' + __version__ + '\n'
                    'Root-Is-Purelib: true\n'
                    'Tag: py3-none-any\n\n'
                )

    def test_when_record_is_missing_recreates_it(self, wf, buf):
        wf.writestr("file", b'data')
        wf.record = None

        with WheelFile.from_wheelfile(wf, buf) as cwf:
            assert "file" in cwf.record


class TestNoOverwriting:
    def test_raises_VE_when_same_buf_used(self, wf):
        buf = wf.zipfile.fp
        with pytest.raises(ValueError):
            WheelFile.from_wheelfile(wf, buf)

    def test_raises_VE_when_same_fielobj_used(self, tmp_file):
        with open(tmp_file, 'bw+') as f:
            with WheelFile(f, mode='w') as wf:
                with pytest.raises(ValueError):
                    WheelFile.from_wheelfile(wf, f)

    def test_raises_VE_when_same_path_used(self, wf, buf, tmp_file):
        with WheelFile(tmp_file, mode='w') as wf:
            with pytest.raises(ValueError):
                WheelFile.from_wheelfile(wf, tmp_file)

    def test_raises_VE_when_same_path_used_relatively(self, wf, tmp_path):
        (tmp_path / 'relative/').mkdir()
        (tmp_path / 'path/').mkdir()
        path = (tmp_path / 'relative/../path/../')
        assert path.is_dir()
        with WheelFile(path, mode='w', distname='_', version='0') as wf:
            with pytest.raises(ValueError):
                WheelFile.from_wheelfile(wf, tmp_path)

    @pytest.fixture
    def tmp_cwd(self, tmp_path):
        old_dir = os.getcwd()
        os.chdir(tmp_path)
        yield tmp_path
        os.chdir(old_dir)

    def test_raises_VE_when_same_path_used_via_curdir(self, tmp_cwd):
        with WheelFile(tmp_cwd, mode='w', distname='_', version='0') as wf:
            with pytest.raises(ValueError):
                WheelFile.from_wheelfile(wf)
