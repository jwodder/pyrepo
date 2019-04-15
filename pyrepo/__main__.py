import click
from   .init    import init
from   .release import release

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    pass

main.add_command(init, 'init')
main.add_command(release, 'release')

if __name__ == '__main__':
    main()
