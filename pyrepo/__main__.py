import click
from   .        import __version__
from   .init    import init
from   .release import release

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    __version__, '-V', '--version', message='%(prog)s %(version)s',
)
def main():
    pass

main.add_command(init, 'init')
main.add_command(release, 'release')

if __name__ == '__main__':
    main()
