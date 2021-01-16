<h1 style='border-bottom-style: none' align="center"> Wheelfile
🔪🧀</h1>

<table style="border: none">
<tr style="border: none">
<td style="border: none">

This library tries to make it dead simple to create a format-compliant
[.whl file (wheel)](https://pythonwheels.com/). It aims to provide an API
comparable to [zipfile](https://docs.python.org/3/library/zipfile.html). Use
this if you wish to create wheels in your code.

For a quick look, see example on the right, which makes wheelfile
package itself into a wheel 🤸.

#### What's the difference between this and [wheel](https://pypi.org/project/wheel/)?

"Wheel" tries to provide a reference implementation for the standard. It is used
by setuptools and has its own CLI, but no stable API. The goal of Wheelfile is
to provide a simple API.

## Related PEPs and specs
- [PEP-427 - The Wheel Binary Package Format
  1.0](https://www.python.org/dev/peps/pep-0427/)
- [PEP-425 - Compatibility Tags for Built
  Distributions](https://www.python.org/dev/peps/pep-0425/)
- [PEP-376 - Database of Installed Python Distributions - RECORD
  file](https://www.python.org/dev/peps/pep-0376/#record)
- [PEP-566 - Metadata for Python Software Packages
  v2.1](https://www.python.org/dev/peps/pep-0566/)
- [PEP-345 - Metadata for Python Software Packages
  v1.2](https://www.python.org/dev/peps/pep-0345/)
- [PEP-314 - Metadata for Python Software Packages
  v1.1](https://www.python.org/dev/peps/pep-0314/)
- [PEP-241 - Metadata for Python Software Packages
  v1.0](https://www.python.org/dev/peps/pep-0241/)


## Ackonwledgements

Thanks to [Paul Moore](https://github.com/pfmoore) for providing
[his gist](https://gist.github.com/pfmoore/20f3654ca33f8b14f0fcb6dfa1a6b469)
of basic metadata parsing logic, which helped to avoid many foolish mistakes
in the initial implementation.

</td>
<td style="border: none">

```py
from wheelfile import WheelFile, __version__

spec = {
    'distname': 'wheelfile',
    'version': __version__
}

requirements = [
    'packaging ~= 20.8'
]

with WheelFile(mode='w', **spec) as wf:
    wf.metadata.requires_dists = requirements
    wf.write('./wheelfile.py')

```

</td>
</tr>
