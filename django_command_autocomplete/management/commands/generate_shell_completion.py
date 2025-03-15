import os
from django.core.management.base import BaseCommand

from django_command_autocomplete.command_discovery import discover_commands
from django_command_autocomplete.generators.base import BaseGenerator


class Command(BaseCommand):
    help = "Generate shell completion script for Django management commands"

    def add_arguments(self, parser):
        parser.add_argument(
            "shell",
            choices=BaseGenerator.get_all_command_flags(),
            help="Shell to generate completion script for",
        )
        parser.add_argument(
            "--output",
            "-o",
            help="Output file path for the shell script",
        )

    def handle(self, *args, **options):
        shell: str = options["shell"]
        output_file: str = options["output"]

        generator: BaseGenerator = BaseGenerator.get_generator_by_flag(shell)

        if not generator:
            error_message = "Unable to find generator for shell {}".format(shell)
            self.style.ERROR(error_message)
            raise ValueError(error_message)

        try:
            commands = discover_commands()

            script = generator.generate_output(
                commands=commands, project_path=os.getcwd()
            )
            output_file = output_file or generator.get_default_output_path()

            with open(output_file, "w") as f:
                f.write(script)

            self.stdout.write(
                self.style.SUCCESS(generator.generate_helptext(output_file))
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(str(e)))
