from typing import Literal
from django.core.management.base import BaseCommand
from ...command_discovery import (
    generate_powershell_completion,
    generate_bash_completion,
)


class Command(BaseCommand):
    help = "Generate shell completion script for Django management commands"

    def add_arguments(self, parser):
        # TODO: Switch choices to use the dictionary of functions with keys of shell type
        parser.add_argument(
            "shell",
            choices=["powershell", "bash"],
            help="Shell to generate completion script for (powershell or bash)",
        )
        parser.add_argument(
            "--output",
            "-o",
            help="Output file path for the shell script (defaults to django_completion.ps1 for PowerShell or django_completion.sh for Bash)",
        )

    def handle(self, *args, **options):
        # TODO: Switch to a dictionary of functions with keys of shell type
        shell: Literal["powershell", "bash"] = options["shell"]
        output_file = options["output"]

        if shell == "powershell":
            script = generate_powershell_completion()
            default_output = "django_completion.ps1"
            source_cmd = ". .\\{}"
        else:  # bash
            script = generate_bash_completion()
            default_output = "django_completion.sh"
            source_cmd = "source ./{}"

        output_file = output_file or default_output

        with open(output_file, "w") as f:
            f.write(script)

        self.stdout.write(
            self.style.SUCCESS(
                f"{shell.title()} completion script generated at {output_file}\n"
                "To use it, run the following command:\n"
                f"{source_cmd.format(output_file)}"
            )
        )
