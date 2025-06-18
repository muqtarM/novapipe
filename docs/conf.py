import os
import sys
sys.path.insert(0, os.path.abspath(".."))  # so autodoc can import novapipe

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

html_theme = "sphinx_rtd_theme"
