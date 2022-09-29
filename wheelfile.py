# Copyright (c) 2020-2021 Blazej Michalik
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""API for handling ".whl" files.

Use :class:`WheelFile` to create or read a wheel.

Managing metadata is done via `metadata`, `wheeldata`, and `record` attributes.
See :class:`MetaData`, :class:`WheelData`, and :class:`WheelRecord` for
documentation of the objects returned by these attributes.

Example
-------
Here's how to create a simple package under a specific directory path::

    with WheelFile('path/to/directory/', mode='w'
                   distname="mywheel", version="1") as wf:
        wf.write('path/to/a/module.py', arcname="mywheel.py")
"""

import os
import csv
import io
import sys
import hashlib
import base64
import warnings

from string import ascii_letters, digits
from pathlib import Path
from collections import namedtuple
from inspect import signature
from packaging.tags import parse_tag
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from email.message import EmailMessage
from email.policy import EmailPolicy
from email import message_from_string

if sys.version_info >= (3, 8):
    import zipfile
else:
    import zipfile38 as zipfile

from typing import Optional, Union, List, Dict, IO, BinaryIO

__version__ = '0.0.8-1'


# TODO: ensure that writing into `file` arcname and then into `file/not/really`
# fails.
# TODO: the file-directory confusion should also be checked on the WheelRecord
# level, and inside WheelFile.validate()

# TODO: idea: Corrupted class: denotes that something is present, but could not
# be parsed. Would take a type and contents to parse, compare falsely to
# the objects of given type, and not compare with anything else.
# Validate would raise errors with messages about parsing if it finds something
# corrupted, and about missing file otherwise.

# TODO: change AssertionErrors to custom exceptions?
# TODO: idea - install wheel - w/ INSTALLER file
# TODO: idea - wheel from an installed distribution?

# TODO: fix inconsistent referencing style of symbols in docstrings

# TODO: parameters for path-like values should accept bytes

# TODO: idea - wheeldata -> wheelinfo, but it contradicts the idea below
# TODO: idea - might be better to provide WheelInfo objects via a getinfo(),
# which would inherit from ZipInfo but also cointain the hash from the RECORD.
# It would simplify the whole implementation.

# TODO: fix usage of UnnamedDistributionError and ValueError - it is ambiguous


def _slots_from_params(func):
    """List out slot names based on the names of parameters of func

    Usage: __slots__ = _slots_from_signature(__init__)
    """
    funcsig = signature(func)
    slots = list(funcsig.parameters)
    slots.remove('self')
    return slots


# TODO: accept packaging.requirements.Requirement in requires_dist, fix this in
# example, ensure such objects are converted on __str__
# TODO: reimplement using dataclasses
# TODO: add version to the class name, reword the "Note"
# name regex for validation: ^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$
# TODO: helper-function or consts for description_content_type
# TODO: parse version using packaging.version.parse?
# TODO: values validation
# TODO: validate provides_extras ↔ requires_dists?
# TODO: validate values charset-wise
# TODO: ensure name is the same as wheelfile namepath
# TODO: PEP-643 - v2.2
# TODO: don't raise invalid version, assign a degenerated version object instead
class MetaData:
    """Implements Wheel Metadata format v2.1.

    Descriptions of parameters based on
    https://packaging.python.org/specifications/core-metadata/. All parameters
    are keyword only. Attributes of objects of this class follow parameter
    names.

    All parameters except "name" and "version" are optional.

    Note
    ----
    Metadata-Version, the metadata format version specifier, is unchangable.
    Version "2.1" is used.

    Parameters
    ----------
    name
        Primary identifier for the distribution that uses this metadata. Must
        start and end with a letter or number, and consists only of ASCII
        alphanumerics, hyphen, underscore, and period.

    version
        A string that contains PEP-440 compatible version identifier.

        Can be specified using packaging.version.Version object, or a string,
        where the latter is always converted to the former.

    summary
        A one-line sentence describing this distribution.

    description
        Longer text that describes this distribution in detail. Can be written
        using plaintext, reStructuredText, or Markdown (see
        "description_content_type" parameter below).

        The string given for this field should not include RFC 822 indentation
        followed by a "|" symbol. Newline characters are permitted

    description_content_type
        Defines content format of the text put in the "description" argument.
        The field value should follow the following structure:

            <type/subtype>; charset=<charset>[; <param_name>=<param value> ...]

        Valid type/subtype strings are:
            - text/plain
            - text/x-rst
            - text/markdown

        For charset parameter, the only legal value is UTF-8.

        For text/markdown, parameter "variant=<variant>" specifies variant of
        the markdown used. Currently recognized variants include "GFM" and
        "CommonMark".

        Examples:

            Description-Content-Type: text/markdown; charset=UTF-8; variant=GFM

            Description-Content-Type: text/markdown

    keywords
        List of search keywords for this distribution. Optionally a single
        string literal with keywords separated by commas.

        Note: despite the name being a plural noun, the specification defines
        this field as a single-use field. In this implementation however, the
        value of the attribute after instance initialization is a list of
        strings, and conversions to and from string follow the spec - they
        require a comma-separated list.

    classifiers
        List PEP-301 classification values for this distribution, optionally
        followed by a semicolon and an environmental marker.

        Example of a classifier:

            Operating System :: Microsoft :: Windows :: Windows 10

    author
        Name and, optionally, contact information of the original author of the
        distribution.

    author_email
        Email address of the person specified in the "author" parameter. Format
        of this field must follow the format of RFC-822 "From:" header field.

    maintainer
        Name and, optionally, contact information of person currently
        maintaining the project to which this distribution belongs to.

        Omit this parameter if the author and current maintainer is the same
        person.

    maintainer_email
        Email address of the person specified in the "maintainer" parameter.
        Format of this field must follow the format of RFC-822 "From:" header
        field.

        Omit this parameter if the author and current maintainer is the same
        person.

    license
        Text of the license that covers this distribution. If license
        classifier is used, this parameter may be omitted or used to specify the
        particular version of the intended legal text.

    home_page
        URL of the home page for this distribution (project).

    download_url
        URL from which this distribution (in this version) can be downloaded.

    project_urls
        List of URLs with labels for them, in the following format:

            <label>, <url>

        The label must be at most 32 characters.

        Example of an item of this list:

            Repository, https://github.com/MrMino/wheelfile

    platforms
        List of strings that signify supported operating systems. Use only if
        an OS cannot be listed by using a classifier.

    supported_platforms
        In binary distributions list of strings, each defining an operating
        system and a CPU for which the distribution was compiled.

        Semantics of this field aren't formalized by metadata specifications.

    requires_python
        PEP-440 version identifier, that specifies the set Python language
        versions that this distribution is compatible with.

        Some package management tools (most notably pip) use the value of this
        field to filter out installation candidates.

        Example:

            ~=3.5,!=3.5.1,!=3.5.0

    requires_dists
        List of PEP-508 dependency specifiers (think line-split contents of
        requirements.txt).

    requires_externals
        List of system dependencies that this distribution requires.

        Each item is a string with a name of the dependency optionally followed
        by a version (in the same way items in "requires_dists") are specified.

        Each item may end with a semicolon followed by a PEP-496 environment
        markers.

    provides_extras
        List of names of optional features provided by a distribution. Used to
        specify which dependencies should be installed depending on which of
        these optional features are requested.

        For example, if you specified "network" and "ssh" as optional features,
        the following requirement specifier can be used in "requires_externals"
        list to indicate, that the "paramiko" dependency should only be
        installed when "ssh" feature is requested:

            paramiko; extra == "ssh"

        or

            paramiko[ssh]

        If a dependency is required by multiple features, the features can be
        specified in a square brackets, separated by commas:

            ipython[repl, jupyter_kernel]

        Specifying an optional feature without using it in "requires_externals"
        is considered invalid.

        Feature names "tests" and "doc" are reserved in their semantics. They
        can be used for dependencies of automated testing or documentation
        generation.

    provides_dists
        List of names of other distributions contained within this one. Each
        entry must follow the same format that entries in "requires_dists" list
        do.

        Different distributions may use a name that does not correspond to any
        particular project, to indicate a capability to provide a certain
        feature, e.g. "relational_db" may be used to say that a project
        provides relational database capabilities

    obsoletes_dists
        List of names of distributions obsoleted by installing this one,
        indicating that they should not coexist in a single environment with
        this one. Each entry must follow the same format that entries in
        "requires_dists" list do.
    """
    def __init__(self, *, name: str, version: Union[str, Version],
                 summary: Optional[str] = None,
                 description: Optional[str] = None,
                 description_content_type: Optional[str] = None,
                 keywords: Union[List[str], str, None] = None,
                 classifiers: Optional[List[str]] = None,
                 author: Optional[str] = None,
                 author_email: Optional[str] = None,
                 maintainer: Optional[str] = None,
                 maintainer_email: Optional[str] = None,
                 license: Optional[str] = None,
                 home_page: Optional[str] = None,
                 download_url: Optional[str] = None,
                 project_urls: Optional[List[str]] = None,
                 platforms: Optional[List[str]] = None,
                 supported_platforms: Optional[List[str]] = None,
                 requires_python: Optional[str] = None,
                 requires_dists: Optional[List[str]] = None,
                 requires_externals: Optional[List[str]] = None,
                 provides_extras: Optional[List[str]] = None,
                 provides_dists: Optional[List[str]] = None,
                 obsoletes_dists: Optional[List[str]] = None
                 ):
        # self.metadata_version = '2.1' by property
        self.name = name
        self.version = Version(version) if isinstance(version, str) else version

        self.summary = summary
        self.description = description
        self.description_content_type = description_content_type
        if keywords is None:
            keywords = []
        self.keywords = (keywords if isinstance(keywords, list)
                         else keywords.split(','))
        self.classifiers = classifiers or []

        self.author = author
        self.author_email = author_email
        self.maintainer = maintainer
        self.maintainer_email = maintainer_email

        self.license = license

        self.home_page = home_page
        self.download_url = download_url
        self.project_urls = project_urls or []

        self.platforms = platforms or []
        self.supported_platforms = supported_platforms or []

        self.requires_python = requires_python
        self.requires_dists = requires_dists or []
        self.requires_externals = requires_externals or []
        self.provides_extras = provides_extras or []
        self.provides_dists = provides_dists or []
        self.obsoletes_dists = obsoletes_dists or []

    __slots__ = _slots_from_params(__init__)

    @property
    def metadata_version(self):
        return self._metadata_version
    _metadata_version = '2.1'

    @classmethod
    def field_is_multiple_use(cls, field_name: str) -> bool:
        field_name = field_name.lower().replace('-', '_').rstrip('s')
        if field_name in cls.__slots__ or field_name == 'keyword':
            return False
        if field_name + 's' in cls.__slots__:
            return True
        else:
            raise ValueError(f"Unknown field: {repr(field_name)}.")

    @classmethod
    def _field_name(cls, attribute_name: str) -> str:
        if cls.field_is_multiple_use(attribute_name):
            attribute_name = attribute_name[:-1]
        field_name = attribute_name.title()
        field_name = field_name.replace('_', '-')
        field_name = field_name.replace('Url', 'URL')
        field_name = field_name.replace('-Page', '-page')
        field_name = field_name.replace('-Email', '-email')
        return field_name

    @classmethod
    def _attr_name(cls, field_name: str) -> str:
        if cls.field_is_multiple_use(field_name):
            field_name += 's'
        return field_name.lower().replace('-', '_')

    def __str__(self) -> str:
        m = EmailMessage(EmailPolicy(max_line_length=None))
        m.add_header("Metadata-Version", self.metadata_version)
        for attr_name in self.__slots__:
            content = getattr(self, attr_name)
            if not content:
                continue

            field_name = self._field_name(attr_name)

            if field_name == 'Keywords':
                content = ','.join(content)
            elif field_name == "Version":
                content = str(content)

            if self.field_is_multiple_use(field_name):
                assert not isinstance(content, str), (
                    f"Single string in multiple use attribute: {attr_name}"
                )

                for value in content:
                    m.add_header(field_name, value)
            elif field_name == 'Description':
                m.set_payload(content)
            else:
                assert isinstance(content, str), (
                    f"Expected string, got {type(content)} instead: {attr_name}"
                )
                m.add_header(field_name, content)
        return str(m)

    def __eq__(self, other):
        if isinstance(other, MetaData):
            # Having None as a description is the same as having an empty string
            # in it. The former is put there by having an Optional[str]
            # argument, the latter is there due to semantics of email-style
            # parsing.
            # Ensure these two values compare equally in the description.
            mine = '' if self.description is None else self.description
            theirs = '' if other.description is None else other.description
            descriptions_equal = (mine == theirs)

            return (all(getattr(self, field) == getattr(other, field)
                        for field in self.__slots__ if field != 'description')
                    and descriptions_equal)
        else:
            return NotImplemented

    @classmethod
    def from_str(cls, s: str) -> 'MetaData':
        m = message_from_string(s)

        # TODO: validate this when the rest of the versions are implemented
        # assert m['Metadata-Version'] == cls._metadata_version

        del m['Metadata-Version']

        args = {}
        for field_name in m.keys():
            attr = cls._attr_name(field_name)
            if not attr.endswith('s'):
                args[attr] = m.get(field_name)
            else:
                if field_name == "Keywords":
                    args[attr] = m.get(field_name).split(',')
                else:
                    args[attr] = m.get_all(field_name)

        args['description'] = m.get_payload()

        return cls(**args)


# TODO: reimplement using dataclasses?
# TODO: add version to the class name, reword the "Note"
# TODO: values validation
class WheelData:
    """Implements .dist-info/WHEEL file format.

    Descriptions of parameters based on PEP-427. All parameters are keyword
    only. Attributes of objects of this class follow parameter names.

    Note
    ----
    Wheel-Version, the wheel format version specifier, is unchangeable. Version
    "1.0" is used.

    Parameters
    ----------
    generator
        Name and (optionally) version of the generator that generated the wheel
        file. By default, "wheelfile {__version__}" is used.

    root_is_purelib
        Defines whether the root of the wheel file should be first unpacked into
        purelib directory (see distutils.command.install.INSTALL_SCHEMES).

    tags
        See PEP-425 - "Compatibility Tags for Built Distributions". Either a
        single string denoting one tag or a list of tags. Tags may contain
        compressed tag sets, in which case they will be expanded.

        By default, "py3-none-any" is used.

    build
        Optional build number. Used as a tie breaker when two wheels have the
        same version.
    """
    def __init__(self, *,
                 generator: str = 'wheelfile ' + __version__,
                 root_is_purelib: bool = True,
                 tags: Union[List[str], str] = 'py3-none-any',
                 build: Optional[int] = None):
        # self.wheel_version = '1.0' by property
        self.generator = generator
        self.root_is_purelib = root_is_purelib
        self.tags = self._extend_tags(
            tags if isinstance(tags, list) else [tags]
        )
        self.build = build
    __slots__ = _slots_from_params(__init__)

    @property
    def wheel_version(self) -> str:
        return '1.0'

    def _extend_tags(self, tags: List[str]) -> List[str]:
        extended_tags = []
        for tag in tags:
            extended_tags.extend([str(t) for t in parse_tag(tag)])
        return extended_tags

    def __str__(self) -> str:
        # TODO Custom exception? Exception message?
        assert isinstance(self.generator, str), (
            f"'generator' must be a string, got {type(self.generator)} instead"
        )
        assert isinstance(self.root_is_purelib, bool), (
            f"'root_is_purelib' must be a boolean, got"
            f"{type(self.root_is_purelib)} instead"
        )
        assert isinstance(self.tags, list), (
            f"Expected a list in 'tags', got {type(self.tags)} instead"
        )
        assert self.tags, "'tags' cannot be empty"
        assert isinstance(self.build, int) or self.build is None, (
            f"'build' must be an int, got {type(self.build)} instead"
        )

        m = EmailMessage()
        m.add_header("Wheel-Version", self.wheel_version)
        m.add_header("Generator", self.generator)
        m.add_header("Root-Is-Purelib", "true"
                     if self.root_is_purelib else "false")
        for tag in self.tags:
            m.add_header("Tag", tag)
        if self.build is not None:
            m.add_header("Build", str(self.build))

        return str(m)

    @classmethod
    def from_str(cls, s: str) -> 'WheelData':
        m = message_from_string(s)
        assert m['Wheel-Version'] == '1.0'
        args = {
            'generator': m.get('Generator'),
            'root_is_purelib': bool(m.get('Root-Is-Purelib')),
            'tags': m.get_all('Tag'),
        }

        if 'build' in m:
            args['build'] = int(m.get('build'))

        return cls(**args)

    def __eq__(self, other):
        if isinstance(other, WheelData):
            return all(getattr(self, f) == getattr(other, f)
                       for f in self.__slots__)
        else:
            return NotImplemented


# TODO: add_entry method, that raises if entry for a path already exists
# TODO: leave out hashes of *.pyc files?
class WheelRecord:
    """Contains logic for creation and modification of RECORD files.

    Keeps track of files in the wheel and their hashes.

    For the full spec, see PEP-376 "RECORD" section, PEP-627,
    "The .dist-info directory" section of PEP-427, and
    https://packaging.python.org/specifications/recording-installed-packages/.
    """
    HASH_BUF_SIZE = 65536

    _RecordEntry = namedtuple('_RecordEntry', 'path hash size')

    def __init__(self, hash_algo: str = 'sha256'):
        self._records: Dict[str, WheelRecord._RecordEntry] = {}
        self._hash_algo = ""
        self.hash_algo = hash_algo

    @property
    def hash_algo(self) -> str:
        """Hash algorithm to use to generate RECORD file entries"""
        return self._hash_algo

    @hash_algo.setter
    def hash_algo(self, value: str):
        # per PEP-376
        if value not in hashlib.algorithms_guaranteed:
            raise UnsupportedHashTypeError(
                f"{repr(value)} is not a valid record hash."
            )
        # per PEP 427
        if value in ('md5', 'sha1'):
            raise UnsupportedHashTypeError(
                f"{repr(value)} is a forbidden hash type."
            )

        # PEP-427 says the RECORD hash must be sha256 or better.  Does that mean
        # hashes such as sha224 are forbidden as well though not specifically
        # called out?

        self._hash_algo = value

    def hash_of(self, arcpath) -> str:
        """Return the hash of a file in the archive this RECORD describes


        Parameters
        ----------
        arcpath
            Location of the file inside the archive.

        Returns
        -------
        str
            String in the form <algorithm>=<base64_str>, where algorithm is the
            name of the hashing agorithm used to generate the hash (see
            hash_algo), and base64_str is a string containing a base64 encoded
            version of the hash with any trailing '=' removed.
        """
        return self._records[arcpath].hash

    def __str__(self) -> str:
        buf = io.StringIO()
        records = csv.DictWriter(buf, fieldnames=self._RecordEntry._fields)
        for entry in self._records.values():
            records.writerow(entry._asdict())
        return buf.getvalue()

    @classmethod
    def from_str(cls, s) -> 'WheelRecord':
        record = WheelRecord()
        buf = io.StringIO(s)
        reader = csv.DictReader(buf, cls._RecordEntry._fields)
        for row in reader:
            entry = cls._RecordEntry(**row)

            if entry.path.endswith("/"):
                raise RecordContainsDirectoryError(
                    "RECORD of this wheel contains an entry with for a "
                    "directory: {repr(entry.path)}."
                )

            record._records[entry.path] = entry
        return record

    def update(self, arcpath: str, buf: IO[bytes]):
        """Add a record entry for a file in the archive.

        Parameters
        ----------
        arcpath
            Path in the archive of the file that the entry describes.

        buf
            Buffer from which the data will be read in HASH_BUF_SIZE chunks.
            Must be fresh, i.e. seek(0)-ed.

        Raises
        ------
        RecordContainsDirectoryError
            If ``arcpath`` is a path to a directory.
        """
        assert buf.tell() == 0, (
            f"Stale buffer given - current position: {buf.tell()}."
        )
        assert not arcpath.endswith('.dist-info/RECORD'), (
            f"Attempt to add an entry for a RECORD file to the RECORD: "
            f"{repr(arcpath)}."
        )

        if arcpath.endswith("/"):
            raise RecordContainsDirectoryError(
                f"Attempt to add an entry for a directory: {repr(arcpath)}"
            )

        self._records[arcpath] = self._entry(arcpath, buf)

    def remove(self, arcpath: str):
        del self._records[arcpath]

    def _entry(self, arcpath: str, buf: IO[bytes]) -> _RecordEntry:
        size = 0
        hasher = getattr(hashlib, self.hash_algo)()
        while True:
            data = buf.read(self.HASH_BUF_SIZE)
            size += len(data)
            if not data:
                break
            hasher.update(data)
        hash_entry = f"{hasher.name}={self._hash_encoder(hasher.digest())}"
        return self._RecordEntry(arcpath, hash_entry, size)

    @staticmethod
    def _hash_encoder(data: bytes) -> str:
        """
        Encode a file hash per PEP 376 spec

        From the spec:
        The hash is either the empty string or the hash algorithm as named in
        hashlib.algorithms_guaranteed, followed by the equals character =,
        followed by the urlsafe-base64-nopad encoding of the digest
        (base64.urlsafe_b64encode(digest) with trailing = removed).
        """
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode('ascii')

    def __eq__(self, other):
        if isinstance(other, WheelRecord):
            return str(self) == str(other)
        else:
            return NotImplemented

    def __contains__(self, path):
        return path in self._records


class UnsupportedHashTypeError(ValueError):
    """The given hash name is not allowed by the spec."""


class RecordContainsDirectoryError(ValueError):
    """Record contains an entry path that ends with a slash (a directory)."""


class BadWheelFileError(ValueError):
    """The given file cannot be interpreted as a wheel nor fixed."""


class UnnamedDistributionError(BadWheelFileError):
    """Distribution name cannot be deduced from arguments."""


class ProhibitedWriteError(ValueError):
    """Writing into given arcname would result in a corrupted package."""


def resolved(path: Union[str, Path]) -> str:
    """Get the name of the file or directory the path points to.

    This is a convenience function over the functionality provided by
    `resolve` argument of `WheelFile.write` and similar methods. Since
    `resolve=True` is ignored when `arcname` is given, it is impossible to add
    arbitrary prefix to `arcname` without resolving the path first - and this
    is what this function provides.

    Using this, you can have both custom `arcname` prefix and the "resolve"
    functionality, like so::

        wf = WheelFile(...)
        wf.write(some_path, arcname="arc/dir/" + resolved(some_path))

    Parameters
    ----------
    path
        Path to resolve.


    Returns
    -------
    str
        The name of the file or directory the `path` points to.
    """
    return os.path.basename(os.path.abspath(path))


# TODO: read
# TODO: read_distinfo
# TODO: read_data
# TODO: prevent arbitrary writes to METADATA, WHEEL, and RECORD - or make sure
# the writes are reflected internally
# TODO: prevent adding .dist-info directories if there's one already there
# TODO: ensure distname and varsion have no weird characters (!slashes!)
# TODO: debug propery, as with ZipFile.debug
# TODO: comment property
# TODO: append mode
# TODO: writing inexistent metadata in lazy mode
# TODO: better repr
# TODO: comparison operators for comparing version + build number
class WheelFile:
    """An archive that follows the wheel specification.

    Used to read, create, validate, or modify `.whl` files.

    Can be used as a context manager, in which case `close()` is called upon
    exiting the context.

    Attributes
    ----------
    filename : str
        If initialized with:
            - An IO buffer: the filename that the wheel would have after saving
              it onto filesystem.
            - A path to a directory: the path to the wheel, composed from its
              the given path and the filename generated using the parameters
              given to `__init__`.
            - A path to a file: that path, even if it is not compliant with the
              spec (in lazy mode).

         **Returned path is not resolved, and so might be relative and/or
         contain `../` and `./` segments**.

    distname : str
        Name of the distribution (project). Either given to __init__()
        explicitly or inferred from its file_or_path argument.

    version : packaging.version.Version
        Version of the distribution. Either given to __init__() explicitly or
        inferred from its file_or_path argument.

    build_tag : Optional[int]
        Distribution's build number. Either given to __init__() explicitly or
        inferred from its file_or_path argument, otherwise `None` in lazy mode.

    language_tag : str
        Interpretter implementation compatibility specifier. See PEP-425 for
        the full specification. Either given to __init__() explicitly or
        inferred from its file_or_path argument otherwise an empty string in
        lazy mode.

    abi_tag : str
        ABI compatibility specifier. See PEP-425 for the full specification.
        Either given to __init__() explicitly or inferred from its file_or_path
        argument, otherwise an empty string in lazy mode.

    platform_tag : str
        Platform compatibility specifier. See PEP-425 for the full
        specification. Either given to __init__() explicitly or inferred from
        its file_or_path argument, otherwise an empty string in lazy mode.

    record : Optional[WheelRecord]
        Current state of .dist-info/RECORD file.

        When reading wheels in lazy mode, if the file does not exist or is
        misformatted, this attribute becomes None.

        In non-lazy modes this file is always read & validated on
        initialization.
        In write and exclusive-write modes, written to the archive on close().

    metadata : Optional[MetaData]
        Current state of .dist-info/METADATA file.

        Values from `distname` and `version` are used to provide required
        arguments when the file is created from scratch by `__init__()`.

        When reading wheels in lazy mode, if the file does not exist or is
        misformatted, this attribute becomes None.

        In non-lazy modes this file is always read & validated on
        initialization.
        In write and exclusive-write modes, written to the archive on close().

    wheeldata : Optional[WheelData]
        Current state of .dist-info/WHEELDATA file.

        Values from `build_tag`, `language_tag`, `abi_tag`, `platform_tag`, or
        their substitutes inferred from the filename are used to initialize
        this object.

        When reading wheels in lazy mode, if the file does not exist or is
        misformatted, this attribute becomes None.

        In non-lazy modes this file is always read & validated on
        initialization.
        In write and exclusive-write modes, written to the archive on close().

    distinfo_dirname
        Name of the ``.dist-info`` directory inside the archive wheel,
        without the trailing slash.

    data_dirname
        Name of the ``.data`` directory inside the archive wheel, without
        the trailing slash.

    closed : bool
        True if the underlying `ZipFile` object is closed, false otherwise.
    """
    VALID_DISTNAME_CHARS = set(ascii_letters + digits + '._')
    METADATA_FILENAMES = {"WHEEL", "METADATA", "RECORD"}

    # TODO: implement lazy mode
    # TODO: in lazy mode, log reading/missing metadata errors
    # TODO: warn on 'w' modes if filename does not end with .whl
    def __init__(
        self,
        file_or_path: Union[str, Path, BinaryIO] = './',
        mode: str = 'r',
        *,
        distname: Optional[str] = None,
        version: Optional[Union[str, Version]] = None,
        build_tag: Optional[Union[int, str]] = None,
        language_tag: Optional[str] = None,
        abi_tag: Optional[str] = None,
        platform_tag: Optional[str] = None,
        compression: int = zipfile.ZIP_DEFLATED,
        allowZip64: bool = True,
        compresslevel: Optional[int] = None,
        strict_timestamps: bool = True,
    ) -> None:
        # FIXME: Validation does not fail if filename differs from generated
        # filename, yet it validates the extension
        """Open or create a wheel file.

        In write and exclusive-write modes, if `file_or_path` is not specified,
        it is assumed to be the current directory. If the specified path is a
        directory, the wheelfile will be created inside it, with filename
        generated using the values given via `distname`, `version`,
        `build_tag`, `language_tag`, `abi_tag`, and `platfrom_tag` arguments.
        Each of these parameters is stored in a read-only property of the same
        name.
        If `file_or_path` is a path to a file, the wheel will be created
        under the specified path.

        If lazy mode is not specified:

            - In read and append modes, the file is validated using validate().
              Contents of metadata files inside .dist-info directory are read
              and converted into their respective object representations (see
              "metadata", "wheeldata", and "record" attributes).
            - In write and exclusive-write modes, object representations for
              each metadata file are created from scratch. They will be written
              to each of their respective .dist-info/ files on close().

        To skip the validation, e.g. if you wish to fix a misformated wheel,
        use lazy mode ('l' - see description of the "mode" parameter).

        In lazy mode, if the opened file does not contain WHEEL, METADATA, or
        RECORD (which is optional as per PEP-627), the attributes corresponding
        to the missing data structures will be set to None.

        If any of the metadata files cannot be read due to a wrong format, they
        are considered missing.

        Filename tags are only inferred if the filename contains 5 or 6
        segments inbetween `'-'` characters. Otherwise, if any tag argument is
        omitted, its attribute is set to an empty string.

        If the archive root contains a directory with a name ending with
        '.dist-info', it is considered to be *the* metadata directory for the
        wheel, even if the given/inferred distname and version do not match its
        name.

        If the archive already contains either one of the aforementioned files,
        they are read, but are not checked for consistency. Use validate() to
        check whether there are errors, and fix() to fix them.

        There are currently 2 classes of errors which completely prevent a well
        formatted zip file from being read by this class:

            - Unknown/incorrect distribution name/version - when the naming
              scheme is violated in a way that prevents inferring these values
              and the user hasn't provided these values, or provided ones that
              do not conform to the specifications. In such case, the scope of
              functioning features of this class would be limited to that of a
              standard ZipFile, and is therefore unsupported.
            - When there are multiple .data or .dist-info directories. This
              would mean that the class would have to guess which are the
              genuine ones - and we refuse the temptation to do that (see "The
              Zen of Python").

        In other words, this class is liberal in what it accepts, but very
        conservative in what it does (A.K.A. the robustness principle).

        Note
        ----
        Despite all of this, THERE ARE NO GUARANTEES being made as to whether a
        misformatted file can be read or fixed by this class, and even if it is
        currently, whether it will still be the case in the future versions.

        Parameters
        ----------
        file_or_path
            Path to the file to open/create or a file-like object to use.

        mode
            See zipfile.ZipFile docs for the list of available modes.

            In the read and append modes, the file given has to contain proper
            PKZIP-formatted data.

            Adding "l" to the mode string turns on the "lazy mode". This
            changes the behavior on initialization (see above), the behavior of
            close() (see its docstring for more info), makes the archive
            modifying methods refrain from refreshing the record & writing it
            to the archive.

            Lazy mode should only be used in cases where a misformatted wheels
            have to be read or fixed.

        distname
            Name of the distribution for this wheelfile.

            If omitted, the name will be inferred from the filename given in
            the path. If a file-like object is given instead of a path, it will
            be inferred from its "name" attribute.

            The class requires this information, as it's used to infer the name
            of the directory in the archive in which metadata should reside.

            This argument should be understood as an override for the values
            calculated from the object given in "file_or_path" argument.  It
            should only be necessary when a file is read from memory or has a
            misformatted name.

            Should be composed of alphanumeric characters and underscores only.
            Must not be an empty string.

            See the description of "distname" attribute for more information.

        version
            Version of the distribution in this wheelfile. Follows the same
            semantics as "distname".

            The given value must be compliant with PEP-440 version identifier
            specification.

            See the description of "version" attribute for more information.

        build
            Optional build number specifier for the distribution.

            See `WheelData` docstring for information about semantics of this
            field.

            If lazy mode is not specified, this value must be an integer or a
            string that converts to one. Otherwise no checks for this value are
            performed.

        language_tag
            Language implementation specification. Used to distinguish
            between distributions targetted at different versions of
            interpreters.

            The given value should be in the same form as the ones appearing
            in wheels' filenames.

            Defaults to `'py3'`, but only if an unnamed or a directory target
            was given.

        abi_tag
            In distributions that utilize compiled binaries, specifies the
            version of the ABI that the binaries in the wheel are compatible
            with.

            The given value should be in the same form as the ones appearing
            in wheels' filenames.

            Defaults to `'none'`, but only if an unnamed or a directory target
            was given.

        platform_tag
            Used to specify platforms that the distribution is compatible with.

            The given value should be in the same form as the ones appearing
            in wheels' filenames.

            Defaults to `'any'`, but only if an unnamed or a directory target
            was given.

        compression
            Compression method to use. By default `zipfile.ZIP_DEFLATED` is
            used.

            See `zipfile.ZipFile` documentation for the full description. This
            argument differs from its `ZipFile` counterpart in that here it is
            keyword-only, and the default value is different.

        allowZip64
            Flag used to indicate whether ZIP64 extensions should be used.

            See `zipfile.ZipFile` documentation for the full description. This
            argument differs from its `ZipFile` counterpart in that here it is
            keyword-only.

        compresslevel
            Compression level to use when writing to the archive.

            See `zipfile.ZipFile` documentation for the full description. This
            argument differs from its `ZipFile` counterpart in that here it is
            keyword-only

        strict_timestamps
            When `True`, files with modification times older than 1980-01-01 or
            newer than 2107-12-31 are allowed. Keyword only.

            See `zipfile.ZipFile` documentation for the full description. This
            argument differs from its `ZipFile` counterpart in that here it is
            keyword-only.

        Raises
        ------
        UnnamedDistributionError
            Raised if the distname or version cannot be inferred from the
            given arguments.

            E.g. when the path does not contain the version, or the
            file-like object has no "name" attribute to get the filename from,
            and the information wasn't provided via other arguments.

        BadWheelFileError
            Raised if the archive contains multiple '.dist-info' or '.data'
            directories.

        zipfile.BadZipFile
            If given file is not a proper zip.
        """
        assert not isinstance(file_or_path, io.TextIOBase), (
            "Text buffer given where a binary one was expected."
        )

        if 'a' in mode:
            # Requires rewrite feature
            raise NotImplementedError(
                "Append mode is not supported yet"
            )

        if 'l' in mode:
            warnings.warn(RuntimeWarning(
                "Lazy mode is not fully implemented yet. "
                "Methods of this class may raise exceptions where "
                "documentation states lazy mode will suppress them."
            ))

        # TODO: this should be read-only prop
        self.mode = mode

        # These might be None in case a corrupted wheel is read in lazy mode
        self.wheeldata: Optional[WheelData] = None
        self.metadata: Optional[MetaData] = None
        self.record: Optional[WheelRecord] = None

        self._strict_timestamps = strict_timestamps

        if isinstance(file_or_path, str):
            file_or_path = Path(file_or_path)

        # TODO if value error, set build_tag to degenerated version, that
        # compares with Version in a way that makes Version the higher one.
        build_tag = int(build_tag) if build_tag is not None else None

        if self._is_unnamed_or_directory(file_or_path):
            self._require_distname_and_version(distname, version)

        filename = self._get_filename(file_or_path)
        self._pick_a_distname(filename, given_distname=distname)
        self._pick_a_version(filename, given_version=version)
        self._pick_tags(
            filename, build_tag, language_tag, abi_tag, platform_tag
        )

        if self._is_unnamed_or_directory(file_or_path):
            assert distname is not None and version is not None  # For Mypy
            self._generated_filename = self._generate_filename(
                self._distname, self._version, self._build_tag,
                self._language_tag, self._abi_tag, self._platform_tag
            )
        else:
            self._generated_filename = ''

        if isinstance(file_or_path, Path):
            file_or_path /= self._generated_filename

        # FIXME: the file is opened before validating the arguments, so this
        # litters empty and corrupted wheels if any arg is wrong.
        self._zip = zipfile.ZipFile(file_or_path, mode.strip('l'),
                                    compression=compression,
                                    allowZip64=allowZip64,
                                    compresslevel=compresslevel,
                                    strict_timestamps=strict_timestamps)

        # Used by distinfo_dirname, data_dirname, and _distinfo_path
        self._distinfo_prefix: Optional[str] = None

        if 'w' in mode or 'x' in mode:
            self._initialize_distinfo()
        else:
            self._distinfo_prefix = self._find_distinfo_prefix()
            self._read_distinfo()

        if 'l' not in mode:
            self.validate()

    class _Sentinel:
        """Used in `from_wheelfile` to specify that a given paramter should be
        copied from the source object.
        """
    _unspecified = _Sentinel()

    @classmethod
    def from_wheelfile(
        cls, wf: "WheelFile",
        file_or_path: Union[str, Path, BinaryIO] = './',
        mode: str = 'w',
        *,
        distname: Union[str, None, _Sentinel] = _unspecified,
        version: Union[str, Version, None, _Sentinel] = _unspecified,
        build_tag: Union[int, str, None, _Sentinel] = _unspecified,
        language_tag: Union[str, None, _Sentinel] = _unspecified,
        abi_tag: Union[str, None, _Sentinel] = _unspecified,
        platform_tag: Union[str, None, _Sentinel] = _unspecified,
        compression: int = zipfile.ZIP_DEFLATED,
        allowZip64: bool = True,
        compresslevel: Optional[int] = None,
        strict_timestamps: bool = True,
    ) -> "WheelFile":
        """Recreate `wf` using different parameters.

        Creates a new `WheelFile` object using data from another, given as
        `wf`, and given constructor parameters. The new object will contain
        the same files (including those under `.data` and `.dist-info`
        directories), with the same timestamps, compression methods,
        compression levels, access modes, etc., *except*:

        - `.dist-info` directory is renamed, if `version` or `distname` is
          changed.
        - `.data` directory is renamed, if `version` or `distname` is
          changed.
        - `METADATA` will contain almost all the same information, except
          for the fields that were changed via arguments of this method.
        - `WHEEL` will be changed to contain the new `tags` and `build`
          number. The `generator` field will be reset to the one given by
          `WheelData` by default: `"wheelfile <version>"`.
        - `RECORD` is reconstructed in order to accomodate the differences
          above.

        This can be used to rename a wheel, change its metadata, or add files
        to it. It also fixes some common problems of wheel packages, e.g.
        unnormalized dist-info directory names.

        If any of the metadata files is missing or corrupted in `wf`, i.e. the
        properties `metadata`, `wheeldata`, and `record` of `wf` are set to
        `None`, new ones with will be created for the new object, using default
        values.

        All parameters of this method except `wf` are passed to the new
        object's `__init__`.

        For `distname`, `version`, and `*_tag` arguments, if a parameter is not
        given, the value from `wf` is used. If a default is needed instead, set
        the argument to `None` explicitly.

        Even if `wf` was created using a path to a directory, the default value
        used for `file_or_path` will be the current working directory.

        The new `WheelFile` object must be writable, so by default `"w"` mode
        is used, instead of `"r"`. If copying `wf` would result in overwriting
        a file or buffer from which `wf` was created, `ValueError` will be
        raised.

        Parameters
        ----------
        wf
            `WheelFile` object from which the new object should be recreated.

        mode
            Mode in which the new `WheelFile` should be opened. Accepts the
            same modes as `WheelFile.__init__`, except read mode (`"r"`) is not
            allowed.

        distname, version, build_tag, language_tag, abi_tag, platform_tag
            Optional argument passed to the new object's constructor. See
            `WheelFile.__init__` for the full description. If not specified,
            value from `wf` is used (it is avaialable via property of the same
            name). If `None` is given explicitly, constructor's default is
            used.

        compression, allowZip64, compresslevel, strict_timestamps
            Optional argument passed to the new object's constructor, which in
            turn passes them to `zipfile.ZipFile` - see `zipfile` docs for full
            description on each.

            Value from `wf` is *not* reused for this parameter.

        Raises
        ------
        ValueError
            Raised when:
               - Read mode is used (`"r"`) in `mode`.
               - Creating the object would result in rewriting the underlying
                 buffer of `wf` (if `wf` uses an IO buffer).
               - Creating the object would result in rewriting the file on
                 which `wf` operates.
        """
        if "r" in mode:
            raise ValueError(
                f"Passing \"r\" as mode is not allowed when recreating a "
                f"wheel: {repr('mode')}."
            )

        if distname is cls._unspecified:
            distname = wf.distname
        if version is cls._unspecified:
            version = wf.version
        if build_tag is cls._unspecified:
            build_tag = wf.build_tag
        if language_tag is cls._unspecified:
            language_tag = wf.language_tag
        if abi_tag is cls._unspecified:
            abi_tag = wf.abi_tag
        if platform_tag is cls._unspecified:
            platform_tag = wf.platform_tag

        # Required for the path check below
        if isinstance(version, str):
            version = Version(version)
        if isinstance(file_or_path, str):
            file_or_path = Path(file_or_path)

        # For MyPy
        assert isinstance(distname, str) or distname is None
        assert isinstance(version, (str, Version)) or version is None
        assert isinstance(build_tag, (int, str)) or build_tag is None
        assert isinstance(language_tag, str) or language_tag is None
        assert isinstance(abi_tag, str) or abi_tag is None
        assert isinstance(platform_tag, str) or platform_tag is None

        if file_or_path == wf.zipfile.fp:
            raise ValueError(
                "Buffer object used to save the new wheel cannot be the "
                "same as the one used by the other WheelFile object."
            )

        f_o_p = file_or_path  # For brevity
        dir_path = (
            f_o_p.resolve() if isinstance(f_o_p, Path) and f_o_p.is_dir() else
            f_o_p.parent.resolve() if isinstance(f_o_p, Path) else
            getattr(f_o_p, 'name', None)
        )

        # wf.zipfile.filename is not None only when it is writing to a file
        both_are_files = (
            wf.zipfile.filename is not None
            and dir_path is not None
        )

        if both_are_files:
            assert wf.zipfile.filename is not None  # For MyPy
            # Ensure we won't overwrite wf
            wf_dir_path = Path(wf.zipfile.filename).parent.resolve()
            if wf_dir_path == dir_path and (
                wf.distname == distname
                and wf.version == version
                and wf.build_tag == build_tag
                and wf.language_tag == language_tag
                and wf.abi_tag == abi_tag
                and wf.platform_tag == platform_tag
            ):
                raise ValueError(
                    "Operation would overwrite the old wheel - "
                    "both objects' paths point at the same file."
                )

        new_wf = WheelFile(
            file_or_path, mode,
            distname=distname,
            version=version,
            build_tag=build_tag,
            language_tag=language_tag,
            abi_tag=abi_tag,
            platform_tag=platform_tag,
            compression=compression,
            allowZip64=allowZip64,
            compresslevel=compresslevel,
            strict_timestamps=strict_timestamps,
        )

        assert new_wf.wheeldata is not None  # For MyPy

        # TODO: if Corrupted() is implemented, make sure to test
        # wf.metadata = Corupted (& wheeldata, & record)

        if wf.metadata is not None:
            # TODO: use copy.deepcopy instead
            new_wf.metadata = MetaData.from_str(str(wf.metadata))
            new_wf.metadata.name = new_wf.distname
            new_wf.metadata.version = new_wf.version

        if wf.wheeldata is not None:
            new_wf.wheeldata.root_is_purelib = wf.wheeldata.root_is_purelib

            # TODO: if wf.wheeldata.build/tags are changed, the changed values
            # should superseed those from wf's name in cloning, i.e. new_wf
            # should have build/tags from wf in its own name, but build/tags
            # from wf.wheeldata in its wheeldata.
            #
            # new_wf.wheeldata.tags = wf.wheeldata.tags
            # new_wf.wheeldata.build = wf.wheeldata.build
            #
            # But the given build tag should always superseed the above:
            #
            # <<(dedent)
            # if build_tag is not cls._unspecified:
            #     new_wf.wheeldata.build = build_tag
            # <<
            #
            # Similar modality should be put in place for distname and version
            # of wf.metadata.

        to_copy = wf.infolist()
        for zinfo in to_copy:

            arcname = zinfo.filename
            arcname_head, *arcname_tail_parts = arcname.split('/')
            arcname_tail = '/'.join(arcname_tail_parts)
            if arcname_head == wf.distinfo_dirname:
                new_arcname = new_wf.distinfo_dirname + '/' + arcname_tail
                new_wf.writestr(new_arcname, wf.zipfile.read(zinfo))
                continue
            if arcname_head == wf.data_dirname:
                new_arcname = new_wf.data_dirname + '/' + arcname_tail
                new_wf.writestr(new_arcname, wf.zipfile.read(zinfo))
                continue

            new_wf.writestr(zinfo, wf.zipfile.read(zinfo))

        return new_wf

    @staticmethod
    def _is_unnamed_or_directory(target: Union[Path, BinaryIO]) -> bool:
        return (
            (getattr(target, 'name', None) is None)
            or
            (isinstance(target, Path) and target.is_dir())
        )

    @staticmethod
    def _require_distname_and_version(
        distname: Optional[str], version: Optional[Union[str, Version]]
    ):
        if distname is None:
            raise UnnamedDistributionError(
                "No distname provided and an unnamed object given."
            )
        if version is None:
            raise UnnamedDistributionError(
                "No version provided and an unnamed object given."
            )

    @staticmethod
    def _generate_filename(
        distname: str,
        version: Union[str, Version],
        build_tag: Optional[Union[str, int]],
        language_tag: str,
        abi_tag: str,
        platform_tag: str
    ) -> str:
        if build_tag is None:
            segments = [distname, str(version),
                        language_tag, abi_tag, platform_tag]
        else:
            segments = [distname, str(version), str(build_tag),
                        language_tag, abi_tag, platform_tag]

        filename = '-'.join(segments) + '.whl'
        return filename

    @classmethod
    def _get_filename(
        cls, file_or_path: Union[BinaryIO, Path]
    ) -> Optional[str]:
        """Return a filename from file obj or a path.

        If given file, the asumption is that the filename is within the value
        of its `name` attribute.
        If given a `Path`, assumes it is a path to an actual file, not a
        directory.
        If given an unnamed object, this returns None.
        """
        if cls._is_unnamed_or_directory(file_or_path):
            return None

        # TODO: test this
        # If a file object given, ensure its a filename, not a path
        if isinstance(file_or_path, Path):
            return file_or_path.name
        else:
            # File objects contain full path in ther name attribute
            filename = Path(file_or_path.name).name
            return filename

    def _pick_a_distname(self, filename: Optional[str],
                         given_distname: Union[None, str]):
        # filename == None means an unnamed object was given
        assert filename is not None or given_distname is not None

        if given_distname is not None:
            distname = given_distname
        else:
            assert filename is not None  # For MyPy
            distname = filename.split('-')[0]
            if distname == '':
                raise UnnamedDistributionError(
                    f"No distname provided and the inferred filename does not "
                    f"contain a proper distname substring: {repr(filename)}."
                )
        self._distname = distname

    def _pick_a_version(
        self, filename: Optional[str], given_version: Union[None, str, Version]
    ):
        # filename == None means an unnamed object was given
        assert filename is not None or given_version is not None

        if isinstance(given_version, Version):
            # We've got a valid object here, nothing else to do
            self._version = given_version
            return
        elif isinstance(given_version, str):
            version = given_version
        elif given_version is not None:
            raise TypeError(
                "'version' must be either packaging.version.Version or a string"
            )
        else:
            assert filename is not None  # For MyPy
            name_segments = filename.split('-')

            if len(name_segments) < 2 or name_segments[1] == '':
                raise UnnamedDistributionError(
                    f"No version provided and the inferred filename does not "
                    f"contain a version segment: {repr(filename)}."
                )
            version = name_segments[1]

        try:
            self._version = Version(version)
        except InvalidVersion as e:
            # TODO: assign degenerated version instead
            raise ValueError(
                f"Filename contains invalid version: {repr(version)}."
            ) from e

    def _pick_tags(self,
                   filename: Optional[str],
                   given_build: Optional[int],
                   given_language: Optional[str],
                   given_abi: Optional[str],
                   given_platform: Optional[str]):
        # filename == None means an unnamed object was given
        if filename is None:
            self._build_tag = given_build
            self._language_tag = given_language or 'py3'
            self._abi_tag = given_abi or 'none'
            self._platform_tag = given_platform or 'any'
            return

        if filename.endswith('.whl'):
            filename = filename[:-4]

        segments = filename.split('-')
        if not (len(segments) == 6 or len(segments) == 5):
            segments = [''] * 5

        # TODO: test this when lazy mode is ready
        if len(segments) == 6 and given_build is None:
            try:
                self._build_tag = int(segments[2])
            except ValueError:
                # TODO: set to degenerated build number instead
                self._build_tag = None
        else:
            self._build_tag = given_build

        self._language_tag = given_language or segments[-3]
        self._abi_tag = given_abi or segments[-2]
        self._platform_tag = given_platform or segments[-1]

    def _initialize_distinfo(self):
        collapsed_tags = '-'.join((self._language_tag,
                                   self._abi_tag,
                                   self._platform_tag))
        self.wheeldata = WheelData(build=self.build_tag, tags=collapsed_tags)
        self.metadata = MetaData(name=self.distname, version=self.version)
        self.record = WheelRecord()

    # TODO: test edge cases related to bad contents
    # TODO: should "bad content" exceptions be saved for validate()?
    # TODO: the try...excepts should use something stricter than "Exception"
    # TODO: save the exceptions in Corrupted objects after they are implemented
    def _read_distinfo(self):
        try:
            metadata = self.zipfile.read(self._distinfo_path('METADATA'))
            self.metadata = MetaData.from_str(metadata.decode('utf-8'))
        except Exception:
            self.metadata = None

        try:
            wheeldata = self.zipfile.read(self._distinfo_path('WHEEL'))
            self.wheeldata = WheelData.from_str(wheeldata.decode('utf-8'))
        except Exception:
            self.metadata = None

        try:
            record = self.zipfile.read(self._distinfo_path('RECORD'))
            self.record = WheelRecord.from_str(record.decode('utf-8'))
        except Exception:
            self.record = None

    # TODO: check what are the common bugs with wheels and implement checks here
    # TODO: test behavior if no candidates found
    def _find_distinfo_prefix(self):
        # TODO: this could use a walrus
        candidates = {path.split('/')[0] for path in self.zipfile.namelist()}
        candidates = {name for name in candidates
                      if name.endswith('.dist-info')}
        # TODO: log them onto debug
        if len(candidates) > 1:
            raise BadWheelFileError(
                "Multiple .dist-info directories found in the archive."
            )
        if len(candidates) == 0:
            raise BadWheelFileError(
                "Archive does not contain any .dist-info directory."
            )

        return candidates.pop()[:-len('dist-info')]

    @property
    def filename(self) -> str:
        return self._zip.filename or self._generated_filename

    @property
    def distname(self) -> str:
        return self._distname

    @property
    def version(self) -> Version:
        return self._version

    @property
    def build_tag(self) -> Optional[int]:
        return self._build_tag

    @property
    def language_tag(self) -> str:
        return self._language_tag

    @property
    def abi_tag(self) -> str:
        return self._abi_tag

    @property
    def platform_tag(self) -> str:
        return self._platform_tag

    @property
    def distinfo_dirname(self):
        return self._distinfo_path("", kind="dist-info")[:-1]

    @property
    def data_dirname(self):
        return self._distinfo_path("", kind="data")[:-1]

    # TODO: the baseline for this should be "is the wheel installable"?
    # TODO: validate naming conventions, metadata, etc.
    # TODO: use testwheel()
    # TODO: idea: raise when completely out-of-spec, return a compliancy score?
    # TODO: fail if there are multiple .dist-info or .data directories
    # TODO: actually, having two .data directories doesn't seem like a big
    # deal, it could be just unpacked in the same place rest of the contents
    # of the wheel are
    # TODO: use lint()?
    # TODO: ensure there are no synonym files for metadata (maybe others?)
    # TODO: the bottom-line semantics of this method should be: if validate()
    # goes through, the wheel is installable. Of course there are other
    # requirements.
    # TODO: custom exception
    # TODO: test every check
    # TODO: check filename segments are not empty
    # TODO: !in lazy mode, return exception objects instead of raising them!
    def validate(self):
        if self.filename is not None and not self.filename.endswith('.whl'):
            raise ValueError(
                f"Filename must end with '.whl': {repr(self.filename)}"
            )

        if self.distname == '':
            raise ValueError("Distname cannot be an empty string.")

        distname_valid = set(self.distname) <= self.VALID_DISTNAME_CHARS
        if not distname_valid:
            raise ValueError(
                f"Invalid distname: {repr(self.distname)}. Distnames should "
                f"contain only ASCII letters, numbers, underscores, and "
                f"periods."
            )

        if self.metadata is None:
            raise ValueError(
                "METADATA file is not present in the archive or is corrupted."
            )

        if self.wheeldata is None:
            raise ValueError(
                "WHEEL file is not present in the archive or is corrupted."
            )

        # TODO: make this optional
        if self.record is None:
            raise ValueError(
                "RECORD file is not present in the archive or is corrupted."
            )

        if self.wheeldata.build != self.build_tag:
            raise ValueError(
                "WHEEL build tag is different than the one in the filename"
            )

    # TODO: return a list of defects & negligences present in the wheel file
    # TODO: maybe it's a good idea to put it outside this class?
    # TODO: The implementation could be made simpler by utilizng an internal
    # list of error & lint objects, that have facilities to check a WheelFile
    # object and fix it.
    def lint(self):
        raise NotImplementedError()

    # TODO: fix everything we can without guessing
    # TODO: provide sensible defaults
    # TODO: return proper filename
    # TODO: base the fixes on the return value of lint()?
    def fix(self) -> str:
        # Requires rewrite feature
        raise NotImplementedError()

    # TODO: ensure RECORD is correct, if it exists
    # TODO: for the first wrong record found, return its arcpath
    # TODO: for the first file not found in the record, return its arcpath
    # TODO: docstring
    def testwheel(self):
        first_broken = self._zip.testzip()
        if first_broken is not None:
            return first_broken
        raise NotImplementedError("Check if RECORD is correct here")

    # TODO: if arcname is None, refresh everything (incl. deleted files)
    # TODO: docstring - mention that this does not write record to archive and
    # that the record itself is optional
    # FIXME: this makes basic wheel creation impossible on files with 'wb' mode
    def refresh_record(self, arcname: Union[Path, str]):
        # RECORD file is optional
        if self.record is None:
            return

        # Adding directories to record is bad
        if str(arcname).endswith('/'):
            return

        if isinstance(arcname, Path):
            arcname = str(arcname)
        if self.closed:
            raise RuntimeError("Cannot refresh record: file closed.")
        # See mypy issue #9917
        assert self._zip.fp.readable(), (  # type: ignore
            "The zipfile stream must be readable in order to generate a record "
            "entry."
        )
        with self._zip.open(arcname) as zf:
            self.record.update(arcname, zf)

    def _distinfo_path(self, filename: str, *, kind='dist-info') -> str:
        if self._distinfo_prefix is None:
            name = canonicalize_name(self.distname).replace("-", "_")
            version = str(self.version).replace("-", "_")
            self._distinfo_prefix = f"{name}-{version}."

        return f"{self._distinfo_prefix}{kind}/{filename}"

    # TODO: lazy mode - do not write anything in lazy mode
    # TODO: use validate(), add possible raised exceptions to the docstring
    # TODO: ensure there are no writing handles open in zipfile before writing
    # meta
    def close(self) -> None:
        """Finalize and close the file.

        Writes the rest of the necessary data to the archive, performs one last
        validation of the contents (unless the file is open in lazy mode), and
        closes the file.

        There must not be any handles left open for the zip contents, i.e. all
        objects returned by `open()` or `.zip.open()` must be closed before
        calling this subroutine.

        Raises
        ------
        RuntimeError
            If there are unclosed content handles.
        """

        if self.closed:
            return

        if 'r' not in self.mode:
            if self.metadata is not None:
                self.writestr(self._distinfo_path("METADATA"),
                              str(self.metadata).encode())
            if self.wheeldata is not None:
                self.writestr(self._distinfo_path("WHEEL"),
                              str(self.wheeldata).encode())
            self._zip.writestr(self._distinfo_path("RECORD"),
                               str(self.record).encode())

        self._zip.close()

    def __del__(self):
        try:
            self.close()
        except AttributeError:
            # This may happen if __init__ fails before creating self._zip
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def closed(self) -> bool:
        # ZipFile.fp is set to None upon ZipFile.close()
        return self._zip.fp is None

    # TODO: symlinks?
    # TODO: use shutil.copyfileobj same way ZipFile.write does
    def write(self,
              filename: Union[str, Path],
              arcname: Optional[str] = None,
              compress_type: Optional[int] = None,
              compresslevel: Optional[int] = None,
              *, recursive: bool = True, resolve: bool = True,
              skipdir: bool = True) -> None:
        """Add the file to the wheel.

        Updates the wheel record, if the record is being kept.

        Parameters
        ----------
        filename
            Path to the file or directory to add.

        arcname
            Path in the archive to assign the file/directory into. If not
            given, `filename` will be used instead. In both cases, the leading
            path separators and the drive letter (if any) will be removed.

        compress_type
            Same as in `zipfile.ZipFile.write`. Overrides the `compression`
            parameter given to `__init__`.

        compresslevel
            Same as in `zipfile.ZipFile.write`. Overrides the `compresslevel`
            parameter given to `__init__`.

        recursive
            Keyword only. When True, if given path leads to a directory, all of
            its contents are going to be added into the archive, including
            contents of its subdirectories.

            If its False, only a directory entry is going to be added, without
            any of its contents.

        resolve
            Keyword only. When True, and no `arcname` is given, the path given
            to `filename` will not be used as the arcname (as is the case with
            `ZipFile.write`), but only the name of the file that it points to
            will be used.

            For example, if you set `filename` to `../some/other/dir/file`,
            `file` entry will be written in the archive root.

            Has no effect when set to False or when `arcname` is given.

        skipdir
            Keyword only. Indicates whether directory entries should be skipped
            in the archive. Set to `True` by default, which means that
            attempting to write an empty directory will be silently omitted.
        """
        if resolve and arcname is None:
            arcname = resolved(filename)
        self._write_to_zip(filename, arcname, skipdir, compress_type,
                           compresslevel)

        if recursive:
            common_root = str(filename)
            root_arcname = arcname
            for root, dirs, files in os.walk(filename):
                # For reproducibility, sort directories, so that os.walk
                # traverses them in a defined order.
                dirs.sort()

                dirs = [d + '/' for d in dirs]
                for name in sorted(dirs + files):
                    filepath = os.path.join(root, name)
                    arcpath = self._os_walk_path_to_arcpath(
                        common_root, root, name, root_arcname
                    )
                    self._write_to_zip(filepath, arcpath, skipdir,
                                       compress_type, compresslevel)

    def _write_to_zip(self, filename, arcname, skipdir, compress_type,
                      compresslevel):
        zinfo = zipfile.ZipInfo.from_file(
            filename, arcname, strict_timestamps=self._strict_timestamps
        )

        # Since we construct ZipInfo manually here, we have to propagate
        # defaults ourselves.
        if compress_type is None:
            compress_type = self.zipfile.compression
        if compresslevel is None:
            compresslevel = self.zipfile.compresslevel

        if zinfo.is_dir():
            if skipdir:
                return
            else:
                data = b''
        else:
            with open(filename, 'br') as f:
                data = f.read()
        self._zip.writestr(zinfo, data, compress_type, compresslevel)
        self.refresh_record(zinfo.filename)

    @staticmethod
    def _os_walk_path_to_arcpath(prefix: str, directory: str,
                                 stem: str, arcname: Optional[str]):
        if arcname is None:
            arcname = prefix

        # Ensure that os.path.join will not get an absolute path after cutting
        # 'prefix' out of 'directory'.
        # Otherwise cutting out 'prefix' might've left out leading '/', which
        # would make os.path.join below ignore 'arcname'.
        prefix = prefix.rstrip(os.sep) + os.sep

        path = os.path.join(arcname, directory[len(prefix):], stem)
        return path

    # TODO: Make sure fields of given ZipInfo objects are propagated
    def writestr(self,
                 zinfo_or_arcname: Union[zipfile.ZipInfo, str],
                 data: Union[bytes, str],
                 compress_type: Optional[int] = None,
                 compresslevel: Optional[int] = None) -> None:
        """Write given data into the wheel under the given path.

        Updates the wheel record, if the record is being kept.

        Parameters
        ----------
        zinfo_or_arcname
            Specifies the path in the archive under which the data will be
            stored.

        data
            The data that will be writen into the archive. If it's a string, it
            is encoded as UTF-8 first.

        compress_type
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compression`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compress_type` field is also
            overriden.

        compresslevel
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compresslevel`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compresslevel` field is also
            overriden.
        """

        # XXX: ZipFile.writestr() does not normalize arcpaths the same way
        #      ZipFile.write() does, and so this method won't do that either

        arcname = (
            zinfo_or_arcname.filename
            if isinstance(zinfo_or_arcname, zipfile.ZipInfo)
            else zinfo_or_arcname
        )

        self._zip.writestr(zinfo_or_arcname, data, compress_type, compresslevel)
        self.refresh_record(arcname)

    # TODO: drive letter should be stripped from the arcname the same way
    # ZipInfo.from_file does it
    # TODO: symlinks?
    def write_data(self, filename: Union[str, Path],
                   section: str, arcname: Optional[str] = None,
                   compress_type: Optional[int] = None,
                   compresslevel: Optional[int] = None,
                   *, recursive: bool = True, resolve: bool = True,
                   skipdir: bool = True) -> None:
        """Write a file to the .data directory under a specified section.

        This method is a handy shortcut for writing into
        `<dist>-<version>.data/`, such that you dont have to generate the path
        yourself.

        Updates the wheel record, if the record is being kept.

        Parameters
        ----------
        filename
            Path to the file or directory to add.

        section
            Name of the section, i.e. the directory inside `.data/` that the
            file should be put into. Sections have special meaning, see PEP-427.
            Cannot contain any slashes, nor be empty.

        arcname
            Path in the archive to assign the file/directory into, relative to
            the directory of the specified data section. If left empty,
            filename is used. Leading slashes are stripped.

        compress_type
            Same as in `zipfile.ZipFile.write`. Overrides the `compression`
            parameter given to `__init__`.

        compresslevel
            Same as in `zipfile.ZipFile.write`. Overrides the `compresslevel`
            parameter given to `__init__`.

        recursive
            Keyword only. When True, if given path leads to a directory, all of
            its contents are going to be added into the archive, including
            contents of its subdirectories.

            If its False, only a directory entry is going to be added, without
            any of tis contents.

        resolve
            Keyword only. When True, and no `arcname` is given, the path given
            to `filename` will not be used as the arcname (as is the case with
            `ZipFile.write`), but only the name of the file that it points to
            will be used.

            For example, if you set `filename` to `../some/other/dir/file`,
            `file` entry will be written in the archive root.

            Has no effect when set to False or when `arcname` is given.

        skipdir
            Keyword only. Indicates whether directory entries should be skipped
            in the archive. Set to `True` by default, which means that
            attempting to write an empty directory will be silently omitted.
        """
        self._check_section(section)

        if isinstance(filename, str):
            filename = Path(filename)
        if arcname is None:
            arcname = filename.name

        arcname = self._distinfo_path(section + '/' + arcname.lstrip('/'),
                                      kind='data')

        self.write(filename, arcname, compress_type, compresslevel,
                   recursive=recursive, resolve=resolve, skipdir=skipdir)

    # TODO: drive letter should be stripped from the arcname the same way
    # ZipInfo.from_file does it
    # TODO: Make sure fields of given ZipInfo objects are propagated
    def writestr_data(self, section: str,
                      zinfo_or_arcname: Union[zipfile.ZipInfo, str],
                      data: Union[bytes, str],
                      compress_type: Optional[int] = None,
                      compresslevel: Optional[int] = None) -> None:
        """Write given data to the .data directory under a specified section.

        This method is a handy shortcut for writing into
        `<dist>-<version>.data/`, such that you dont have to generate the path
        yourself.

        Updates the wheel record, if the record is being kept.

        Parameters
        ----------
        section
            Name of the section, i.e. the directory inside `.data/` that the
            file should be put into. Sections have special meaning, see PEP-427.
            Cannot contain any slashes, nor be empty.

        zinfo_or_arcname
            Specifies the path in the archive under which the data will be
            stored. This is relative to the path of the section directory.
            Leading slashes are stripped.

        data
            The data that will be writen into the archive. If it's a string, it
            is encoded as UTF-8 first.

        compress_type
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compression`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compress_type` field is also
            overriden.

        compresslevel
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compresslevel`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compresslevel` field is also
            overriden.
        """
        self._check_section(section)

        arcname = (
            zinfo_or_arcname.filename
            if isinstance(zinfo_or_arcname, zipfile.ZipInfo)
            else zinfo_or_arcname
        )

        arcname = self._distinfo_path(section + '/' + arcname.lstrip('/'),
                                      kind='data')

        self.writestr(arcname, data, compress_type, compresslevel)

    # TODO: Lazy mode should permit writing meta here
    def write_distinfo(self, filename: Union[str, Path],
                       arcname: Optional[str] = None,
                       compress_type: Optional[int] = None,
                       compresslevel: Optional[int] = None,
                       *, recursive: bool = True, resolve: bool = True,
                       skipdir: bool = True) -> None:
        """Write a file to `.dist-info` directory in the wheel.

        This is a shorthand for `write(...)` with `arcname` prefixed with
        the `.dist-info` path. It also ensures that the metadata files critical
        to the wheel correctnes (i.e. the ones written into archive on
        `close()`) aren't being pre-written.

        Parameters
        ----------
        filename
            Path to the file or directory to add.

        arcname
            Path in the archive to assign the file/directory into. If not
            given, `filename` will be used instead. In both cases, the leading
            path separators and the drive letter (if any) will be removed.

            This parameter will be prefixed with proper `.dist-info` path
            automatically.

        compress_type
            Same as in `zipfile.ZipFile.write`. Overrides the `compression`
            parameter given to `__init__`.

        compresslevel
            Same as in `zipfile.ZipFile.write`. Overrides the `compresslevel`
            parameter given to `__init__`.

        recursive
            Keyword only. When True, if given path leads to a directory, all of
            its contents are going to be added into the archive, including
            contents of its subdirectories.

            If its False, only a directory entry is going to be added, without
            any of its contents.

        resolve
            Keyword only. When True, and no `arcname` is given, the path given
            to `filename` will not be used as the arcname (as is the case with
            `ZipFile.write`), but only the name of the file that it points to
            will be used.

            For example, if you set `filename` to `../some/other/dir/file`,
            `file` entry will be written in the `.dist-info` directory.

            Has no effect when set to False or when `arcname` is given.

        skipdir
            Keyword only. Indicates whether directory entries should be skipped
            in the archive. Set to `True` by default, which means that
            attempting to write an empty directory will be silently omitted.

        Raises
        ------
        ProhibitedWriteError
            Raised if the write would result with duplicated `WHEEL`,
            `METADATA`, or `RECORD` files after `close()` is called.
        """
        if resolve and arcname is None:
            arcname = resolved(filename)
        elif arcname is None:
            arcname = str(filename)

        if arcname == '':
            raise ProhibitedWriteError(
                "Empty arcname - write would result in duplicating zip entry "
                "for .dist-info directory."
            )

        if arcname in self.METADATA_FILENAMES:
            raise ProhibitedWriteError(
                f"Write would result in a duplicated metadata file: {arcname}."
            )

        arcname = self._distinfo_path(arcname)

        self.write(filename, arcname, compress_type, compresslevel,
                   recursive=recursive, skipdir=skipdir)

    # TODO: Make sure fields of given ZipInfo objects are propagated
    def writestr_distinfo(self, zinfo_or_arcname: Union[zipfile.ZipInfo, str],
                          data: Union[bytes, str],
                          compress_type: Optional[int] = None,
                          compresslevel: Optional[int] = None) -> None:
        """Write given data to the .dist-info directory.

        This method is a handy shortcut for writing into
        `<dist>-<version>.dist-info/`, such that you dont have to generate the
        path yourself.

        Updates the wheel record, if the record is being kept.

        Does not permit writing into arcpaths of metadata files managed by this
        class.

        Parameters
        ----------
        zinfo_or_arcname
            Specifies the path in the archive under which the data will be
            stored. This is relative to the path of the section directory.
            Leading slashes are stripped.

        data
            The data that will be writen into the archive. If it's a string, it
            is encoded as UTF-8 first.

        compress_type
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compression`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compress_type` field is also
            overriden.

        compresslevel
            Same as in `zipfile.ZipFile.writestr`. Overrides the `compresslevel`
            parameter given to `__init__`. If the first parameter is a
            `ZipInfo` object, the value its `compresslevel` field is also
            overriden.

        Raises
        ------
        ProhibitedWriteError
            When attempting to write into `METADATA`, `WHEEL`, or `RECORD`.
        """
        arcname = (
            zinfo_or_arcname.filename
            if isinstance(zinfo_or_arcname, zipfile.ZipInfo)
            else zinfo_or_arcname
        )

        # TODO don't check this in lazy mode
        if (arcname in self.METADATA_FILENAMES
                or arcname.split('/')[0] in self.METADATA_FILENAMES):
            raise ProhibitedWriteError(
                f"Write would result in a duplicated metadata file: {arcname}."
            )

        arcname = self._distinfo_path(arcname.lstrip('/'))
        self.writestr(arcname, data, compress_type, compresslevel)

    @staticmethod
    def _check_section(section):
        # TODO make sure lazy mode doesn't do this
        if section == '':
            raise ValueError("Section cannot be an empty string.")
        if '/' in section:
            raise ValueError("Section cannot contain slashes.")

    def namelist(self) -> List[str]:
        """Return a list of wheel members by name, omit metadata files.

        Same as ``ZipFile.namelist()``, but omits ``RECORD``, ``METADATA``, and
        ``WHEEL`` files.
        """
        skip = [self._distinfo_path(n) for n in self.METADATA_FILENAMES]
        return [name for name in self.zipfile.namelist() if name not in skip]

    def infolist(self) -> List[zipfile.ZipInfo]:
        """Return a list of ``ZipInfo`` objects for each wheel member.

        Same as ``ZipFile.infolist()``, but omits objects corresponding to
        ``RECORD``, ``METADATA``, and ``WHEEL`` files.
        """
        skip = [self._distinfo_path(n) for n in self.METADATA_FILENAMES]
        return [zi for zi in self.zipfile.infolist() if zi.filename not in skip]

    @property
    def zipfile(self) -> zipfile.ZipFile:
        return self._zip

    # TODO: return a handle w/ record refresh semantics
    def open(self, path) -> IO:
        raise NotImplementedError()
