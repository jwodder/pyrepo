.. image:: http://www.repostatus.org/badges/latest/wip.svg
    :target: http://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

{% if has_travis %}
.. image:: https://travis-ci.org/jwodder/{{repo_name}}.svg?branch=master
    :target: https://travis-ci.org/jwodder/{{repo_name}}

.. image:: https://coveralls.io/repos/github/jwodder/{{repo_name}}/badge.svg?branch=master
    :target: https://coveralls.io/github/jwodder/{{repo_name}}?branch=master

{% endif %}
{% if has_pypi %}
.. image:: https://img.shields.io/pypi/pyversions/{{project_name}}.svg
    :target: https://pypi.python.org/pypi/{{project_name}}

{% endif %}
.. image:: https://img.shields.io/github/license/jwodder/{{repo_name}}.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/{{repo_name}}>`_
{% if has_pypi %}
| `PyPI <https://pypi.python.org/pypi/{{project_name}}>`_
{% endif %}
{% if has_docs %}
| `Documentation <https://{{rtfd_name}}.readthedocs.io>`_
{% endif %}
| `Issues <https://github.com/jwodder/{{repo_name}}/issues>`_

INSERT LONG DESCRIPTION HERE

Installation
============
{% if py2 %}
Just use `pip <https://pip.pypa.io>`_ (You have pip, right?) to install
``{{project_name}}`` and its dependencies::

    pip install {{project_name}}
{% else %}
``{{project_name}}`` requires Python {{python_versions[0]}} or higher.  Just
use `pip <https://pip.pypa.io/>`_ for Python 3 (You have pip, right?) to
install ``{{project_name}}`` and its dependencies::

    pip3 install {{project_name}}
{% endif %}


Examples
========
INSERT EXAMPLES HERE
