"""Tests for OutputFormatter."""

from cli.cli.output import OutputFormatter


class TestOutputFormatter:
    def test_json_mode_suppresses_info(self, capsys):
        out = OutputFormatter(json_mode=True)
        out.info("hello")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_mode_suppresses_ok(self, capsys):
        out = OutputFormatter(json_mode=True)
        out.ok("done")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_mode_suppresses_warn(self, capsys):
        out = OutputFormatter(json_mode=True)
        out.warn("beware")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_mode_prints_json(self, capsys):
        out = OutputFormatter(json_mode=True)
        out.print_json({"key": "value"})
        captured = capsys.readouterr()
        assert '"key"' in captured.out
        assert '"value"' in captured.out

    def test_non_json_shows_info(self, capsys):
        out = OutputFormatter(json_mode=False)
        out.info("hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out

    def test_pluralize(self):
        from cli.utils.validators import pluralize

        assert pluralize(1, "rule") == "1 rule"
        assert pluralize(3, "rule") == "3 rules"
        assert pluralize(2, "version") == "2 versions"

    def test_truncate(self):
        from cli.utils.validators import truncate

        assert truncate("short") == "short"
        assert len(truncate("x" * 100, max_len=10)) == 10

    def test_is_valid_version(self):
        from cli.utils.validators import is_valid_version

        assert is_valid_version("1.0.0") is True
        assert is_valid_version("0.0.1") is True
        assert is_valid_version("1.0") is False
        assert is_valid_version("abc") is False

    def test_stdlib_modules_present(self):
        from cli.utils.validators import STDLIB_MODULES

        assert "os" in STDLIB_MODULES
        assert "sys" in STDLIB_MODULES
        assert "json" in STDLIB_MODULES
