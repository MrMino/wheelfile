import os
from functools import partial
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_BZIP2, ZIP_DEFLATED, ZIP_STORED
from zipfile import Path as ZipPath
from zipfile import ZipFile, ZipInfo

import pytest
from packaging.version import Version

from wheelfile import (
    BadWheelFileError,
    ProhibitedWriteError,
    UnnamedDistributionError,
    WheelFile,
)


def test_UnnamedDistributionError_is_BadWheelFileError():
    assert issubclass(UnnamedDistributionError, BadWheelFileError)


def test_BadWheelFileError_is_ValueError():
    assert issubclass(BadWheelFileError, ValueError)


def test_can_work_on_in_memory_bufs(buf):
    wf = WheelFile(buf, "w", distname="_", version="0")
    wf.close()
    assert buf.tell() != 0


class TestWheelFileInit:

    def empty_wheel_bytes(self, name, version):
        buf = BytesIO()
        with WheelFile(buf, "w", name, version):
            pass

    @pytest.fixture
    def real_path(self, tmp_path):
        return tmp_path / "test-0-py2.py3-none-any.whl"

    def test_target_can_be_pathlib_path(self, real_path):
        WheelFile(real_path, "w").close()

    def test_target_can_be_str_path(self, real_path):
        path = str(real_path)
        WheelFile(path, "w").close()

    def test_target_can_be_binary_rwb_file_obj(self, real_path):
        file_obj = open(real_path, "wb+")
        WheelFile(file_obj, "w").close()

    # This one fails because refresh_record() reads from the zipfile.
    # The only way it could work is if the record calculation is performed on
    # the data passed directly to the method, not from the zipfile.
    @pytest.mark.skip  # Because WheelFile.__del__ shows tb
    @pytest.mark.xfail
    def test_target_can_be_binary_wb_file_obj(self, real_path):
        file_obj = open(real_path, "wb")
        WheelFile(file_obj, "w").close()

    def test_on_bufs_x_mode_behaves_same_as_w(self):
        f1, f2 = BytesIO(), BytesIO()
        wf1 = WheelFile(f1, "x", distname="_", version="0")
        wf1.close()
        wf2 = WheelFile(f2, "w", distname="_", version="0")
        wf2.close()

        assert f1.getvalue() == f2.getvalue()

    def test_metadata_is_created(self, wf):
        assert wf.metadata is not None

    def test_created_metadata_contains_given_name(self, buf):
        wf = WheelFile(buf, "w", distname="given_name", version="0")
        assert wf.metadata.name == "given_name"

    def test_created_metadata_contains_given_version(self, buf):
        v = Version("1.2.3.4.5")
        wf = WheelFile(buf, "w", distname="_", version=v)
        assert wf.metadata.version == v

    def test_wheeldata_is_created(self, wf):
        assert wf.wheeldata is not None

    def test_record_is_created(self, wf):
        assert wf.record is not None

    def test_record_is_empty_after_creation(self, wf):
        assert str(wf.record) == ""

    def test_if_given_empty_distname_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, "w", distname="", version="0")

    def test_if_given_distname_with_wrong_chars_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, "w", distname="!@#%^&*", version="0")

    def test_wont_raise_on_distname_with_periods_and_underscores(self, buf):
        try:
            WheelFile(buf, "w", distname="_._._._", version="0")
        except ValueError:
            pytest.fail("Raised unexpectedly.")

    def test_if_given_empty_version_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, "w", distname="_", version="")

    def test_if_given_bogus_version_raises_ValueError(self, buf):
        with pytest.raises(ValueError):
            WheelFile(buf, "w", distname="_", version="BOGUS")

    def test_default_language_tag_is_py3(self, wf):
        assert wf.language_tag == "py3"

    def test_default_abi_tag_is_none(self, wf):
        assert wf.abi_tag == "none"

    def test_default_platform_tag_is_any(self, wf):
        assert wf.platform_tag == "any"

    def test_if_given_build_number_passes_it_to_wheeldata(self, buf):
        build_tag = 123
        wf = WheelFile(buf, "w", distname="_", version="0", build_tag=build_tag)
        assert wf.wheeldata.build == build_tag

    def test_build_number_can_be_str(self, buf):
        build_tag = "123"
        wf = WheelFile(buf, "w", distname="_", version="0", build_tag=build_tag)
        assert wf.wheeldata.build == int(build_tag)

    def test_if_given_language_tag_passes_it_to_wheeldata_tags(self, buf):
        language_tag = "ip2"
        wf = WheelFile(buf, "w", distname="_", version="0", language_tag=language_tag)
        assert wf.wheeldata.tags == ["ip2-none-any"]

    def test_if_given_abi_tag_passes_it_to_wheeldata_tags(self, buf):
        abi_tag = "cp38d"
        wf = WheelFile(buf, "w", distname="_", version="0", abi_tag=abi_tag)
        assert wf.wheeldata.tags == ["py3-cp38d-any"]

    def test_if_given_platform_tag_passes_it_to_wheeldata_tags(self, buf):
        platform_tag = "linux_x84_64"
        wf = WheelFile(buf, "w", distname="_", version="0", platform_tag=platform_tag)
        assert wf.wheeldata.tags == ["py3-none-linux_x84_64"]

    def test_wheeldata_tag_defaults_to_py3_none_any(self, wf):
        assert wf.wheeldata.tags == ["py3-none-any"]

    def test_can_be_given_version_as_int(self, buf):
        with pytest.raises(TypeError):
            WheelFile(buf, mode="w", distname="wheel", version=1)

    def test_given_an_int_version_raises_type_error_on_buf(self, tmp_path):
        with pytest.raises(TypeError):
            WheelFile(tmp_path, mode="w", distname="wheel", version=1)

    @pytest.mark.skip
    def test_passes_zipfile_kwargs_to_zipfile(self, buf, zfarg):
        argument_to_pass_to_zipfile = zfarg
        WheelFile(
            buf, mode="w", distname="_", version="0", **argument_to_pass_to_zipfile
        )

    def test_default_compression_method(self, wf):
        assert wf.zipfile.compression == ZIP_DEFLATED


class TestWheelFileAttributes:

    def test_zipfile_attribute_returns_ZipFile(self, buf, wf):
        assert isinstance(wf.zipfile, ZipFile)

    def test_zipfile_attribute_is_read_only(self, buf):
        with pytest.raises(AttributeError):
            WheelFile(buf, "w", distname="_", version="0").zipfile = None

    def test_object_under_zipfile_uses_given_buf(self, wf, buf):
        assert wf.zipfile.fp is buf

    def test_filename_returns_buf_name(self, buf):
        buf.name = "random_name-0-py3-none-any.whl"
        wf = WheelFile(buf, "w", distname="_", version="0")
        assert wf.filename == buf.name

    def test_given_distname_is_stored_in_distname_attr(self, buf):
        distname = "random_name"
        wf = WheelFile(buf, "w", distname=distname, version="0")
        assert wf.distname == distname

    def test_given_version_is_stored_in_version_attr(self, buf):
        version = Version("1.2.3")
        wf = WheelFile(buf, "w", distname="_", version=version)
        assert wf.version == version

    def test_given_build_tag_is_stored_in_build_tag_attr(self, buf):
        build_tag = 123
        wf = WheelFile(buf, "w", distname="_", version="0", build_tag=build_tag)
        assert wf.build_tag == build_tag

    def test_given_str_build_tag_stores_int_in_build_tag_attr(self, buf):
        build_tag = "123"
        wf = WheelFile(buf, "w", distname="_", version="0", build_tag=build_tag)
        assert wf.build_tag == int(build_tag)

    def test_given_language_tag_is_stored_in_language_tag_attr(self, buf):
        language_tag = "cp3"
        wf = WheelFile(buf, "w", distname="_", version="0", language_tag=language_tag)
        assert wf.language_tag == language_tag

    def test_given_abi_tag_is_stored_in_abi_tag_attr(self, buf):
        abi_tag = "abi3"
        wf = WheelFile(buf, "w", distname="_", version="0", abi_tag=abi_tag)
        assert wf.abi_tag == abi_tag

    def test_given_platform_tag_is_stored_in_abi_tag_attr(self, buf):
        platform_tag = "win32"
        wf = WheelFile(buf, "w", distname="_", version="0", platform_tag=platform_tag)
        assert wf.platform_tag == platform_tag

    def test_distinfo_dirname(self, buf):
        wf = WheelFile(buf, distname="first.part", version="1.2.3", mode="w")
        assert wf.distinfo_dirname == "first_part-1.2.3.dist-info"

    def test_data_dirname(self, buf):
        wf = WheelFile(buf, distname="first.part", version="1.2.3", mode="w")
        assert wf.data_dirname == "first_part-1.2.3.data"


class TestWheelFileClose:

    def test_closes_wheelfiles_zipfile(self, wf):
        wf.close()
        assert wf.zipfile.fp is None

    def test_adds_metadata_to_record(self, wf):
        wf.close()
        assert "_-0.dist-info/METADATA" in wf.record

    def test_adds_wheeldata_to_record(self, wf):
        wf.close()
        assert "_-0.dist-info/WHEEL" in wf.record

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
        path = "unrecorded/file/in/wheel"
        wf.zipfile.writestr(path, "_")
        assert path not in wf.record
        wf.close()
        assert path in wf.record


class TestWheelFileContext:

    def test_is_not_closed_after_entry(self, buf):
        with WheelFile(buf, "w", distname="_", version="0") as wf:
            assert not wf.closed

    def test_is_closed_after_exit(self, buf):
        with WheelFile(buf, "w", distname="_", version="0") as wf:
            pass
        assert wf.closed


class TestWheelFileWrites:

    @pytest.fixture
    def arcpath(self, wf):
        path = "/some/archive/path"
        return ZipPath(wf.zipfile, path)

    def test_writestr_writes_text(self, wf, arcpath):
        text = "Random text."
        wf.writestr(arcpath.at, text)
        assert arcpath.read_text() == text

    def test_writestr_writes_bytes(self, wf, arcpath):
        bytestr = b"random bytestr"
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
        arc_file = ZipPath(wf.zipfile, str(tmp_file.name).lstrip("/"))

        assert arc_file.read_text() == tmp_file.read_text()

    def test_write_puts_files_at_arcname(self, wf, tmp_file):
        wf.write(tmp_file, arcname="arcname/path")
        assert "arcname/path" in wf.zipfile.namelist()

    def test_write_writes_proper_path_to_record(self, wf, tmp_file):
        wf.write(tmp_file, "/////this/should/be/stripped")
        assert "this/should/be/stripped" in wf.record

    def test_writes_preserve_mtime(self, wf, tmp_file):
        tmp_file.touch()
        # 1600000000 is September 2020
        os.utime(tmp_file, (1600000000, 1600000000))

        wf.write(tmp_file, arcname="file")
        assert wf.zipfile.getinfo("file").date_time == (2020, 9, 13, 14, 26, 40)

    def test_write_has_resolve_arg(self, wf, tmp_file):
        wf.write(tmp_file, resolve=True)

    def test_write_data_has_resolve_arg(self, wf, tmp_file):
        wf.write_data(tmp_file, section="test", resolve=True)

    @pytest.fixture
    def spaghetti_path(self, tmp_path):
        (tmp_path / "s" / "p" / "a" / "g" / "h" / "e" / "t" / "t" / "i").mkdir(
            parents=True
        )
        return tmp_path

    def test_write_resolves_paths(self, wf, spaghetti_path):
        path = spaghetti_path / "s/p/a/g/h/e/t/t/i/../../../t/t/i/file"
        path.touch()
        wf.write(path, resolve=True)
        assert wf.zipfile.namelist() == ["file"]

    def test_write_data_resolves_paths(self, wf, spaghetti_path):
        path = spaghetti_path / "s/p/a/g/h/e/t/t/i/../../../t/t/i/file"
        path.touch()
        wf.write_data(path, "section", resolve=True)
        data_path = wf.distname + "-" + str(wf.version) + ".data"
        assert wf.zipfile.namelist() == [data_path + "/section/file"]

    def test_write_doesnt_resolve_when_given_arcname(self, wf, tmp_file):
        wf.write(tmp_file, arcname="not_resolved", resolve=True)
        assert wf.zipfile.namelist() == ["not_resolved"]

    def test_write_data_doesnt_resolve_when_given_arcname(self, wf, tmp_file):
        wf.write_data(tmp_file, "section", arcname="not_resolved", resolve=True)
        data_path = wf.distname + "-" + str(wf.version) + ".data"
        assert wf.zipfile.namelist() == [data_path + "/section/not_resolved"]

    def test_write_distinfo_writes_to_the_right_arcname(self, wf, tmp_file):
        wf.write_distinfo(tmp_file)
        di_arcpath = wf.distname + "-" + str(wf.version) + ".dist-info"
        assert wf.zipfile.namelist() == [di_arcpath + "/" + tmp_file.name]

    def test_write_distinfo_resolve_arg(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, resolve=False)
        di_arcpath = wf.distname + "-" + str(wf.version) + ".dist-info"
        assert wf.zipfile.namelist() == [di_arcpath + str(tmp_file)]

    def test_write_distinfo_recursive(self, wf, tmp_path):
        (tmp_path / "file").touch()
        wf.write_distinfo(tmp_path, skipdir=False, recursive=True)
        di_arcpath = wf.distname + "-" + str(wf.version) + ".dist-info"
        assert set(wf.zipfile.namelist()) == {
            di_arcpath + "/" + tmp_path.name + "/",
            di_arcpath + "/" + tmp_path.name + "/file",
        }

    def test_write_distinfo_non_recursive(self, wf, tmp_path):
        (tmp_path / "file").touch()
        wf.write_distinfo(tmp_path, skipdir=False, recursive=False)
        di_arcpath = wf.distname + "-" + str(wf.version) + ".dist-info"
        assert wf.zipfile.namelist() == [di_arcpath + "/" + tmp_path.name + "/"]

    def test_write_distinfo_arcpath(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, arcname="custom_filename")
        di_arcpath = wf.distname + "-" + str(wf.version) + ".dist-info"
        assert wf.zipfile.namelist() == [di_arcpath + "/custom_filename"]

    @pytest.mark.parametrize("filename", ("WHEEL", "METADATA", "RECORD"))
    def test_write_distinfo_doesnt_permit_writing_metadata(
        self, wf, tmp_path, filename
    ):
        (tmp_path / filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.write_distinfo(tmp_path / filename)

    def test_write_distinfo_doesnt_permit_empty_arcname(self, wf, tmp_file):
        with pytest.raises(ProhibitedWriteError):
            wf.write_distinfo(tmp_file, arcname="")

    @pytest.mark.xfail
    def test_write_distinfo_doesnt_permit_backing_out(self, wf, tmp_file):
        with pytest.raises(ValueError):
            wf.write_distinfo(tmp_file, arcname="../file")

    @pytest.mark.xfail
    @pytest.mark.parametrize("filename", ("WHEEL", "METADATA", "RECORD"))
    def test_write_doesnt_permit_writing_metadata(self, wf, tmp_path, filename):
        (tmp_path / filename).touch()
        with pytest.raises(ProhibitedWriteError):
            wf.write(tmp_path / filename)

    @pytest.mark.xfail
    @pytest.mark.parametrize("filename", ("WHEEL", "METADATA", "RECORD"))
    def test_writestr_doesnt_permit_writing_metadata(self, wf, filename):
        with pytest.raises(ProhibitedWriteError):
            wf.writestr(filename, b"")

    def test_writestr_distinfo(self, wf):
        arcname = "my_meta_file"
        data = b"my data"
        wf.writestr_distinfo(arcname, data)
        assert wf.zipfile.read(wf.distinfo_dirname + "/" + arcname) == data

    def test_writestr_distinfo_via_zipinfo(self, wf):
        arcname = "my_meta_file"
        data = b"my data"
        zi = ZipInfo(arcname)
        wf.writestr_distinfo(zi, data)
        assert wf.zipfile.read(wf.distinfo_dirname + "/" + arcname) == data

    @pytest.mark.parametrize("name", ("WHEEL", "METADATA", "RECORD"))
    def test_writestr_distinfo_doesnt_permit_writing_metadata(self, wf, name):
        with pytest.raises(ProhibitedWriteError):
            wf.writestr_distinfo(name, b"")

    @pytest.mark.parametrize("name", ("WHEEL", "METADATA", "RECORD"))
    def test_writestr_distinfo_doesnt_permit_writing_metadata_as_dirs(self, wf, name):
        with pytest.raises(ProhibitedWriteError):
            wf.writestr_distinfo(name + "/" + "file", b"")

    # TODO: also test write_data and write_distinfo
    # TODO: ALSO remember to test metadata names separately - they are not
    # inside the archive until `close()` is called, so it will not be detected.
    @pytest.mark.xfail
    def test_write_bails_on_writing_directories_over_files(self, wf, tmp_path):
        file_to_write = tmp_path / "file"
        file_to_write.touch()
        wf.write(file_to_write, "file")
        with pytest.raises(ProhibitedWriteError):
            wf.write(file_to_write, "file/or_is_it")

    # TODO: also test writestr_data and writestr_distinfo
    @pytest.mark.xfail
    def test_writestr_bails_on_writing_directories_over_files(self, wf):
        wf.writestr("file", b"")
        with pytest.raises(ProhibitedWriteError):
            wf.writestr("file/or_is_it", b"")


def named_bytesio(name: str) -> BytesIO:
    bio = BytesIO()
    bio.name = str(name)
    return bio


rwb_open = partial(open, mode="wb+")


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
        wf = WheelFile(path, "w")
        assert (
            wf.distname == "my_awesome.wheel"
            and str(wf.version) == "4.2.0"
            and wf.language_tag == "py38"
            and wf.abi_tag == "cp38d"
            and wf.platform_tag == "linux_x84_64"
        )

    def test_infers_from_given_path_with_build_tag(self, tmp_path, target_type):
        path = target_type(
            tmp_path / "my_awesome.wheel-1.2.3.dev0-5-ip37-cp38d-win32.whl"
        )
        wf = WheelFile(path, "w")
        assert (
            wf.distname == "my_awesome.wheel"
            and str(wf.version) == "1.2.3.dev0"
            and wf.build_tag == 5
            and wf.language_tag == "ip37"
            and wf.abi_tag == "cp38d"
            and wf.platform_tag == "win32"
        )

    def test_if_distname_part_is_empty_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "-4.2.0-py3-none-any.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, "w")

    def test_if_given_distname_only_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, "w")

    def test_if_version_part_is_empty_raises_UDE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel--py3-none-any.whl")
        with pytest.raises(UnnamedDistributionError):
            WheelFile(path, "w")

    def test_if_bad_chars_in_distname_raises_VE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_@wesome.wheel-4.2.0-py3-none-any.whl")
        with pytest.raises(ValueError):
            WheelFile(path, "w")

    def test_if_invalid_version_raises_VE(self, tmp_path, target_type):
        path = target_type(tmp_path / "my_awesome.wheel-nice-py3-none-any.whl")
        with pytest.raises(ValueError):
            WheelFile(path, "w")


def test_given_unnamed_buf_and_no_distname_raises_UDE(buf):
    with pytest.raises(UnnamedDistributionError):
        WheelFile(buf, "w", version="0")


def test_given_unnamed_buf_and_no_version_raises_UDE(buf):
    with pytest.raises(UnnamedDistributionError):
        WheelFile(buf, "w", distname="_")


class TestWheelFileDirectoryTarget:
    """Tests how WheelFile.__init__() behaves when given a directory"""

    def test_if_version_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, "w", distname="my_dist")

    def test_if_distname_not_given_raises_ValueError(self, tmp_path):
        with pytest.raises(ValueError):
            WheelFile(tmp_path, "w", version="0")

    def test_given_directory_and_all_args__sets_filename(self, tmp_path):
        with WheelFile(tmp_path, "w", distname="my_dist", version="1.0.0") as wf:
            expected_name = (
                "-".join(
                    (
                        wf.distname,
                        str(wf.version),
                        wf.language_tag,
                        wf.abi_tag,
                        wf.platform_tag,
                    )
                )
                + ".whl"
            )
            assert wf.filename == str(tmp_path / expected_name)

    def test_given_no_target_assumes_curdir(self, tmp_path):
        old_path = Path.cwd()
        os.chdir(tmp_path)
        with WheelFile(mode="w", distname="my_dist", version="1.0.0") as wf:
            expected_name = (
                "-".join(
                    (
                        wf.distname,
                        str(wf.version),
                        wf.language_tag,
                        wf.abi_tag,
                        wf.platform_tag,
                    )
                )
                + ".whl"
            )
            assert wf.filename == str(Path("./") / expected_name)
        os.chdir(old_path)

    def test_given_no_target_creates_file_from_args(self, tmp_path):
        old_path = Path.cwd()
        os.chdir(tmp_path)
        with WheelFile(
            mode="w",
            distname="my_dist",
            version="1.2.alpha1",
            build_tag=123,
            language_tag="jp2",
            abi_tag="jre8",
            platform_tag="win32",
        ) as wf:
            expected_name = "my_dist-1.2a1-123-jp2-jre8-win32.whl"
            assert wf.filename == str(Path("./") / expected_name)
        os.chdir(old_path)


class TestWheelFileDistDataWrite:

    def test_write__if_section_is_empty_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.write_data("_", "")

    def test_write__if_section_contains_slashes_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.write_data("_", "section/path/")

    @pytest.mark.parametrize("path_type", [str, Path])
    def test_write__writes_given_str_path(self, wf, tmp_file, path_type):
        contents = "Contents of the file to write"
        expected_arcpath = f"_-0.data/section/{tmp_file.name}"
        tmp_file.write_text(contents)
        wf.write_data(path_type(tmp_file), "section")

        assert wf.zipfile.read(expected_arcpath) == tmp_file.read_bytes()

    def test_writestr__if_section_is_empty_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.writestr_data("", "_", b"data")

    def test_writestr__if_section_contains_slashes_raises_VE(self, wf):
        with pytest.raises(ValueError):
            wf.writestr_data("section/path/", "_", "data")

    def test_writestr__writes_given_str_path(self, wf):
        contents = b"Contents of to write"
        filename = "file"
        expected_arcpath = f"_-0.data/section/{filename}"
        wf.writestr_data("section", filename, contents)

        assert wf.zipfile.read(expected_arcpath) == contents

    def test_mode_is_written_to_mode_attribute(self, wf):
        assert wf.mode == "w"


class TestWheelFileRecursiveWrite:
    def test_write_has_recursive_arg(self, wf, tmp_path):
        wf.write(tmp_path, recursive=True)

    def test_recursive_write_does_not_break_on_files(self, wf, tmp_file):
        wf.write(tmp_file, recursive=True)

    def test_write_data_has_recursive_arg(self, wf, tmp_path):
        wf.write_data(tmp_path, "section", recursive=True)

    def test_recursive_write_data_does_not_break_on_files(self, wf, tmp_file):
        wf.write_data(tmp_file, "section", recursive=True)

    @pytest.fixture
    def path_tree(self, tmp_path):
        """The directory tree root is the first item in the list."""
        d = tmp_path
        tree = [
            d / "file",
            d / "empty_dir" / "",
            d / "dir_a" / "",
            d / "dir_a" / "subdir_a",
            d / "dir_a" / "subdir_a" / "1_file",
            d / "dir_a" / "subdir_a" / "2_file",
            d / "dir_b",
            d / "dir_b" / "subdir_b_1" / "",
            d / "dir_b" / "subdir_b_1" / "file",
            d / "dir_b" / "subdir_b_2" / "",
            d / "dir_b" / "subdir_b_2" / "file",
        ]

        for path in tree:
            if path.stem.endswith("file"):
                path.write_text("contents")
            else:
                path.mkdir()

        tree = [d] + tree

        return [str(p) + "/" if p.is_dir() else str(p) for p in tree]

    def test_write_recursive_writes_all_files_in_the_tree(self, wf, path_tree):
        directory = path_tree[0]
        wf.write(directory, recursive=True, resolve=False, skipdir=False)
        expected_tree = [pth.lstrip("/") for pth in path_tree]
        assert set(wf.zipfile.namelist()) == set(expected_tree)

    def test_write_recursive_writes_with_proper_arcname(self, wf, path_tree):
        directory = path_tree[0]
        custom_arcname = "something/different"
        wf.write(directory, arcname=custom_arcname, recursive=True)
        assert all(path.startswith(custom_arcname) for path in wf.zipfile.namelist())

    def test_write_data_writes_recursively_when_asked(self, wf, path_tree):
        directory = path_tree[0]
        directory_name = os.path.basename(directory.rstrip("/"))
        archive_root = "_-0.data/test/" + directory_name + "/"

        wf.write_data(directory, section="test", skipdir=False, recursive=True)

        expected_tree = [archive_root + pth[len(directory) :] for pth in path_tree]
        assert set(wf.zipfile.namelist()) == set(expected_tree)

    def test_write_data_writes_non_recursively_when_asked(self, wf, path_tree):
        directory = path_tree[0]
        directory_name = os.path.basename(directory.rstrip("/"))
        archive_root = "_-0.data/test/" + directory_name + "/"

        wf.write_data(directory, section="test", skipdir=False, recursive=False)

        expected_tree = [archive_root]
        assert wf.zipfile.namelist() == expected_tree


class TestWheelFileRefreshRecord:

    def test_silently_skips_directories(self, wf):
        wf.writestr("directory/", b"")
        wf.refresh_record("directory/")
        assert str(wf.record) == ""


class TestWheelFileNameList:
    def test_after_init_is_empty(self, wf):
        assert wf.namelist() == []

    def test_after_writing_contains_the_arcpath_of_written_file(self, wf):
        arcpath = "this/is/a/file"
        wf.writestr(arcpath, b"contents")
        assert wf.namelist() == [arcpath]

    @pytest.mark.parametrize("meta_file", ["METADATA", "RECORD", "WHEEL"])
    def test_after_closing_does_not_contain_meta_files(self, wf, meta_file):
        wf.close()
        assert (wf.distinfo_dirname + "/" + meta_file) not in wf.namelist()


class TestWheelFileInfoList:
    def test_after_init_is_empty(self, wf):
        assert wf.infolist() == []

    def test_after_writing_contains_the_arcpath_of_written_file(self, wf):
        arcpath = "this/is/a/file"
        wf.writestr(arcpath, b"contents")
        infolist = wf.infolist()
        assert len(infolist) == 1 and infolist[0].filename == arcpath

    @pytest.mark.parametrize("meta_file", ["METADATA", "RECORD", "WHEEL"])
    def test_after_closing_does_not_contain_meta_files(self, wf, meta_file):
        wf.close()
        infolist_arcpaths = [zi.filename for zi in wf.infolist()]
        assert (wf.distinfo_dirname + "/" + meta_file) not in infolist_arcpaths


@pytest.mark.parametrize("metadata_name", ["METADATA", "RECORD", "WHEEL"])
def test_wheelfile_METADATA_FILENAMES(metadata_name):
    assert metadata_name in WheelFile.METADATA_FILENAMES


class TestSkipDir:
    def test_write_skips_empty_dir_on_skipdir(self, wf, tmp_path):
        wf.write(tmp_path, recursive=False, skipdir=True)
        assert wf.namelist() == []

    def test_write_data_skips_empty_dir_on_skipdir(self, wf, tmp_path):
        wf.write_data(tmp_path, section="_", recursive=False, skipdir=True)
        assert wf.namelist() == []

    def test_write_distinfo_skips_empty_dir_on_skipdir(self, wf, tmp_path):
        wf.write_distinfo(tmp_path, recursive=False, skipdir=True)
        assert wf.namelist() == []

    def test_write_doesnt_skip_dirs_if_skipdir_not_set(self, wf, tmp_path):
        wf.write(tmp_path, recursive=False, skipdir=False)
        expected_entry = str(tmp_path.name).lstrip("/") + "/"
        assert wf.namelist() == [expected_entry]

    def test_write_data_doesnt_skip_dirs_if_skipdir_not_set(self, wf, tmp_path):
        wf.write_data(tmp_path, section="_", recursive=False, skipdir=False)
        expected_entry = (
            wf.data_dirname + "/" + "_/" + str(tmp_path.name).lstrip("/") + "/"
        )
        assert wf.namelist() == [expected_entry]

    def test_write_distinfo_doesnt_skip_dirs_if_skipdir_not_set(self, wf, tmp_path):
        wf.write_distinfo(tmp_path, recursive=False, skipdir=False)
        expected_entry = (
            wf.distinfo_dirname + "/" + str(tmp_path.name).lstrip("/") + "/"
        )
        assert wf.namelist() == [expected_entry]


class TestZipFileRelatedArgs:

    @pytest.fixture
    def wf(self, buf):
        wf = WheelFile(
            buf, "w", distname="_", version="0", compression=ZIP_STORED, compresslevel=1
        )
        yield wf
        wf.close()

    def test_passes_compression_arg_to_zipfile(self, buf):
        wf = WheelFile(buf, mode="w", distname="_", version="0", compression=ZIP_BZIP2)
        assert wf.zipfile.compression == ZIP_BZIP2

    def test_passes_allowZip64_arg_to_zipfile(self, buf):
        wf = WheelFile(buf, mode="w", distname="_", version="0", allowZip64=False)
        # ZipFile.open trips when allowZip64 is forced in a zipfile that does
        # not allow it.
        #
        # Exception message:
        # "force_zip64 is True, but allowZip64 was False when opening the ZIP
        # file."
        with pytest.raises(ValueError, match="allowZip64 was False"):
            assert wf.zipfile.open("file", mode="w", force_zip64=True)

    def test_passes_compresslevel_arg_to_zipfile(self, buf):
        wf = WheelFile(buf, mode="w", distname="_", version="0", compresslevel=7)
        assert wf.zipfile.compresslevel == 7

    def test_passes_strict_timestamps_arg_to_zipfile(self, buf, tmp_file):
        wf = WheelFile(
            buf, mode="w", distname="_", version="0", strict_timestamps=False
        )
        # strict_timestamps will be propagated into ZipInfo objects created by
        # ZipFile.
        # Given very old timestamp, ZipInfo will set itself to 01-01-1980
        os.utime(tmp_file, (10000000, 100000000))
        wf.write(tmp_file, resolve=False)
        zinfo = wf.zipfile.getinfo(str(tmp_file).lstrip("/"))
        assert zinfo.date_time == (1980, 1, 1, 0, 0, 0)

    def test_writestr_sets_the_right_compress_type(self, wf):
        arcname = "file"
        wf.writestr(arcname, b"_", compress_type=ZIP_BZIP2)
        assert wf.zipfile.getinfo(arcname).compress_type == ZIP_BZIP2

    def test_writestr_compress_type_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi.compress_type = ZIP_DEFLATED
        wf.writestr(zi, b"_", compress_type=ZIP_BZIP2)
        assert wf.zipfile.getinfo(zi.filename).compress_type == ZIP_BZIP2

    def test_writestr_data_sets_the_right_compress_type(self, wf):
        arcname = "file"
        wf.writestr_data("_", arcname, b"_", compress_type=ZIP_BZIP2)
        arcpath = wf.data_dirname + "/_/" + arcname
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_writestr_data_compress_type_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi.compress_type = ZIP_DEFLATED
        wf.writestr_data("_", zi, b"_", compress_type=ZIP_BZIP2)
        arcpath = wf.data_dirname + "/_/" + zi.filename
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_writestr_distinfo_sets_the_right_compress_type(self, wf):
        arcname = "file"
        wf.writestr_distinfo(arcname, b"_", compress_type=ZIP_BZIP2)
        arcpath = wf.distinfo_dirname + "/" + arcname
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_writestr_distinfo_compress_type_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi.compress_type = ZIP_DEFLATED
        wf.writestr_distinfo(zi, b"_", compress_type=ZIP_BZIP2)
        arcpath = wf.distinfo_dirname + "/" + zi.filename
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_write_sets_the_right_compress_type(self, wf, tmp_file):
        wf.write(tmp_file, compress_type=ZIP_BZIP2)
        assert wf.zipfile.getinfo(tmp_file.name).compress_type == ZIP_BZIP2

    def test_write_data_sets_the_right_compress_type(self, wf, tmp_file):
        wf.write_data(tmp_file, "_", compress_type=ZIP_BZIP2)
        arcpath = wf.data_dirname + "/_/" + tmp_file.name
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_write_distinfo_sets_the_right_compress_type(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, compress_type=ZIP_BZIP2)
        arcpath = wf.distinfo_dirname + "/" + tmp_file.name
        assert wf.zipfile.getinfo(arcpath).compress_type == ZIP_BZIP2

    def test_writestr_sets_the_right_compresslevel(self, wf):
        arcname = "file"
        wf.writestr(arcname, b"_", compresslevel=7)
        assert wf.zipfile.getinfo(arcname)._compresslevel == 7

    def test_writestr_compresslevel_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi._compresslevel = 3
        wf.writestr(zi, b"_", compresslevel=7)
        assert wf.zipfile.getinfo(zi.filename)._compresslevel == 7

    def test_writestr_data_sets_the_right_compresslevel(self, wf):
        arcname = "file"
        wf.writestr_data("_", arcname, b"_", compresslevel=7)
        arcpath = wf.data_dirname + "/_/" + arcname
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_writestr_data_compresslevel_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi._compresslevel = 3
        wf.writestr_data("_", zi, b"_", compresslevel=7)
        arcpath = wf.data_dirname + "/_/" + zi.filename
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_writestr_distinfo_sets_the_right_compresslevel(self, wf):
        arcname = "file"
        wf.writestr_distinfo(arcname, b"_", compresslevel=7)
        arcpath = wf.distinfo_dirname + "/" + arcname
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_writestr_distinfo_compresslevel_overrides_zinfo(self, wf):
        zi = ZipInfo("_")
        zi._compresslevel = 3
        wf.writestr_distinfo(zi, b"_", compresslevel=7)
        arcpath = wf.distinfo_dirname + "/" + zi.filename
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_write_sets_the_right_compresslevel(self, wf, tmp_file):
        wf.write(tmp_file, compresslevel=7)
        assert wf.zipfile.getinfo(tmp_file.name)._compresslevel == 7

    def test_write_data_sets_the_right_compresslevel(self, wf, tmp_file):
        wf.write_data(tmp_file, "_", compresslevel=7)
        arcpath = wf.data_dirname + "/_/" + tmp_file.name
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_write_distinfo_sets_the_right_compresslevel(self, wf, tmp_file):
        wf.write_distinfo(tmp_file, compresslevel=7)
        arcpath = wf.distinfo_dirname + "/" + tmp_file.name
        assert wf.zipfile.getinfo(arcpath)._compresslevel == 7

    def test_write_default_compress_type_is_deflate(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write(tmp_file)
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_write_data_default_compress_type_is_deflate(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write_data(tmp_file, "section")
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_write_distinfo_default_compress_type_is_deflate(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write_distinfo(tmp_file)
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_write_default_compress_type_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.write(tmp_file)
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_write_data_default_compress_type_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.write_data(tmp_file, "section")
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_write_distinfo_default_compress_type_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.write_distinfo(tmp_file)
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_write_default_compresslevel_is_none(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write(tmp_file)
        assert wf.infolist()[0]._compresslevel is None

    def test_write_data_default_compresslevel_is_none(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write_data(tmp_file, "section")
        assert wf.infolist()[0]._compresslevel is None

    def test_write_distinfo_default_compresslevel_is_none(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.write_distinfo(tmp_file)
        assert wf.infolist()[0]._compresslevel is None

    def test_write_default_compresslevel_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.write(tmp_file)
        assert wf.infolist()[0]._compresslevel == 9

    def test_write_data_default_compresslevel_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.write_data(tmp_file, "section")
        assert wf.infolist()[0]._compresslevel == 9

    def test_write_distinfo_default_compresslevel_is_from_init(self, buf, tmp_file):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.write_distinfo(tmp_file)
        assert wf.infolist()[0]._compresslevel == 9

    def test_writestr_default_compress_type_is_deflate(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr("file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_writestr_data_default_compress_type_is_deflate(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr_data("section", "file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_writestr_distinfo_default_compress_type_is_deflate(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr_distinfo("file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_DEFLATED

    def test_writestr_default_compress_type_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.writestr("file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_writestr_data_default_compress_type_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.writestr_data("section", "file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_writestr_distinfo_default_compress_type_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compression=ZIP_BZIP2)
        wf.writestr_distinfo("file", b"data")
        assert wf.infolist()[0].compress_type == ZIP_BZIP2

    def test_writestr_default_compresslevel_is_none(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr("file", b"data")
        assert wf.infolist()[0]._compresslevel is None

    def test_writestr_data_default_compresslevel_is_none(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr_data("section", "file", b"data")
        assert wf.infolist()[0]._compresslevel is None

    def test_writestr_distinfo_default_compresslevel_is_none(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0")
        wf.writestr_distinfo("file", b"data")
        assert wf.infolist()[0]._compresslevel is None

    def test_writestr_default_compresslevel_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.writestr("file", b"data")
        assert wf.infolist()[0]._compresslevel == 9

    def test_writestr_data_default_compresslevel_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.writestr_data("section", "file", b"data")
        assert wf.infolist()[0]._compresslevel == 9

    def test_writestr_distinfo_default_compresslevel_is_from_init(self, buf):
        wf = WheelFile(buf, "w", distname="_", version="0", compresslevel=9)
        wf.writestr_distinfo("file", b"data")
        assert wf.infolist()[0]._compresslevel == 9


class TestZipinfoAttributePreserval:

    preserved_fields = pytest.mark.parametrize(
        "field, value",
        [
            ("date_time", (2000, 1, 2, 3, 4, 2)),
            ("compress_type", ZIP_BZIP2),
            ("comment", b"Wubba lubba dub dub"),
            ("extra", bytes([0x00, 0x00, 0x04, 0x00] + [0xFF] * 4)),
            ("create_system", 4),
            ("create_version", 31),
            ("extract_version", 42),
            ("internal_attr", 0x02),
            ("external_attr", 0x02),
            # Failing / impossible:
            # ZIP stores timestamps with two seconds of granularity
            # ("date_time", (2000, 1, 2, 3, 4, 1)),
            # Not preservable without changing other values
            # ("flag_bits", 0xFFFFFF),
            # Not supported by Python's zipfile
            # ("volume", 0x01),
        ],
    )

    @preserved_fields
    def test_writestr_propagates_zipinfo_fields(self, field, value, wf, buf):
        arcpath = "some/archive/path"
        zi = ZipInfo(arcpath)
        setattr(zi, field, value)

        wf.writestr(zi, "_")
        wf.close()

        with WheelFile(buf, distname="_", version="0") as wf:
            assert getattr(wf.zipfile.getinfo(arcpath), field) == value

    @preserved_fields
    def test_writestr_data_propagates_zipinfo_fields(self, field, value, wf, buf):
        data_path = "some/data"
        section = "section"
        zi = ZipInfo(data_path)
        setattr(zi, field, value)

        wf.writestr_data(section, zi, "_")
        wf.close()

        arcpath = wf.data_dirname + "/" + section + "/" + data_path

        with WheelFile(buf, distname="_", version="0") as wf:
            assert getattr(wf.zipfile.getinfo(arcpath), field) == value

    @preserved_fields
    def test_writestr_distinfo_propagates_zipinfo_fields(self, field, value, wf, buf):
        data_path = "some/metadata"
        zi = ZipInfo(data_path)
        setattr(zi, field, value)

        wf.writestr_distinfo(zi, "_")
        wf.close()

        arcpath = wf.distinfo_dirname + "/" + data_path

        with WheelFile(buf, distname="_", version="0") as wf:
            assert getattr(wf.zipfile.getinfo(arcpath), field) == value
