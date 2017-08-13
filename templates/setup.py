{% if importable %}
from setuptools import setup
setup()
{% else %}
{% if py2 %}
import errno
{% endif %}
from   os.path    import dirname, join
import re
from   setuptools import setup{% if not is_flat_module %}, find_packages{% endif %}

{% if is_flat_module %}
with open(join(dirname(__file__), {{(import_name + '.py')|repr}})) as fp:
{% else %}
with open(join(dirname(__file__), {{import_name|repr}}, '__init__.py')) as fp:
{% endif %}
    for line in fp:
        m = re.search(r'^\s*__version__\s*=\s*([\'"])([^\'"]+)\1\s*$', line)
        if m:
            version = m.group(2)
            break
    else:
        raise RuntimeError('Unable to find own __version__ string')

try:
    with open(join(dirname(__file__), 'README.rst')) as fp:
        long_desc = fp.read()
{% if py2 %}
except EnvironmentError as e:
    if e.errno == errno.ENOENT:
        long_desc = None
    else:
        raise
{% else %}
except FileNotFoundError:
    long_desc = None
{% endif %}

setup(
    name={{project_name|repr}},
    version=version,
{% if is_flat_module %}
    py_modules=[{{import_name|repr}}],
{% else %}
    packages=find_packages(),
{% endif %}
    license='MIT',
    author={{author|repr}},
    author_email={{(email_username + '@' + email_hostname)|repr}},
    ###keywords='',
    description={{short_description|repr}},
    long_description=long_desc,
    url={{('https://github.com/jwodder/' + repo_name)|repr}},

    python_requires={{python_requires|repr}},

    install_requires=[],

    classifiers=[
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',

{% if py2 %}
        'Programming Language :: Python :: 2',
{% for v in py2_versions %}
        'Programming Language :: Python :: {{v}}',
{% endfor %}
{% else %}
        'Programming Language :: Python :: 3 :: Only',
{% endif %}
        'Programming Language :: Python :: 3',
{% for v in py3_versions %}
        'Programming Language :: Python :: {{v}}',
{% endfor %}
        'Programming Language :: Python :: Implementation :: CPython',
{% if py2 %}
        'Programming Language :: Python :: Implementation :: PyPy',
{% endif %}

        'License :: OSI Approved :: MIT License',

        ###
    ],

    entry_points={
        "console_scripts": [
        ]
    },
)
{% endif %}
