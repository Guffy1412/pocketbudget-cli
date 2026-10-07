from pocketbudget import cli


def test_cli_entry_point_exists_and_runs() -> None:
    assert cli.main([]) == 0
