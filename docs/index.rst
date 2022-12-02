wheelfile
=========


.. automodule:: wheelfile

Other examples
--------------

Here's a list of more in-depth examples. Each example is based on a real piece
of software that's used "in the wild" at the time of writing.

.. toctree::
    :maxdepth: 1

    examples/buildscript.rst
    examples/pep-517-builder.rst

Installation
------------

To be able to use the module, you have to install it first::

    pip install wheelfile

Main class
----------
.. autoclass:: WheelFile
    :special-members:
    :members:

Metadata classes
----------------
.. autoclass:: WheelRecord
    :special-members:
    :members:

.. autoclass:: WheelData
    :special-members:
    :members:

.. autoclass:: MetaData
    :special-members:
    :members:

.. autoclass:: EntryPoints
    :special-members:
    :members:

Exceptions
----------
.. autoexception:: BadWheelFileError

.. autoexception:: UnnamedDistributionError

.. autoexception:: ProhibitedWriteError


Utilities
---------
.. autofunction:: resolved
