# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

This project adheres to [Semantic
Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- **Dropped support of Python versions lower than Python 3.9.**

## [0.0.8] - 2021-08-03
### Changed
- Since `WheelFile` write methods now have `skipdir=True` default (see below),
  writing recursively from a directory will no longer produce entries for
  directories. This also means, that attempting to write an empty directory (or
  any directory, even with `recursive=False`) is no longer possible, unless
  `skipdir=False` is specified.

  This does not apply to `writestr_*` methods - attempting to write to an
  `arcname` ending in `/` _will_ produce an entry that is visible as a
  directory.
- `WheelFile.validate` will now fail and raise `ValueError` if `WHEEL` build
  tag field (`.wheeldata.build`) contains a value that is different from the
  wheel name (`.build_tag`).

### Added
- `WheelFile.from_wheelfile` - a constructor class-method that makes it
  possible to recreate a wheel and: rename it (change distname, version,
  buildnumber and/or tags), append files to it, change its metadata, etc.
- `WheelFile.METADATA_FILENAMES` - a static field with a set of names of
  metadata files managed by this class.
- `WheelFile.writestr_distinfo` - similar to `write_distinfo`, this is a safe
  shortcut for writing into `.dist-info` directory.
- `WheelFile.__init__` now takes configuration arguments known from `ZipFile`:
  `compression`, `compression`, `allowZip64`, and `strict_timestamps`. They
  work the same way, except that they are keyword only in `WheelFile`, and the
  default value for `compression` is `zipfile.ZIP_DEFLATED`.
- `WheelFile` write methods now take optional `compress_type` and
  `compresslevel` arguments known from `ZipFile`.
- New `skipdir` argument in `WheelFile` write methods: `write`, `write_data`,
  and `write_distinfo`. When `True` (which is the default), these methods will
  not write ZIP entries for directories into the archive.

### Fixed
- Docstring of the `WheelFile.filename` property, which was innacurate.
- `MetaData.from_str` will now correctly unpack `Keywords` field into a list of
  strings, instead of a one-element list with a string containing
  comma-separated tags.

## [0.0.7] - 2021-07-19
### Changed
- Default compression method is now set to `zipfile.ZIP_DEFLATED`.
- Wheels with directory entries in their `RECORD` files will now make
  `WheelFile` raise `RecordContainsDirectoryError`.
- Lazy mode is now allowed, in a very limited version - most methods will still
  raise exceptions, even when the documentation states that lazy mode
  suppresses them.

  Use it by specifying `l` in the `mode` argument, e.g.
  `WheelFile("path/to/wheel", mode='rl')`.  This may be used to read wheels
  generated with previous version of wheelfile, which generated directory
  entries in `RECORD`, making them incompatible with this release.

- In anticipation of an actual implementation, `WheelFile.open()` raises
  `NotImplementedError` now, as it should. Previously only a `def ...: pass`
  stub was present.

### Added
- Implemented `WheelFile.namelist()`, which, similarily to `ZipFile.namelist()`,
  returns a list of archive members, but omits the metadata files which should
  not be written manually: `RECORD`, `WHEEL` and `METADATA`.
- Added `WheelFile.infolist()`. Similarily to the `namelist()` above - it
  returns a `ZipInfo` for each member, but omits the ones corresponding to
  metadata files.
- `RecordContainsDirectoryError` exception class.
- `distinfo_dirname` and `data_dirname` properties, for easier browsing.

### Fixed
- Wheel contents written using `write(..., recursive=True)` no longer contain
  entries corresponding to directories in their `RECORD`.
- Removed a bunch of cosmetic mistakes from exception messages.

## [0.0.6] - 2021-07-01

*This release introduces backwards-incompatible changes in `WheelFile.write`.*
Overall, it makes the method safer and easier to use. One will no longer create
a wheel-bomb by calling `write('./')`.

If you were passing relative paths as `filename` without setting `arcname`, you
probably want to set `resolve=False` for retaining compatibility with this
release. See the "Changed" section.

### Added
- `WheelFile.write` and `WheelFile.write_data` now have a new, keyword-only
  `resolve` argument, that substitutes the default `arcname` with the name of
  the file the path in `filename` points to. This is set to `True` by default
  now.
- New `WheelFile.write_distinfo` method, as a safe shorthand for writing to
  `.dist-info/`.
- New `resolved` utility function.
- New `ProhibitedWriteError` exception class.

### Changed
- `WheelMeta` no longer prohibits reading metadata in versions other than v2.1.
  It uses `2.1` afterwards, and its still not changeable though.
- Since `WheelFile.write` and `WheelFile.write_data` methods have `resolve`
  argument set to `True` by default now, paths are no longer being put verbatim
  into the archive, only the filenames they point to. Set `resolve` to `False`
  to get the old behavior, the one exhibited by `ZipFile.write`.
- Parts of `WheelFile.__init__` have been refactored for parity between "named"
  and "unnamed" modes, i.e. it no longer raises different exceptions based on
  whether it is given a file, path to a directory, path to a file, or an io
  buffer.
- Wheels generated by `WheelFile` are now reproducible. The modification times
  written into the resulting archives using `.write(...)` no longer differ
  between builds consisting of the same, unchanged files - they are taken from
  the files itself.

### Fixed
- `WheelFile` no longer accepts arguments of types other than `Version` and
  `str` in its `version` argument, when an io buffer is given. `TypeError` is
  raised instead.
- `MetaData` started accepting keywords given via single string (comma
  separated). Previously this support was documented, but missing.
- The `wheelfile` package itself should now have the keywords set properly ;).

## [0.0.5] - 2021-05-12
### Fixed
- Added `ZipInfo38` requirement - v0.0.4 has been released without it by
  mistake.

## [0.0.4] - 2021-05-05
### Added
- `WheelFile.write` and `WheelFile.write_data` now accept a `recursive`
  keyword-only argument, which makes both of them recursively add the whole
  directory subtree, if the `filename` argument was pointing at one.

### Changed
- `WheelFile.write` and `WheelFile.write_data` are recursive by default.
- Backported support to python 3.6 (thanks,
  [e2thenegpii](https://github.com/e2thenegpii)!)

## [0.0.3] - 2021-03-28

Big thanks to [e2thenegpii](https://github.com/e2thenegpii) for their
contributions - both of the fixes below came from them.

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

[Unreleased]: https://github.com/mrmino/wheelfile/compare/v0.0.8...HEAD
[0.0.8]: https://github.com/mrmino/wheelfile/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/mrmino/wheelfile/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/mrmino/wheelfile/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/mrmino/wheelfile/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/mrmino/wheelfile/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/mrmino/wheelfile/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/mrmino/wheelfile/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/mrmino/wheelfile/releases/tags/v0.0.1
