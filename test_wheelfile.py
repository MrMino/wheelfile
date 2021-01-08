import pytest

from wheelfile import __version__ as lib_version, WheelData, MetaData
from textwrap import dedent


class TestMetadata:
    def test_only_name_and_version_is_required(self):
        md = MetaData(name='my-package', version='1.2.3')
        assert md.name == 'my-package' and md.version == '1.2.3'

    @pytest.fixture
    def metadata(self):
        return MetaData(name='my-package', version='1.2.3')

    def test_metadata_version_is_2_1(self, metadata):
        assert metadata.metadata_version == '2.1'

    def test_metadata_version_is_unchangeable(self, metadata):
        with pytest.raises(AttributeError):
            metadata.metadata_version = '3.0'

    def test_plural_params_default_to_empty_lists(self, metadata):
        # Each of the attribute names here should end with an "s".
        assert (metadata.keywords == []
                and metadata.classifiers == []
                and metadata.project_urls == []
                and metadata.platforms == []
                and metadata.supported_platforms == []
                and metadata.requires_dists == []
                and metadata.requires_externals == []
                and metadata.provides_extras == []
                and metadata.provides_dists == []
                and metadata.obsoletes_dists == [])

    @pytest.fixture
    def full_usage(self):
        description = dedent("""\

            Some

            Long

            Description
        """)
        kwargs = {
            'name': 'package-name',
            'version': '1.2.3',
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
            Obsoletes-Dist: wheel
        """).splitlines()
        expected_payload = dedent("""\


            Some

            Long

            Description
        """)

        lines = str(MetaData(**full_usage)).splitlines()
        header_end_idx = lines.index('')
        headers = lines[:header_end_idx]
        payload = lines[header_end_idx:]
        assert set(headers) == set(expected_headers)
        assert payload == expected_payload

    def test_no_mistaken_attributes(self, metadata):
        with pytest.raises(AttributeError):
            metadata.maintainers = ''

        with pytest.raises(AttributeError):
            metadata.Description = ''

        with pytest.raises(AttributeError):
            metadata.clasifiers = []

    def test_there_are_24_fields_in_this_metadata_version(self):
        assert len(
            [field for field in MetaData.__slots__ if field != '__weakref__']
            + ['metadata_version']
        ) == 24

    @pytest.mark.skip
    def test_keywords_param_accepts_both_a_list_and_comman_separated_str(self):
        pass


class TestWheelData:
    def test_simple_init(self):
        wm = WheelData()
        assert (wm.generator.startswith('wheelfile ')
                and wm.root_is_purelib is True
                and set(wm.tags) == set(['py2-none-any', 'py3-none-any'])
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

    def test_to_dict_returns_without__weakref__(self):
        assert '__weakref__' not in WheelData().to_dict()

    def test_is_dictable_both_ways(self):
        wm = WheelData()
        fd_wm = WheelData(**wm.to_dict())

        assert wm == fd_wm
