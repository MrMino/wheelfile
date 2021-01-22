# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Added `write_data` and `writestr_data` methods to `WheelFile` class. Use
  these methods to write files to `.data/` directory of the wheel.
- Added `build_tag` and `language_tag` parameters to `WheelFile.__init__`, with
  their respective properties.

### Changed
- Default tag set of `WheelData` class is now `['py3-none-any']`. Previously,
  universal tag was used.

## [0.0.1] - 2021-01-16
### Added
- First working version of the library.
- It's possible to create wheels from scratch.

[unreleased]: https://github.com/mrmino/wheelfile/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/mrmino/wheelfile/releases/tags/v0.0.1
