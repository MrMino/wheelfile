# We do not target python2.
# Which python3 versions should we target? 3.6+ seems like a good idea.
import csv
import io
import hashlib

from pathlib import Path
from collections import namedtuple
from inspect import signature
from packaging.tags import parse_tag
from packaging.utils import canonicalize_name
from packaging.version import Version
from email.message import EmailMessage
from email import message_from_string
from zipfile import ZipFile, ZipInfo

from typing import Optional, Union, List, Dict, IO, BinaryIO

__version__ = '0.0.1'


# TODO: change AssertionErrors to custom exceptions?
# TODO: idea - install wheel - w/ INSTALLER file
# TODO: idea - wheel from an installed distribution?

# TODO: module docstring
# TODO: fix inconsistent referencing style of symbols in docstrings


def _slots_from_params(func):
    """List out slot names based on the names of parameters of func

    Usage: __slots__ = _slots_from_signature(__init__)
    """
    funcsig = signature(func)
    slots = list(funcsig.parameters)
    slots.remove('self')
    return slots


# TODO: reimplement using dataclasses
# TODO: add version to the class name, reword the "Note"
# name regex for validation: ^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$
# TODO: helper-function or consts for description_content_type
# TODO: parse version using packaging.version.parse?
# TODO: values validation
# TODO: validate provides_extras ↔ requires_dists?
# TODO: validate values charset-wise
# TODO: as_json?
# TODO: as_dict?
# TODO: ensure name is the same as wheelfile namepath
# TODO: PEP-643 - v2.2
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
    def __init__(self, *, name: str, version: str,
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
        self.version = version

        self.summary = summary
        self.description = description
        self.description_content_type = description_content_type
        self.keywords = keywords or []
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
            raise ValueError(f"Unknown field: {field_name}")

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
        m = EmailMessage()
        m.add_header("Metadata-Version", self.metadata_version)
        for attr_name in self.__slots__:
            content = getattr(self, attr_name)
            if not content:
                continue

            field_name = self._field_name(attr_name)

            if field_name == 'Keywords':
                content = ','.join(content)

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
            return all(getattr(self, f) == getattr(other, f)
                       for f in self.__slots__)
        else:
            return NotImplemented

    @classmethod
    def from_str(cls, s: str) -> 'MetaData':
        m = message_from_string(s)
        assert m['Metadata-Version'] == cls._metadata_version
        del m['Metadata-Version']

        args = {}
        for field_name in m.keys():
            attr = cls._attr_name(field_name)
            if not attr.endswith('s'):
                args[attr] = m.get(field_name)
            else:
                args[attr] = m.get_all(field_name)

        args['description'] = m.get_payload()

        return cls(**args)


# TODO: reimplement using dataclasses?
# TODO: add version to the class name, reword the "Note"
# TODO: values validation
# TODO: to_json?
# TODO: as_dict?
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

        By default, "py2.py3-none-any" (the universal tag) is used.

    build
        Optional build number. Used as a tie breaker when two wheels have the
        same version.
    """
    def __init__(self, *,
                 generator: str = 'wheelfile ' + __version__,
                 root_is_purelib: bool = True,
                 tags: Union[List[str], str] = 'py2.py3-none-any',
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


# TODO: leave out hashes of *.pyc files?
class WheelRecord:
    """Contains logic for creation and modification of RECORD files.

    Keeps track of files in the wheel and their hashes.

    For the full spec, see PEP-376 "RECORD" section, PEP-627,
    "The .dist-info directory" section of PEP-427, and
    https://packaging.python.org/specifications/recording-installed-packages/.
    """
    HASH_ALGO = hashlib.sha256
    HASH_BUF_SIZE = 65536

    _RecordEntry = namedtuple('Record', 'path hash size')

    def __init__(self):
        self._records: Dict[str, self._RecordEntry] = {}

    def hash_of(self, arc_path) -> str:
        """Return the hash of a file in the archive this RECORD describes


        Parameters
        ----------
        arc_path
            Location of the file inside the archive.

        Returns
        -------
        str
            String in the form <algorithm>=<hexstr>, where algorithm is the
            name of the hashing agorithm used to generate the hash (see
            HASH_ALGO), and hexstr is a string containing a hexified version of
            the hash.
        """
        return self._records[arc_path].hash

    def __str__(self) -> str:
        buf = io.StringIO()
        records = csv.DictWriter(buf, fieldnames=self._RecordEntry._fields)
        for entry in self._records.values():
            records.writerow(entry._asdict())
        return buf.getvalue()

    @classmethod
    def from_str(self, s) -> 'WheelRecord':
        record = WheelRecord()
        buf = io.StringIO(s)
        reader = csv.DictReader(buf, self._RecordEntry._fields)
        for row in reader:
            entry = self._RecordEntry(**row)
            record._records[entry.path] = entry
        return record

    def update(self, arc_path: str, buf: BinaryIO):
        """Add a record entry for a file in the archive.

        Parameters
        ----------
        buf
            Buffer from which the data will be read in HASH_BUF_SIZE chunks.
            Must be fresh, i.e. seek(0)-ed.
        """
        assert buf.tell() == 0, (
            f"Stale buffer given - current position: {buf.tell()}."
        )
        assert not arc_path.endswith('.dist-info/RECORD'), (
            f"Attempt to add an entry for a RECORD file to the RECORD: "
            f"{arc_path}."
        )
        self._records[arc_path] = self._entry(arc_path, buf)

    def remove(self, arc_path: str):
        del self._records[arc_path]

    @classmethod
    def _entry(cls, arc_path: str, buf: BinaryIO) -> _RecordEntry:
        size = 0
        hasher = cls.HASH_ALGO()
        while True:
            data = buf.read(cls.HASH_BUF_SIZE)
            size += len(data)
            if not data:
                break
            hasher.update(data)
        hash_hex = hasher.name + '=' + hasher.hexdigest()
        return cls._RecordEntry(arc_path, hash_hex, size)

    def __eq__(self, other):
        if isinstance(other, WheelRecord):
            return str(self) == str(other)
        else:
            return NotImplemented


class BadWheelFile(ValueError):
    """The given file cannot be interpreted as a wheel nor fixed."""


class UnnamedDistribution(BadWheelFile):
    """Distribution name cannot be deduced from arguments."""


# TODO: prevent arbitrary writes to METADATA, WHEEL, and RECORD - or make sure
# the writes are reflected internally
# TODO: prevent adding .dist-info directories if there's one already there
# TODO: add attributes docstrings: distribution, tags, etc
# TODO: ensure distname and varsion have no weird characters (!slashes!)
# TODO: properties for build tag, python tag, abi tag, platform tag?
# TODO: debug propery, as with ZipFile.debug
# TODO: comment property
# TODO: compression level arguments - is compression even supported by the spec?
class WheelFile:
    """An archive that follows the wheel specification.

    Used to read, create, validate, or modify *.whl files.

    Attributes
    ----------
    filename : str
        Path to the file, if the instance was initialized with one, otherwise
        None.

    distname : str
        Name of the distribution (project). Either given to __init__()
        explicitly or inferred from its file_or_path argument.

    version : packaging.version.Version
        Version of the distribution. Either given to __init__() explicitly or
        inferred from its file_or_path argument.

    record : Optional[WheelRecord]
        Current state of .dist-info/RECORD file.

        When modifying other files in the archive, the record is written on
        each operation & on close().

        In lazy mode, this is only the case when using refresh_record() and
        write_record(), and if the file does not exist or is misformatted, this
        attribute becomes None. In such cases, calling refresh_record() creates
        it from scratch().

        In non-lazy modes, this file is always created/read & validated on
        initialization.

    metadata : Optional[MetaData]
        Current state of .dist-info/METADATA file.

        Follows the same semantics as 'record'. Values from 'distname' and
        'version' are used to provide required arguments when the file is
        created from scratch in by __init__().

        In standard modes, when changing data contained by the object this
        property returns, the file is being written only on close(). In order
        to write it beforehand, use write_metadata().

        When using lazy mode, the data is not being written to the archive on
        close().

    wheeldata : Optional[WheelData]
        Current state of .dist-info/WHEELDATA file.

        Follows the same semantics as 'metadata'. Consult docstring of
        WheelData class for the default values used.

        Use write_wheeldata() after editting it, in order to write it before
        close(), or - in lazy mode - to write the archive data at all.
    """
    # TODO: implement lazy mode
    # TODO: in lazy mode, log reading/missing metadata errors
    def __init__(
        self,
        file_or_path: Union[str, Path, BinaryIO],
        mode: str = 'r',
        distname: Optional[str] = None,
        version: Optional[Union[str, Version]] = None,
    ) -> None:
        """Open or create a wheel file.

        If lazy mode is not specified:
            - In read and append modes, the file is validated using validate().
            - In write and exclusive write modes, all .dist-info metadata files
            are created (see "Attributes" section of this class).

        To skip the validation for example if you wish to fix a misformated
        wheel, use lazy mode ('l' - see description of the "mode" parameter).

        In lazy mode, if the opened file does not contain WHEEL, METADATA, or
        RECORD (which is optional as per PEP-627), the attributes corresponding
        to the missing data structures will be set to None. In order to create
        them, either set these attributes yourself and call their respective
        write methods, or use fix().

        If any of the metadata files cannot be read due to a wrong format, they
        are considered missing.

        If the archive root contains a directory with a name ending with
        '.dist-info', it is considered to be _the_ metadata directory for the
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
            would mean that the class would have to guess which are the genuine
            ones - and we refuse the temptation to do that (see "The Zen of
            Python").

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

            See the description of "distname" attribute for more information.

        version
            Version of the distribution in this wheelfile. Follows the same
            semantics as "distname".

            The given value must be compliant with PEP-440 version identifier
            specification.

            See the description of "version" attribute for more information.

        Raises
        ------
        UnnamedDistribution
            Raised if the distname or version cannot be inferred from the
            given arguments.

            E.g. when the path does not contain the version, or the
            file-like object has no "name" attribute to get the filename from,
            and the information wasn't provided via other arguments.

        BadWheelFile
            Raised if the archive contains multiple '.dist-info' or '.data'
            directories.

        zipfile.BadZipFile
            If given file is not a proper zip.
        """
        assert not isinstance(file_or_path, io.TextIOBase), (
            "Text buffer given where a binary one was expected."
        )

        if isinstance(file_or_path, str):
            file_or_path = Path(file_or_path)
        if isinstance(version, str):
            version = Version(version)

        self._target = file_or_path

        if distname is None:
            distname = self._distname_from_target()
        if version is None:
            version = self._version_from_target()

        self._distname = distname
        self._version = version
        self._zip = ZipFile(file_or_path, mode)

        self._read_dist_info()

    # TODO, FIXME: this should not use filename, as it might be a full path
    def _distname_from_target(self) -> str:
        if self.filename is None:
            raise UnnamedDistribution(
                "No distname provided and an unnamed object given."
            )

        distname = self.filename.split('-')[0]

        if not distname:
            raise UnnamedDistribution(
                f"No distname provided and the inferred filename does not "
                f"contain a proper distname substring: {self.filename}"
            )

        return distname

    # TODO, FIXME: this should not use filename, as it might be a full path
    def _version_from_target(self) -> Version:
        if self.filename is None:
            raise UnnamedDistribution(
                "No version provided and an unnamed object given."
            )

        name_segments = self.filename.split('-')

        if len(name_segments) < 2:
            raise UnnamedDistribution(
                f"No version provided and the inferred filename does not "
                f"contain a version segment: {self.filename}"
            )

        return Version(name_segments[1])

    def _read_dist_info(self):
        raise NotImplementedError

    def _dist_info_dir_name(self) -> str:
        name = canonicalize_name(self.distname).replace("-", "_")
        version = str(self.version).replace("-", "_")
        return f"{name}-{version}.dist-info"

    @property
    def filename(self) -> Optional[str]:
        return self._zip.filename

    @property
    def distname(self) -> str:
        return self._distname

    @property
    def version(self) -> Version:
        return self._version

    # TODO: validate naming conventions, metadata, etc.
    # TODO: use testwheel()
    # TODO: idea: raise when completely out-of-spec, return a compliancy score?
    # TODO: fail if there are multiple .dist-info or .data directories
    # TODO: use lint()
    def validate(self):
        raise NotImplementedError

    # TODO: return a list of defects & negligences present in the wheel file
    # TODO: maybe it's a good idea to put it outside this class?
    # TODO: The implementation could be made simpler by utilizng an internal
    # list of error & lint objects, that have facilities to check a WheelFile
    # object and fix it.
    def lint(self):
        raise NotImplementedError

    # TODO: fix everything we can without guessing
    # TODO: provide sensible defaults
    # TODO: return proper filename
    # TODO: base the fixes on the return value of lint()?
    def fix(self) -> str:
        raise NotImplementedError

    # TODO: ensure RECORD is correct, if it exists
    # TODO: for the first wrong record found, return its arcpath
    # TODO: for the first file not found in the record, return its arcpath
    # TODO: docstring
    def testwheel(self):
        first_broken = self._zip.testzip()
        if first_broken is not None:
            return first_broken
        raise NotImplementedError("Check if RECORD is correct here")

    def refresh_record(self):
        raise NotImplementedError

    def write_metadata(self):
        raise NotImplementedError

    def write_wheeldata(self):
        raise NotImplementedError

    def write_record(self):
        raise NotImplementedError

    @property
    def record(self) -> WheelRecord:
        raise NotImplementedError

    @property
    def metadata(self) -> MetaData:
        raise NotImplementedError

    @property
    def wheeldata(self) -> WheelData:
        raise NotImplementedError

    # TODO: do a final metadata write (in case something was changed)
    # TODO: do a final RECORD recalculation?
    # TODO: idea: might be a good idea to redo RECORD and fail if it's different
    # TODO: docstring
    def close(self) -> None:
        self._zip.close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    @property
    def closed(self) -> bool:
        # ZipFile.fp is set to None upon ZipFile.close()
        return self._zip.fp is None

    def __repr__(self):
        raise NotImplementedError

    # Below - only speculation
    # =========================================================================

    # This should take file objects too
    def add(self, path: str) -> None:
        pass

    # This should take file objects too
    # Change argnames to something better: "zip_path" does not carry the right
    # idea, "target_path" might be too descriptive.
    def extract(self, zip_path, target_path):
        pass

    # Same as with add_meta, there should be a way to add from memory.
    # arcname argument maybe?
    def add_data(self, filename: str) -> None:
        pass

    # Argument name is lacking here.
    # Does this class even need this?
    # Might be better to provide WheelInfo objects, which would inherit from
    # ZipInfo but also cointain the hash from the RECORD. It would simplify the
    # whole implementation.
    # Having this method makes it possible to add comments to files.
    def getinfo(self, name: str) -> ZipInfo:
        pass

    # Does this class even need this?
    def infolist(self) -> List[ZipInfo]:
        pass

    # The name of this method comes from zipfile, but its... misleading.
    # It returns full paths from the archive tree. Not "names". Or is "name"
    # what you would call the archive path in PKZIP?
    def namelist(self) -> List[str]:
        pass

    # Might not be needed. There's no good usecase for it, and ensuring RECORD
    # is valid becomes way harder.
    def open(self, path) -> IO:
        pass

    # This has little use when it returns bytes.
    # Might not be needed.
    def read(self, name) -> bytes:
        pass

    # Might not be needed. We have "add".
    def write(self) -> None:
        pass

    # This could be the replacement for "add from memory", a counterpart for
    # add().
    def writestr(self, arcname, data):
        pass

    # This makes it impossible to ensure that RECORD is valid. But without it,
    # the class is much less flexible.
    @property
    def zipfile(self) -> ZipFile:
        pass
