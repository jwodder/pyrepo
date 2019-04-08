{% if importable %}
from setuptools import setup
setup()
{% else %}
{% if py2 %}
import io
{% endif %}
from   os.path    import dirname, join
import re
from   setuptools import setup

{% if is_flat_module %}
with {% if py2 %}io.{% endif %}open(join(dirname(__file__), {{(import_name + '.py')|repr}}), encoding='utf-8') as fp:
{% else %}
with {% if py2 %}io.{% endif %}open(join(dirname(__file__), {{import_name|repr}}, '__init__.py'), encoding='utf-8') as fp:
{% endif %}
    for line in fp:
        m = re.search(r'^\s*__version__\s*=\s*([\'"])([^\'"]+)\1\s*$', line)
        if m:
            version = m.group(2)
            break
    else:
        raise RuntimeError('Unable to find own __version__ string')

setup(version=version)
{% endif %}
