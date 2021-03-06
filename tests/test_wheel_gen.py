import pytest

import sys

from io import BytesIO
from wheelfile import WheelFile

if sys.version_info >= (3, 8):
    from zipfile import ZipFile, Path as ZipPath
else:
    from zipfile38 import ZipFile, Path as ZipPath


class TestEmptyWheelStructure:
    distname = 'my_dist'
    version = '1.0.0'

    @pytest.fixture(scope='class')
    def buf(self):
        return BytesIO()

    @pytest.fixture(scope='class')
    def wheelfile(self, buf):
        wf = WheelFile(buf, 'w', distname=self.distname, version=self.version)
        wf.close()
        return wf

    @pytest.fixture(scope='class')
    def wheel(self, wheelfile, buf):
        assert not buf.closed
        return ZipFile(buf)

    @pytest.fixture(scope='class')
    def distinfo(self, wheel):
        return ZipPath(wheel, f'{self.distname}-{self.version}.dist-info/')

    def test_dist_info_is_dir(self, distinfo):
        assert distinfo.is_dir()

    def test_has_no_synonym_files(self, wheel):
        assert len(set(wheel.namelist())) == len(wheel.namelist())

    def test_metadata_is_from_wheelfile(self, distinfo, wheelfile):
        metadata = distinfo / 'METADATA'
        assert metadata.read_text() == str(wheelfile.metadata)

    def test_wheeldata_is_from_wheelfile(self, distinfo, wheelfile):
        wheeldata = distinfo / 'WHEEL'
        assert wheeldata.read_text() == str(wheelfile.wheeldata)

    def test_record_is_from_wheelfile(self, distinfo, wheelfile):
        record = distinfo / 'RECORD'
        assert record.read_text() == str(wheelfile.record).replace('\r\n', '\n')


class TestLongMetadataLine:
    distname = 'my_dist'
    version = '1.0.0'

    long_requirement = "a" * 400

    @pytest.fixture(scope='class')
    def buf(self):
        return BytesIO()

    @pytest.fixture(scope='class')
    def wheelfile(self, buf):
        wf = WheelFile(buf, 'w', distname=self.distname, version=self.version)
        wf.metadata.requires_dists = [self.long_requirement]
        wf.close()
        return wf

    @pytest.fixture(scope='class')
    def wheel(self, wheelfile, buf):
        assert not buf.closed
        return ZipFile(buf)

    @pytest.fixture(scope='class')
    def distinfo(self, wheel):
        return ZipPath(wheel, f'{self.distname}-{self.version}.dist-info/')

    def test_metadata_is_from_wheelfile(self, distinfo, wheelfile):
        "Test long lines in METADATA aren't split to multiple shorter lines"
        metadata = distinfo / 'METADATA'
        assert f"Requires-Dist: {self.long_requirement}" in metadata.read_text()
