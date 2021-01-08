import pytest

from wheelfile import __version__ as lib_version, WheelData
from textwrap import dedent


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
        wm = WheelData()
        assert wm.wheel_version == '1.0'

    def test_wheel_version_is_not_settable(self):
        wm = WheelData()
        with pytest.raises(AttributeError):
            wm.wheel_version = '2.0'

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
        wm_a = WheelData()
        wm_b = WheelData()

        assert wm_a == wm_b

    def test_different_instances_compare_negatively(self):
        wm_a = WheelData()
        wm_b = WheelData()

        wm_b.build = 10

        assert wm_a != wm_b
