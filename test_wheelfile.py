import pytest

from wheelfile import __version__ as lib_version, WheelMeta
from textwrap import dedent


class TestWheelMeta:
    def test_simple_init(self):
        wm = WheelMeta()
        assert (wm.generator.startswith('wheelfile ')
                and wm.root_is_purelib is True
                and set(wm.tags) == set(['py2-none-any', 'py3-none-any'])
                and wm.build is None)

    def test_init_args(self):
        args = {}
        args.update(generator='test', root_is_purelib=False,
                    tags='my-awesome-tag', build=2)
        wm = WheelMeta(**args)

        assert (wm.generator == args['generator']
                and wm.root_is_purelib == args['root_is_purelib']
                and set(wm.tags) == set([args['tags']])
                and wm.build == args['build'])

    def test_tags_are_extended(self):
        wm = WheelMeta(tags=['py2.py3-none-any', 'py2-cp3.cp2-manylinux1'])
        expected_tags = [
            'py2-none-any',
            'py3-none-any',
            'py2-cp3-manylinux1',
            'py2-cp2-manylinux1'
        ]
        assert set(wm.tags) == set(expected_tags)

    def test_single_tag_is_extended(self):
        wm = WheelMeta(tags='py2.py3-none-any')
        expected_tags = [
            'py2-none-any',
            'py3-none-any',
        ]
        assert set(wm.tags) == set(expected_tags)

    def test_wheel_version_is_1_0(self):
        wm = WheelMeta()
        assert wm.wheel_version == '1.0'

    def test_wheel_version_is_not_settable(self):
        wm = WheelMeta()
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
        wm = WheelMeta(tags='py2-none-any', build=123)
        assert str(wm) == expected_contents

    def test_changing_attributes_changes_str(self):
        wm = WheelMeta()

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
