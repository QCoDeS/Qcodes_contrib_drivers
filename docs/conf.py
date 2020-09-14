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


# -- Project information -----------------------------------------------------

project = 'qcodes_contrib_drivers'
copyright = '2019, QCoDeS Users'
author = 'QCoDeS Users'


# -- General configuration ---------------------------------------------------
import qcodes_contrib_drivers
import sphinx_rtd_theme

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'nbsphinx',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
]

# include special __xxx__ that DO have a docstring
# it probably means something important
napoleon_include_special_with_doc = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '_auto',
                    '**.ipynb_checkpoints']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'matplotlib': ('https://matplotlib.org/', None),
    'python': ('https://docs.python.org/3.6', None),
    'numpy': ('https://docs.scipy.org/doc/numpy', None),
    'py': ('https://pylib.readthedocs.io/en/stable/', None),
    'pyvisa': ('https://pyvisa.readthedocs.io/en/master/', None),
    'IPython': ('https://ipython.readthedocs.io/en/stable/', None,),
    'qcodes': ('https://qcodes.github.io/Qcodes/', None)
}


version = '{}'.format(qcodes_contrib_drivers.__version__)

release = version

# we are using non local images for badges. These will change so we dont
# want to store them locally.
suppress_warnings = ['image.nonlocal_uri']

pygments_style = 'sphinx'

numfig = True

# Use this kernel instead of the one stored in the notebook metadata:
nbsphinx_kernel_name = 'python3'
# always execute notebooks.
nbsphinx_execute = 'always'

# we mock modules that for one reason or another is not
# there when generating the docs
autodoc_mock_imports = ['spirack',
                        'pyspcm',
                        'keysightSD1',
                        'nidaqmx',
                        'niswitch',
                        'zhinst']

# we allow most types from the typing modules to be used in
# docstrings even if they don't resolve
nitpick_ignore = [('py:class', 'Optional'),
                  ('py:class', 'Dict'),
                  ('py:class', 'Union'),
                  ('py:class', 'Any'),
                  ('py:class', 'Tuple'),
                  ('py:class', 'List'),
                  ('py:class', 'Sequence'),
                  ('py:class', 'Iterable'),
                  ('py:class', 'Type'),
                  # These are some types currently in use
                  # in docstrings not actually defined anywhere
                  ('py:class', 'io_manager'),
                  ('py:class', 'chan_type'),
                  ('py:class', 'SD_Wave'),
                  ('py:class', 'array'),
                  # private types that are not currently documented so links
                  # will not resolve
                  ('py:class', 'SweepFixedValues'),
                  ('py:class', 'qcodes_contrib_drivers.drivers.RohdeSchwarz.'
                               'private.HMC804x._RohdeSchwarzHMC804x'),
                  # We don't generate the docs for function since
                  # it is deprecated
                  ('py:class', 'Function'),
                  # We do not document any QCoDeS classes
                  ('py:class', 'Parameter'),
                  # External types that for some reason or the other
                  # don't resolve.
                  ('py:class', 'json.encoder.JSONEncoder'),
                  ('py:class', 'SPI_rack'),
                  ('py:class', 'spirack.SPI_rack'),
                  ('py:class', 'ViAttr'),
                  ('py:class', 'unittest.case.TestCase'),
                  ('py:class', 'builtins.AssertionError'),
                  ('py:class', '_ctypes.Structure'),
                  ('py:exc', 'visa.VisaIOError')
                  ]
