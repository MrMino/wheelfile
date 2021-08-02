import pytest

from wheelfile import (__version__ as lib_version,
                       WheelData, MetaData, WheelRecord,
                       UnsupportedHashTypeError,
                       RecordContainsDirectoryError,
                       )
from packaging.version import Version
from textwrap import dedent
from io import BytesIO


class TestMetadata:
    plurals = {
        "keywords", "classifiers", "project_urls", "platforms",
        "supported_platforms", "requires_dists", "requires_externals",
        "provides_extras", "provides_dists", "obsoletes_dists"
    }

    def test_only_name_and_version_is_required(self):
        md = MetaData(name='my-package', version='1.2.3')
        assert md.name == 'my-package' and str(md.version) == '1.2.3'

    @pytest.fixture
    def metadata(self):
        return MetaData(name='my-package', version='1.2.3')

    def test_basic_eq(self):
        args = {'name': 'x', 'version': '1'}
        assert MetaData(**args) == MetaData(**args)

    def test_basic_to_str(self, metadata):
        expected = dedent("""\
            Metadata-Version: 2.1
            Name: my-package
            Version: 1.2.3

        """)
        assert str(metadata) == expected

    def test_basic_from_str(self, metadata):
        assert str(MetaData.from_str(str(metadata))) == str(metadata)

    def test_to_and_fro_str_objects_are_equal(self, metadata):
        assert metadata == MetaData.from_str(str(metadata))

    def test_metadata_version_is_2_1(self, metadata):
        assert metadata.metadata_version == '2.1'

    def test_metadata_version_is_unchangeable(self, metadata):
        with pytest.raises(AttributeError):
            metadata.metadata_version = '3.0'

    @pytest.mark.parametrize('field', plurals)
    def test_plural_params_default_to_empty_lists(self, metadata, field):
        # Each of the attribute names here should end with an "s".
        assert getattr(metadata, field) == []

    @pytest.mark.parametrize('field', plurals - {'keywords'})
    def test_plural_fields_except_keywords_show_up_as_multiple_use(self, field):
        assert MetaData.field_is_multiple_use(field)

    def test_keywords_is_not_multiple_use(self):
        assert not MetaData.field_is_multiple_use('keywords')

    @pytest.fixture
    def full_usage(self):
        description = dedent("""\

            Some

            Long

            Description
        """)
        kwargs = {
            'name': 'package-name',
            'version': Version('1.2.3'),
            'summary': "this is a test",
            'description': description,
            'description_content_type': 'text/plain',
            'keywords': ["test", "unittests", "package", "wheelfile"],
            'classifiers': ["Topic :: Software Development :: Testing",
                            "Framework :: Pytest"],
            'author': "MrMino",
            'author_email': "mrmino@example.com",
            'maintainer': "NotMrMino",
            'maintainer_email': "not.mrmino@example.com",
            'license': "May be distributed only if this test succeeds",
            'home_page': "http://example.com/package-name/1.2.3",
            'download_url': "http://example.com/package-name/1.2.3/download",
            'project_urls': ["Details: http://example.com/package-name/"],
            'platforms': ["SomeOS", "SomeOtherOS"],
            'supported_platforms': ["some-architecture-128", "my-mips-21"],
            'requires_python': "~=3.6",
            'requires_dists': ["wheelfile[metadata]~=1.0", "paramiko"],
            'requires_externals': ["vim", "zsh"],
            'provides_extras': ["metadata"],
            'provides_dists': ["wheel_packaging"],
            'obsoletes_dists': ["wheel"]
        }

        return kwargs

    def test_params_are_memorized(self, full_usage):
        md = MetaData(**full_usage)
        for field, value in full_usage.items():
            assert getattr(md, field) == value

    def test_metadata_text_generation(self, full_usage):
        # Order of the header lines is NOT tested (order in payload - is)
        expected_headers = dedent("""\
            Metadata-Version: 2.1
            Name: package-name
            Version: 1.2.3
            Platform: SomeOS
            Platform: SomeOtherOS
            Supported-Platform: some-architecture-128
            Supported-Platform: my-mips-21
            Summary: this is a test
            Description-Content-Type: text/plain
            Keywords: test,unittests,package,wheelfile
            License: May be distributed only if this test succeeds
            Home-page: http://example.com/package-name/1.2.3
            Download-URL: http://example.com/package-name/1.2.3/download
            Author: MrMino
            Author-email: mrmino@example.com
            Maintainer: NotMrMino
            Maintainer-email: not.mrmino@example.com
            Classifier: Topic :: Software Development :: Testing
            Classifier: Framework :: Pytest
            Requires-Dist: wheelfile[metadata]~=1.0
            Requires-Dist: paramiko
            Requires-Python: ~=3.6
            Requires-External: vim
            Requires-External: zsh
            Project-URL: Details: http://example.com/package-name/
            Provides-Extra: metadata
            Provides-Dist: wheel_packaging
            Obsoletes-Dist: wheel
        """).splitlines()
        expected_payload = dedent("""\


            Some

            Long

            Description
        """).splitlines()

        lines = str(MetaData(**full_usage)).splitlines()
        header_end_idx = lines.index('')
        headers = lines[:header_end_idx]
        payload = lines[header_end_idx:]
        assert set(headers) == set(expected_headers)
        assert payload == expected_payload

    def test_full_usage_from_str_eqs_by_str(self, full_usage):
        md = MetaData(**full_usage)
        fs = MetaData.from_str(str(md))
        assert str(fs) == str(md)

    def test_full_usage_from_str_eqs_by_obj(self, full_usage):
        md = MetaData(**full_usage)
        fs = MetaData.from_str(str(md))
        assert fs == md

    def test_no_mistaken_attributes(self, metadata):
        with pytest.raises(AttributeError):
            metadata.maintainers = ''

        with pytest.raises(AttributeError):
            metadata.Description = ''

        with pytest.raises(AttributeError):
            metadata.clasifiers = []

    def test_there_are_24_fields_in_this_metadata_version(self):
        assert len(
            [field for field in MetaData.__slots__] + ['metadata_version']
        ) == 24

    def test_keywords_param_accepts_comma_separated_str(self):
        metadata = MetaData(name='name', version='1.2.3', keywords='a,b,c')
        assert metadata.keywords == ['a', 'b', 'c']

    def test_keywords_param_accepts_list(self):
        metadata = MetaData(name='name', version='1.2.3',
                            keywords=['a', 'b', 'c'])
        assert metadata.keywords == ['a', 'b', 'c']


class TestWheelData:
    def test_simple_init(self):
        wm = WheelData()
        assert (wm.generator.startswith('wheelfile ')
                and wm.root_is_purelib is True
                and wm.tags == ['py3-none-any']
                and wm.build is None)

    def test_init_args(self):
        args = {}
        args.update(generator='test', root_is_purelib=False,
                    tags='my-awesome-tag', build=2)
        wm = WheelData(**args)

        assert (wm.generator == args['generator']
                and wm.root_is_purelib == args['root_is_purelib']
                and set(wm.tags) == set([args['tags']])
                and wm.build == args['build'])

    def test_tags_are_extended(self):
        wm = WheelData(tags=['py2.py3-none-any', 'py2-cp3.cp2-manylinux1'])
        expected_tags = [
            'py2-none-any',
            'py3-none-any',
            'py2-cp3-manylinux1',
            'py2-cp2-manylinux1'
        ]
        assert set(wm.tags) == set(expected_tags)

    def test_single_tag_is_extended(self):
        wm = WheelData(tags='py2.py3-none-any')
        expected_tags = [
            'py2-none-any',
            'py3-none-any',
        ]
        assert set(wm.tags) == set(expected_tags)

    def test_wheel_version_is_1_0(self):
        assert WheelData().wheel_version == '1.0'

    def test_wheel_version_is_not_settable(self):
        with pytest.raises(AttributeError):
            WheelData().wheel_version = '2.0'

    def test_strignifies_into_valid_wheelmeta(self):
        expected_contents = dedent(
            f"""\
            Wheel-Version: 1.0
            Generator: wheelfile {lib_version}
            Root-Is-Purelib: true
            Tag: py2-none-any
            Build: 123

            """
        )
        wm = WheelData(tags='py2-none-any', build=123)
        assert str(wm) == expected_contents

    def test_changing_attributes_changes_str(self):
        wm = WheelData()
        wm.generator = 'test'
        wm.root_is_purelib = False
        wm.tags = ['my-test-tag', 'another-test-tag']
        wm.build = 12345

        expected_contents = dedent(
            """\
            Wheel-Version: 1.0
            Generator: test
            Root-Is-Purelib: false
            Tag: my-test-tag
            Tag: another-test-tag
            Build: 12345

            """
        )

        assert str(wm) == expected_contents

    def test_breaks_when_multiple_use_arg_is_given_a_single_string(self):
        wm = WheelData()
        wm.tags = "this is a tag"

        with pytest.raises(AssertionError):
            str(wm)

    def test_no_mistaken_attributes(self):
        wm = WheelData()

        with pytest.raises(AttributeError):
            wm.root_is_platlib = ''

        with pytest.raises(AttributeError):
            wm.tag = ''

        with pytest.raises(AttributeError):
            wm.generated_by = ''

    def test_instances_are_comparable(self):
        assert WheelData() == WheelData()

    def test_different_instances_compare_negatively(self):
        wm_a = WheelData()
        wm_b = WheelData()

        wm_b.build = 10

        assert wm_a != wm_b

    def test_from_str_eqs_by_string(self):
        assert str(WheelData.from_str(str(WheelData()))) == str(WheelData())

    def test_from_str_eqs_by_obj(self):
        assert WheelData.from_str(str(WheelData())) == WheelData()


class TestWheelRecord:
    @pytest.fixture
    def record(self):
        return WheelRecord()

    def test_after_adding_a_file_its_hash_is_available(self, record):
        buf = BytesIO(bytes(1000))
        expected_hash = 'sha256=VBs-naoJsgv4X6Jz5cvT6AGFqk7CmOdl24d0K3ATilM'
        record.update('file', buf)
        assert record.hash_of('file') == expected_hash

    def test_empty_stringifies_to_empty_string(self, record):
        assert str(record) == ''

    def test_stringifies_to_proper_format(self, record):
        size = 1000
        buf = BytesIO(bytes(size))
        expected_hash = 'sha256=VBs-naoJsgv4X6Jz5cvT6AGFqk7CmOdl24d0K3ATilM'
        record.update('file', buf)
        buf.seek(0)
        record.update('another/file', buf)

        # CSV uses CRLF by default, hence \r-s
        expected_record = dedent(
            f"""\
            file,{expected_hash},{size}\r
            another/file,{expected_hash},{size}\r
            """)

        assert str(record) == expected_record

    def test_removing_file_removes_it_from_str_repr(self, record):
        buf = BytesIO(bytes(1000))
        record.update('file', buf)
        record.remove('file')
        assert str(record) == ''

    def test_two_empty_records_are_equal(self):
        assert WheelRecord() == WheelRecord()

    def test_adding_same_files_to_two_records_make_them_equal(self):
        a = WheelRecord()
        b = WheelRecord()
        buf = BytesIO(bytes(1000))
        a.update('file', buf)
        buf.seek(0)
        b.update('file', buf)

    def test_from_empty_str_produces_empty_record(self):
        assert str(WheelRecord.from_str('')) == ''

    def test_stringification_is_stable(self):
        wr = WheelRecord()
        buf = BytesIO(bytes(1000))
        wr.update('file', buf)
        assert str(WheelRecord.from_str(str(wr))) == str(wr)

    def test_has_membership_operator_for_paths_in_the_record(self):
        wr = WheelRecord()
        wr.update('some/particular/path', BytesIO(bytes(1)))
        assert 'some/particular/path' in wr

    def test_throws_with_unknown_hash(self):
        with pytest.raises(UnsupportedHashTypeError):
            WheelRecord(hash_algo='frobnots')

    @pytest.mark.parametrize("hash_algo", ('md5', 'sha1'))
    def test_throw_with_bad_hash(self, hash_algo):
        with pytest.raises(UnsupportedHashTypeError):
            WheelRecord(hash_algo=hash_algo)

    def test_update_throws_on_directory_entry(self):
        with pytest.raises(RecordContainsDirectoryError):
            wr = WheelRecord()
            wr.update('path/to/a/directory/', BytesIO(bytes(1)))

    def test_from_str_throws_on_directory_entry(self):
        with pytest.raises(RecordContainsDirectoryError):
            record_str = "./,sha256=whatever,0"
            WheelRecord.from_str(record_str)
