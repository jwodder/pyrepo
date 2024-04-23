#!/usr/bin/env pipx run
# /// script
# dependencies = ["click ~= 8.0", "linesep ~= 0.5.0"]
# ///
from __future__ import annotations
from pathlib import Path
import re
import sys
import click
from linesep import read_paragraphs


@click.command()
@click.argument(
    "infile", type=click.Path(dir_okay=False, exists=True, path_type=Path), nargs=-1
)
def main(infile: tuple[Path]) -> None:
    for fpath in infile:
        print(fpath)
        with fpath.open() as fp:
            badge_names = []
            new_content = ""
            in_imgs = True
            for para in read_paragraphs(fp):
                if in_imgs and (
                    m := re.match(r"\.\. image:: (\S+)$", para, flags=re.M)
                ):
                    url = m[1]
                    rem_badge = para[m.end(1) :].lstrip("\r\n")
                    if url.startswith("https://www.repostatus.org/"):
                        name = "repostatus"
                    elif "actions/workflows" in url:
                        name = "ci-status"
                    elif url.startswith("https://codecov.io/"):
                        name = "coverage"
                    elif url.startswith("https://img.shields.io/pypi/pyversions/"):
                        name = "pyversions"
                    elif url.startswith("https://img.shields.io/conda/vn/conda-forge/"):
                        name = "conda"
                    elif url.startswith("https://img.shields.io/github/license/"):
                        name = "license"
                    else:
                        sys.exit(f"Unknown image URL: {url!r}")
                    badge_names.append(name)
                    new_content += f".. |{name}| image:: {url}\n{rem_badge}"
                else:
                    in_imgs = False
                    new_content += para
        fpath.write_text(" ".join(f"|{n}|" for n in badge_names) + "\n\n" + new_content)


if __name__ == "__main__":
    main()
