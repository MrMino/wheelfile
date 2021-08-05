PEP-517 Builder
===============

Thanks to `PEP-517 <https://www.python.org/dev/peps/pep-0517/>`__ and `PEP-518
<https://www.python.org/dev/peps/pep-0517/>`__ you can create your very own
package builders, and make them compatible with ``pip install
path/to/repository``.

``wheelfile`` makes developing your own builder & hooks straightforward.

The code at the bottom of this page shows an example of a simple builder that
can create bdist and sdist distributions from a project tree with source code
inside ``src/`` directory.

How to use this example
-----------------------
Package builders are expected to be installed inside the environment site - the
project tree is not included in the import search path when looking for the
hooks.
In order to make this example easier to follow, its code has been packaged into
``pep-517-example`` package, and uploaded to PyPI, so that you can install it
and fiddle with mechanics right away, without having to create your own
package.

You can install this example using::

    pip install pep-517-example

Inside this package, there is a simple entry point script that opens the hook
source inside an editor. You can run it using::

    python -m pep_517_example

Project configuration: pyproject.toml
-------------------------------------
PEP-518 and the example builder expect the project tree to include a
``pyproject.toml`` file. This file specifies the builder that should be used
for creating the package (and installing it afterwards, if ``pip install`` is
used). Additionally, the builder reads its own configuration from this file.

The builder reads the file using ``get_config()`` function.

Here is an example of the contents of this file::

    [build-system]
    requires = ['pep-517-example']
    build-backend = 'pep_517_example.builder'

    [tool.pep_517_example]
    name = "my_package"
    version = "1.0.0"
    maintainers = "Jack Sparrow"
    maintainers_emails = "sparrow.jack@pearl.black"


Project tree & building a wheel using pip
-----------------------------------------
Another file that our builder will expect, is ``requirements.txt``. To sum up,
a project directory that this builder expects should have the following
structure::

    .
    ├── pyproject.toml
    ├── requirements.txt
    └── src
        ├── ...
        └── app.py


After navigating to this directory, you can use the following `pip` command to
build a wheel::

    pip wheel . --no-build-isolation

This command will make ``pip`` politely run the builder hooks over the project
directory tree.

The ``--no-build-isolation`` flag will make `pip` use the builder installed
within your environment (the ``pep_517_example`` one), instead of downloading
it with all of its dependencies from scratch.

After issuing the command above, you should see a wheel po up in the directory
you're currently in::

    my_package-1.0.0-py3-none-any.whl

Builder source code
-------------------

.. literalinclude:: ./pep_517_builder.py
