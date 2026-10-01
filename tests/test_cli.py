import pytest

from casefilter.cli import main


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["   "], "request is empty"),
        (["leukemia", "--n", "0"], "--n must be at least 1"),
        (["leukemia", "--prompt", "classify.v9"], "unknown prompt"),
        (["leukemia", "--prompt", "expand.v1"], "unknown prompt"),
    ],
)
def test_invalid_arguments_exit_with_a_clear_message(argv, message, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err
