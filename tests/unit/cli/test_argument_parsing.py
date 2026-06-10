"""Unit tests for the CLI argument parser.

Parsing is pure (no network), so these check the parser in isolation: each subcommand
maps to the right handler and coerces its arguments correctly.
"""

from __future__ import annotations

import pytest

from cli.main import (
    build_parser, cmd_recipes, cmd_suggestions, cmd_pantry, cmd_plan, cmd_shopping,
)


def parse(argv):
    return build_parser().parse_args(argv)


def test_recipes_search_maps_to_handler():
    args = parse(["recipes", "--search", "pasta"])
    assert args.command == "recipes" and args.search == "pasta" and args.func is cmd_recipes


def test_suggestions_limit_default_and_override():
    assert parse(["suggestions"]).limit == 10
    args = parse(["suggestions", "--limit", "3"])
    assert args.limit == 3 and args.func is cmd_suggestions


def test_plan_add_takes_three_values():
    args = parse(["plan", "--add", "2026-06-10", "dinner", "1"])
    assert args.add == ["2026-06-10", "dinner", "1"] and args.func is cmd_plan


def test_pantry_set_coerces_int_and_float():
    args = parse(["pantry", "--set", "5", "--qty", "2.5", "--unit", "g"])
    assert args.set == 5 and args.qty == 2.5 and args.unit == "g" and args.func is cmd_pantry


def test_shopping_list_date_range():
    args = parse(["shopping-list", "--start", "2026-06-10", "--end", "2026-06-16"])
    assert args.start == "2026-06-10" and args.end == "2026-06-16" and args.func is cmd_shopping


def test_recipe_requires_integer_id():
    assert parse(["recipe", "7"]).id == 7
    with pytest.raises(SystemExit):
        parse(["recipe", "notanumber"])


def test_missing_subcommand_is_an_error():
    with pytest.raises(SystemExit):
        parse([])


def test_global_url_flag():
    args = parse(["--url", "http://host:9000", "recipes"])
    assert args.url == "http://host:9000"
