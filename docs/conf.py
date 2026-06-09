import logging
from os import environ
from datetime import date

# autodoc imports the tino.* modules — tino.mcp.server builds its ASGI app at
# import time and logs while doing so. Silence the application logger so those
# INFO/WARNING lines don't clutter the docs build; Sphinx's own warnings use a
# separate logger and remain visible.
logging.getLogger('tino').setLevel(logging.ERROR)

#
# ⚙️ Generic options.
#

project   = 'TINO'
copyright = f'{date.today().strftime('%Y')}, confirm IT'
author    = 'confirm IT'

#
# 🎨 Theme options.
#

html_theme       = 'furo'
html_static_path = ['_static']
html_extra_path  = ['_extras']
html_css_files   = ['custom.css']

html_theme_options = {
    'light_logo': 'logo.svg',
    'dark_logo': 'logo.svg',
    'sidebar_hide_name': True,
}

#
# 🧩 Extension options.
#

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.intersphinx',
    'sphinx.ext.ifconfig',
    'sphinx.ext.todo',
    'sphinxcontrib.mermaid',
]

autosectionlabel_prefix_document = True

#
# 📝 To Do.
#

todo_include_todos = not environ.get('TINO_HIDE_TODOS', 'false') in {'true', 'yes', 'on', '1'}
todo_link_only     = True

#
# 🔗 Intersphinx.
#

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'handbook': ('https://handbook.confirm.ch', None),
}
