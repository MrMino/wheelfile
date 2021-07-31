import pytest

from wheelfile import WheelFile


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


class TestUnspecifiedArgs:

    @pytest.fixture
    def wf(self, buf):
        wf = WheelFile(buf, 'w',
                       distname='dist',
                       version='123', build_tag='321',
                       language_tag='lang', abi_tag='abi', platform_tag='win32')
        yield wf
        wf.close()

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
        cwf = WheelFile.from_wheelfile(wf, distname='_', version='0',
                                       build_tag=None)
        assert cwf.build_tag is None

    def test_none_language_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, distname='_', version='0',
                                       language_tag=None)
        assert cwf.language_tag == 'py3'

    def test_none_abi_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, distname='_', version='0',
                                       abi_tag=None)
        assert cwf.abi_tag == 'none'

    def test_none_platform_tag_sets_default(self, wf, buf):
        cwf = WheelFile.from_wheelfile(wf, distname='_', version='0',
                                       platform_tag=None)
        assert cwf.platform_tag == 'any'


class TestPassingZipFileArgs:

    pass


class TestCloneTypes:

    def test_buf_to_buf(self, wf, buf):
        wf = WheelFile.from_wheelfile(wf, buf)
        assert isinstance(wf, WheelFile)


class TestContentsCloning:

    pass


class TestClonedMetadata:

    pass


class TestNoOverwriting:

    pass
