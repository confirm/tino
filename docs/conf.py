from os import environ
from datetime import date

#
# ⚙️ Generic options.
#

project   = 'Typarr'
copyright = f'{date.today().strftime('%Y')}, confirm IT'
author    = 'confirm IT'

#
# 🎨 Theme options.
#

html_theme       = 'furo'
html_static_path = ['_static']
html_extra_path  = ['_extras']

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
]

#
# 📝 To Do.
#

todo_include_todos = not environ.get('TYPARR_HIDE_TODOS', 'false') in {'true', 'yes', 'on', '1'}
todo_link_only     = True

#
# 🔗 Intersphinx.
#

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'handbook': ('https://handbook.confirm.ch', None),
}
