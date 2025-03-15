from typing import Dict

from django.apps import apps
from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand


def discover_commands() -> Dict[str, Dict]:
    """
    Discover all available Django management commands and their arguments.

    Returns:
        Dict mapping command names to their argument specifications
    """
    # TODO: Add logging to the command logger
    if not apps.ready:
        try:
            import django

            django.setup()
        except Exception:
            return {}

    commands = {}
    django_commands = get_commands()

    # Sort command names alphabetically
    for command_name in sorted(django_commands.keys()):
        app_name = django_commands[command_name]
        try:
            command = load_command_class(app_name, command_name)
            if isinstance(command, BaseCommand):
                parser = command.create_parser("manage.py", command_name)
                actions = {}

                # Get all arguments from the parser
                for action in parser._actions:
                    if action.dest != "help":  # Skip help action
                        actions[action.dest] = {
                            "flags": action.option_strings,
                            "help": action.help,
                            "required": action.required,
                            "default": action.default,
                            "choices": action.choices,
                            "type": action.type.__name__ if action.type else None,
                        }

                commands[command_name] = {
                    "app": app_name,
                    "help": command.help,
                    "arguments": actions,
                }
        except Exception:
            continue

    return commands
