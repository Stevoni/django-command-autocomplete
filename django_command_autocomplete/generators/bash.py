import os
from typing import Dict

from django_command_autocomplete.generators.base import BaseGenerator


class BashGenerator(BaseGenerator):
    def get_default_output_path(self) -> str:
        return "django_completion.sh"

    @staticmethod
    def get_command_flag() -> str:
        return "bash"

    def generate_output(self, commands: Dict[str, Dict], **kwargs) -> str:
        return self.generate_bash_completion(commands, **kwargs)

    def generate_bash_completion(self, commands, project_path) -> str:
        """
        Generate Bash completion script.

        Returns:
            String containing the Bash completion script
        """
        project_path = os.path.abspath(project_path)

        script = f"""
    # Django Command Completion for Bash
    # Generated for project: {project_path}

    _is_django_project_path() {{
        current_path=$(pwd)
        project_path="{project_path}"

        # Check if we're in the project path or a subdirectory
        case "$current_path" in
            "$project_path"*) return 0 ;;
            *) return 1 ;;
        esac
    }}

    _django_completion()
    {{
        # Only provide completions when in the correct project directory
        if ! _is_django_project_path; then
            return
        fi

        local cur prev words cword commands command
        _init_completion || return

        commands="__COMMAND_LIST__"

        # Handle command completion
        if [ $cword -eq 1 ]; then
            COMPREPLY=( $(compgen -W "${commands}" -- "$cur") )
            return 0
        fi
    """.join("""
        # Get the current command
        command="${words[1]}"

        case "$command" in
    """)

        # Replace placeholder with actual command list (already sorted from discover_commands)
        command_list = " ".join(commands.keys())
        script = script.replace("__COMMAND_LIST__", command_list)

        # Add case statements for each command (already sorted from discover_commands)
        for cmd_name, cmd_info in commands.items():
            script += f"        {cmd_name})\n"
            script += '            case "$prev" in\n'

            # Sort and add completion for arguments that have choices
            sorted_args = sorted(cmd_info["arguments"].items(), key=lambda x: x[0])
            for arg_name, arg_info in sorted_args:
                if arg_info["choices"]:
                    flags_str = "|".join(
                        sorted(f.lstrip("-") for f in arg_info["flags"])
                    )
                    choices_str = " ".join(str(c) for c in sorted(arg_info["choices"]))
                    script += f"                {flags_str})\n"
                    script += f'                    COMPREPLY=( $(compgen -W "{choices_str}" -- "$cur") )\n'
                    script += "                    return 0\n"
                    script += "                    ;;\n"

            script += "                *)\n"
            # Add all flags as completion options (sorted)
            all_flags = []
            for arg_info in cmd_info["arguments"].values():
                all_flags.extend(arg_info["flags"])
            flags_str = " ".join(sorted(all_flags))
            script += f'                    COMPREPLY=( $(compgen -W "{flags_str}" -- "$cur") )\n'
            script += "                    return 0\n"
            script += "                    ;;\n"
            script += "            esac\n"
            script += "            ;;\n"

        script += """        *)
                ;;
        esac
    }

    # Register the completion function
    complete -F _django_completion django-admin
    complete -F _django_completion manage.py
    complete -F _django_completion dj

    # Create dj alias if it doesn't exist
    if _is_django_project_path; then
        alias dj='python manage.py'
    fi
    """

        return script
