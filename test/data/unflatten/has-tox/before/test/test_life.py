from foobar import life


def test_die_alone() -> None:
    assert life([(0, 0)]) == set()
