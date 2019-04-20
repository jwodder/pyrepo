from   configparser import ConfigParser
from   pathlib      import Path
from   types        import SimpleNamespace
import click

DEFAULT_CFG = str(Path.home() / '.config' / 'pyrepo.cfg')

DEFAULTS = {
    'options': {
        'author': 'Anonymous',
        'author_email': 'USER@HOST',
       #'saythanks_to': None,
    },
    "pyversions": {
        'minimum': '3.4',
        'maximum': '3.7',
    }
}

MAJOR_PYTHON_VERSIONS = [3]
PYVER_TEMPLATE = '"3.X"'

def configure(ctx, filename):
    cfg = ConfigParser(interpolation=None)
    cfg.optionxform = lambda s: s.lower().replace('-', '_')
    cfg.read_dict(DEFAULTS)
    if filename is not None:
        cfg.read(filename)
    try:
        min_pyversion = parse_pyversion(cfg["pyversions"]["minimum"])
    except ValueError:
        raise click.UsageError(
            f'Invalid setting for pyversions.minimum config option:'
            f' {cfg["pyversions"]["minimum"]!r}: must be in form'
            f' {PYVER_TEMPLATE}'
        )
    try:
        max_pyversion = parse_pyversion(cfg["pyversions"]["maximum"])
    except ValueError:
        raise click.UsageError(
            f'Invalid setting for pyversions.maximum config option:'
            f' {cfg["pyversions"]["maximum"]!r}: must be in form'
            f' {PYVER_TEMPLATE}'
        )
    if min_pyversion > max_pyversion:
        raise click.UsageError(
            'Config option pyversions.minimum cannot be greater than'
            ' pyversions.maximum'
        )
    ctx.obj = SimpleNamespace(
        pyversions=pyver_range(min_pyversion, max_pyversion)
    )
    if not cfg.has_option("options", "python_requires"):
        cfg["options"]["python_requires"] = '{}.{}'.format(*min_pyversion)
    from .__main__ import main
    for cmdname, cmdobj in main.commands.items():
        defaults = dict(cfg["options"])
        if cfg.has_section("options." + cmdname):
            defaults.update(cfg["options." + cmdname])
        for p in cmdobj.params:
            if isinstance(p, click.Option) and p.is_flag and p.name in defaults:
                try:
                    defaults[p.name] \
                        = cfg.BOOLEAN_STATES[defaults[p.name].lower()]
                except KeyError:
                    raise click.UsageError(
                        f'Invalid boolean value for config option {p.name}:'
                        f' {defaults[p.name]!r}'
                    )
        ctx.default_map.setdefault(cmdname, {}).update(defaults)

def parse_pyversion(s):
    major, _, minor = s.partition('.')
    major = int(major)
    minor = int(minor)
    if major not in MAJOR_PYTHON_VERSIONS:
        raise ValueError
    return (major, minor)

def pyver_range(min_pyversion, max_pyversion):
    minmajor, minminor = min_pyversion
    maxmajor, maxminor = max_pyversion
    if minmajor != maxmajor:
        raise NotImplementedError
    return [f'{minmajor}.{i}' for i in range(minminor, maxminor+1)]
