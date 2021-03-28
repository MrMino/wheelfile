# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Nothing yet

### Changed
- Fixed an issue breaking causing long METADATA lines to be broken into
  multiple shorter lines
- Fixed the production of RECORD files to encode file hashes with base64
  per PEP 376

## [0.0.2] - 2021-01-24
### Added
- Read mode (`'r'`) now works.
- Added `write_data` and `writestr_data` methods to `WheelFile` class. Use
  these methods to write files to `.data/` directory of the wheel.
- Added `build_tag` and `language_tag`, `abi_tag`, and `platform_tag`
  parameters to `WheelFile.__init__`, with their respective properties.
- Tag attributes mentioned above can also be inferred from the filename of the
  specified file.
- Accessing the mode with which the wheelfile was opened is now possible using
  `mode` attribute.

### Changed
- Default tag set of `WheelData` class is now `['py3-none-any']`. Previously,
  universal tag (`"py2.py3-none-any"`) was used.
- Fixed issues with comparing `MetaData` objects that have empty descriptions.
  After parsing a metadata text with empty payload, the returned object has an
  empty string inside description, instead of `None`, which is used by
  `MetaData.__init__` to denote that no description was provided. This means
  that these two values are the effectively the same thing in this context.
  `MetaData.__eq__` now refelcts that.

## [0.0.1] - 2021-01-16
### Added
- First working version of the library.
- It's possible to create wheels from scratch.

[Unreleased]: https://github.com/mrmino/wheelfile/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/mrmino/wheelfile/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/mrmino/wheelfile/releases/tags/v0.0.1
