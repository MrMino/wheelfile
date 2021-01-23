

<table style="border: none">
<tr style="border: none">
<td style="border: none">
<h1 style='border-bottom-style: none' align="center"> Wheelfile
🔪🧀</h1>

This library aims to make it dead simple to create a format-compliant [.whl
file (wheel)](https://pythonwheels.com/). It aims to provide an API comparable
to [zipfile](https://docs.python.org/3/library/zipfile.html). Use this if you
wish to inspect or create wheels in your code.

For a quick look, see example on the right, which packages wheelfile
module itself into a wheel 🤸.

#### What's the difference between this and [wheel](https://pypi.org/project/wheel/)?

"Wheel" tries to provide a reference implementation for the standard. It is used
by setuptools and has its own CLI, but no stable API. The goal of Wheelfile is
to provide a simple API.

## Ackonwledgements

Thanks to [Paul Moore](https://github.com/pfmoore) for providing
[his gist](https://gist.github.com/pfmoore/20f3654ca33f8b14f0fcb6dfa1a6b469)
of basic metadata parsing logic, which helped to avoid many foolish mistakes
in the initial implementation.

</td>
<td style="border: none">

```
pip install wheelfile
```

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

# 🧀
```

</td>
</tr>
