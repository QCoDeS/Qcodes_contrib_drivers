# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ---------------------------------------------------
import qcodes_contrib_drivers

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
]

try:
    # pylint: disable=unused-import
    from qcodes.sphinx_extensions import parse_parameter_attr  # noqa: F401

    extensions.append("qcodes.sphinx_extensions.parse_parameter_attr")
except ModuleNotFoundError:
    import warnings

    warnings.warn(
        "Could not import 'qcodes.sphinx_extensions.parse_parameter_attr'\n"
        "The documentation parameters will not be rendered correctly.\n"
        "Upgrade to qcodes>=0.28.0 to make use of this functionality.",
        RuntimeWarning,
    )

# -- Project information -----------------------------------------------------

project = "qcodes_contrib_drivers"
copyright = "2019, QCoDeS Users"
author = "QCoDeS Users"

# include special __xxx__ that DO have a docstring
napoleon_include_special_with_doc = True

# NB the line below could be used instead of `napoleon_include_init_with_doc`
# BUT the line below ALWAYS includes the __init__ docstring even if it comes from the
# parent class which might be undesired.
# autoclass_content = "both"

# Document __init__ docstring together with class doctring (when __init__ is present)
napoleon_include_init_with_doc = True

autodoc_default_options = {
    "member-order": "groupwise",
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "_auto", "**.ipynb_checkpoints"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable", None),
    "pyvisa": ("https://pyvisa.readthedocs.io/en/stable", None),
    "IPython": (
        "https://ipython.readthedocs.io/en/stable",
        None,
    ),
    "qcodes": ("https://microsoft.github.io/Qcodes", None),
    "TimeTagger": ("https://www.swabianinstruments.com/static/documentation/TimeTagger/", None),
}


version = "{}".format(qcodes_contrib_drivers.__version__)

release = version

# we are using non local images for badges. These will change so we dont
# want to store them locally.
suppress_warnings = ["image.nonlocal_uri"]

pygments_style = "sphinx"

numfig = True

# Use this kernel instead of the one stored in the notebook metadata:
nbsphinx_kernel_name = "python3"
# always execute notebooks.
nbsphinx_execute = "always"

# we mock modules that for one reason or another is not
# there when generating the docs
autodoc_mock_imports = [
    "spirack",
    "pyspcm",
    "keysightSD1",
    "nidaqmx",
    "niswitch",
    "zhinst",
    "msl"
]
