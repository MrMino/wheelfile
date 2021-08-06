import os
import sys

# Makes autodoc look one directory above
sys.path.insert(0, os.path.abspath(".."))

project = "wheelfile"
copyright = "2021, Błażej Michalik"
author = "MrMino"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]
html_theme = "furo"
