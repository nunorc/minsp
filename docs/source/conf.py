
import os, sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'minsp'
copyright = '2024, Nuno Carvalho'
author = 'Nuno Carvalho'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon' ]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
