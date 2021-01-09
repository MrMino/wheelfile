# We do not target python2.
# Which python3 versions should we target? 3.6+ seems like a good idea.
import csv
import hashlib
import zipfile

from collections import namedtuple
from inspect import signature
from io import StringIO
from packaging.tags import parse_tag
from email.message import EmailMessage
from email import message_from_string

from typing import Optional, Union, List, Dict, IO, BinaryIO

__version__ = '0.0.1'


# TODO: change AssertionErrors to custom exceptions?
# TODO: idea - install wheel - w/ INSTALLER file
# TODO: idea - wheel from an installed distribution?


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
# TODO: ensure name is the same as wheelfile name
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

        Ommit this parameter if the author and current maintainer is the same
        person.

    maintainer_email
        Email address of the person specified in the "maintainer" parameter.
        Format of this field must follow the format of RFC-822 "From:" header
        field.

        Ommit this parameter if the author and current maintainer is the same
        person.

    license
        Text of the license that covers this distribution. If license
        classifier is used, this parameter may be ommited or used to specify the
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
        PEP-440 version identificator, that specifies the set Python language
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
    Wheel-Version, the wheel format version specifier, is unchangable. Version
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
# TODO: from_str
class WheelRecord:
    """Contains logic for creation and modification of RECORD files.

    Keeps track of files in the wheel and their hashes.

    For the full spec, see PEP-376 "RECORD" section, PEP-627,
    "The .dist-info directory" section of PEP-427, and
    https://packaging.python.org/specifications/recording-installed-packages/.
    """
    HASH_ALGO = hashlib.sha256
    HASH_BUF_SIZE = 65536

    _Record = namedtuple('Record', 'path hash size')

    def __init__(self):
        self._records: Dict[str, self._Record] = {}

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
        buf = StringIO()
        records = csv.DictWriter(buf, fieldnames=self._Record._fields)
        for entry in self._records.values():
            records.writerow(entry._asdict())
        return buf.getvalue()

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
    def _entry(cls, arc_path: str, buf: BinaryIO) -> str:
        size = 0
        hasher = cls.HASH_ALGO()
        while True:
            data = buf.read(cls.HASH_BUF_SIZE)
            size += len(data)
            if not data:
                break
            hasher.update(data)
        hash_hex = hasher.name + '=' + hasher.hexdigest()
        return cls._Record(arc_path, hash_hex, size)

    def __eq__(self, other):
        if isinstance(other, WheelRecord):
            return str(self) == str(other)
        else:
            return NotImplemented


# TODO: testwheel() method
# TODO: use ZipFile.testzip()
# TODO: facilities for converting arbitrary ZIPs to Wheels
class WheelFile:
    # This should check if the zip name conforms to the wheel standard
    # Semantics to define for 'w' and 'a' modes:
    #   - the file does not exist, create a new empty one
    #   - the file exists, but is not a zip
    #   - the file exists, is a zip, but not a wheel
    #   - the file exists, is a wheel
    # Everything else should error out.
    def __init__(self) -> None:
        pass

    # This should take file objects too
    def add(self, path: str) -> None:
        pass

    # This should take file objects too
    # Change argnames to something better: "zip_path" does not carry the right
    # idea, "target_path" might be too descriptive.
    def extract(self, zip_path, target_path):
        pass

    # Adding metadata file from filesystem is one thing, it should also be
    # possible to add metadata from memory without FS acting as a middleman.
    # arcname argument maybe?
    def add_meta(self, filename: str) -> None:
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
    def getinfo(self, name: str) -> zipfile.ZipInfo:
        pass

    # Does this class even need this?
    def infolist(self) -> List[zipfile.ZipInfo]:
        pass

    # The name of this method comes from zipfile, but its... misleading.
    # It returns full paths from the archive tree. Not "names". Or is "name"
    # what you would call the archive path in PKZIP?
    def namelist(self) -> List[str]:
        pass

    # Do we actually want to have the open → close semantics?
    # Open → close semantics might be required in order to ensure a given file
    # comes last in the binary representation.
    # This should do a final recalculation of RECORD
    def close(self) -> None:
        pass

    @property
    def closed(self) -> bool:
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
    def zipfile(self) -> zipfile.ZipFile:
        pass

    # This name is kinda verbose and can still be conflated with
    # "package_metadata".
    @property
    def wheel_metadata(self) -> WheelData:
        pass

    # Too verbpose?
    # Maybe "pkg_info"?
    @property
    def package_metadata(self) -> PackageMeta:
        pass

    @property
    def record(self) -> WheelRecord:
        pass

    # TODO: properties for data that is included in the naming
    # TODO: compression level arguments - is compression even supported by Pip?
    # TODO: comment property
    # TODO: debug propery, as with ZipFile.debug

    raise NotImplementedError("Implement those below!")

    def __del__(self):
        raise NotImplementedError("Implement me!")
        self.close()

    def __enter__(self):
        raise NotImplementedError("Implement me!")

    def __exit__(self):
        raise NotImplementedError("Implement me!")
