import logging
from   operator        import attrgetter
import os
from   shutil          import copytree
from   click.testing   import CliRunner
import pytest
from   pyrepo.__main__ import main
from   test_helpers    import DATA_DIR, assert_dirtrees_eq, show_result

@pytest.mark.parametrize(
    'dirpath',
    sorted((DATA_DIR / 'unflatten').iterdir()),
    ids=attrgetter("name"),
)
def test_pyrepo_init(caplog, dirpath, tmp_path):
    caplog.set_level(logging.INFO)  # to catch errors in logging statements
    tmp_path /= 'tmp'  # copytree() can't copy to a dir that already exists
    copytree(dirpath / 'before', tmp_path)
    r = CliRunner().invoke(
        main,
        ['-c', os.devnull, '-C', str(tmp_path), 'unflatten'],
        # Standalone mode needs to be disabled so that `ClickException`s (e.g.,
        # `UsageError`) will be returned in `r.exception` instead of a
        # `SystemExit`
        standalone_mode=False,
    )
    assert r.exit_code == 0, show_result(r)
    assert_dirtrees_eq(tmp_path, dirpath / 'after')