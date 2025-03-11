import os
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


def generate_bash_completion() -> str:
    """
    Generate Bash completion script.

    Returns:
        String containing the Bash completion script
    """
    commands = discover_commands()
    project_path = os.path.abspath(os.getcwd())

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
                flags_str = "|".join(sorted(f.lstrip("-") for f in arg_info["flags"]))
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
        script += (
            f'                    COMPREPLY=( $(compgen -W "{flags_str}" -- "$cur") )\n'
        )
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


def generate_powershell_completion() -> str:
    """
    Generate PowerShell script for command completion.

    Returns:
        String containing the PowerShell completion script
    """
    commands = discover_commands()
    project_path = os.path.abspath(os.getcwd())

    script = f"""
# Django Command Completion for PowerShell
# Generated for project: {project_path}

# Store project path and command information in global variables
$Global:DjangoProjectPath = '{project_path}'
$Global:DjangoCommandInfo = @{{
"""

    # Add commands and their arguments to the global variable (already sorted from discover_commands)
    for cmd_name, cmd_info in commands.items():
        script += f"    '{cmd_name}' = @{{\n"
        help_text = cmd_info["help"].replace("'", "''") if cmd_info["help"] else ""
        script += f"        'help' = '{help_text}'\n"
        script += "        'arguments' = @{\n"

        # Sort arguments alphabetically
        sorted_args = sorted(cmd_info["arguments"].items(), key=lambda x: x[0])
        for arg_name, arg_info in sorted_args:
            flags = "', '".join(sorted(arg_info["flags"]))
            script += f"            '{arg_name}' = @{{\n"
            script += f"                'flags' = @('{flags}')\n"
            if arg_info["choices"]:
                choices = "', '".join(str(c) for c in sorted(arg_info["choices"]))
                script += f"                'choices' = @('{choices}')\n"
            script += "            }\n"

        script += "        }\n"
        script += "    }\n"

    script += """
}

# Function to check if we're in the Django project directory
function Test-DjangoProjectPath {
    $currentPath = (Get-Location).Path
    $projectPath = $Global:DjangoProjectPath
    
    # Check if we're in the project path or a subdirectory
    return $currentPath.StartsWith($projectPath)
}

# Function to find manage.py
function Find-ManagePy {
    [CmdletBinding()]
    param()
    
    # Only search when in project directory
    if (-not (Test-DjangoProjectPath)) {
        return $null
    }
    
    # Check in current directory
    if (Test-Path "manage.py") {
        return (Resolve-Path "manage.py").Path
    }
    # Check in src directory
    elseif (Test-Path "src/manage.py") {
        return (Resolve-Path "src/manage.py").Path
    }
    # Search for manage.py in immediate child directories
    else {
        $managePyPaths = Get-ChildItem -Path "." -Filter "manage.py" -Recurse -Depth 2
        if ($managePyPaths.Count -gt 0) {
            return $managePyPaths[0].FullName
        }
    }
    return $null
}

# Find and store manage.py path
$Global:DjangoManagePyPath = Find-ManagePy

# Create the dj function
function global:dj {
    param([Parameter(ValueFromRemainingArguments=$true)]$args)
    
    # Only run when in project directory
    if (-not (Test-DjangoProjectPath)) {
        # Pass through to regular python manage.py if not in project directory
        python manage.py $args
        return
    }
    
    # Verify the path exists
    if (-not (Test-Path $Global:DjangoManagePyPath)) {
        # Fall back to regular python manage.py if manage.py not found
        python manage.py $args
        return
    }
    
    $managePyDir = Split-Path -Parent $Global:DjangoManagePyPath
    if ($managePyDir) { Push-Location $managePyDir }
    try {
        python $Global:DjangoManagePyPath $args
    }
    finally {
        if ($managePyDir) { Pop-Location }
    }
}

# Register the argument completer
Register-ArgumentCompleter -CommandName dj -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    
    # Only provide completions when in the correct project directory
    if (-not (Test-DjangoProjectPath)) {
        return
    }
    
    # If we're completing the command itself
    if ($commandAst.CommandElements.Count -le 1 -or 
        ($commandAst.CommandElements.Count -eq 2 -and $commandAst.CommandElements[1].Extent.Text -eq $wordToComplete)) {
        
        return $Global:DjangoCommandInfo.Keys | Sort-Object | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new(
                $_,
                $_,
                'ParameterValue',
                "$_ - $($Global:DjangoCommandInfo[$_].help)"
            )
        }
    }
    
    # If we're completing a subcommand
    elseif ($commandAst.CommandElements.Count -ge 2) {
        $cmd = $commandAst.CommandElements[1].Extent.Text
        
        if ($Global:DjangoCommandInfo.ContainsKey($cmd)) {
            $cmdInfo = $Global:DjangoCommandInfo[$cmd]
            
            # Check if the word starts with "--" or "-", then suggest option arguments
            if ($wordToComplete.StartsWith("--") -or $wordToComplete.StartsWith("-")) {
                $optionToComplete = $wordToComplete.TrimStart('-')
                
                return $cmdInfo.arguments.Keys | Sort-Object | ForEach-Object {
                    $argInfo = $cmdInfo.arguments[$_]
                    foreach ($flag in ($argInfo.flags | Sort-Object)) {
                        if ($flag.TrimStart('-') -like "$optionToComplete*") {
                            [System.Management.Automation.CompletionResult]::new(
                                $flag,
                                $flag,
                                'ParameterValue',
                                $argInfo.help
                            )
                        }
                    }
                }
            }
            # If the previous word was an argument that has choices, complete those
            elseif ($commandAst.CommandElements.Count -gt 2) {
                $prevArg = $commandAst.CommandElements[-2].Extent.Text
                foreach ($argInfo in ($cmdInfo.arguments.Values | Sort-Object -Property {$_.flags[0]})) {
                    if ($prevArg -in $argInfo.flags -and $argInfo.choices) {
                        return $argInfo.choices | Sort-Object | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                            [System.Management.Automation.CompletionResult]::new(
                                $_,
                                $_,
                                'ParameterValue',
                                "Choice for $prevArg"
                            )
                        }
                    }
                }
            }
        }
    }
}

# Create the dj alias only if in project directory
if (Test-DjangoProjectPath) {
    Set-Alias -Name dj -Value "python manage.py" -ErrorAction SilentlyContinue
    Write-Host "Django command completion registered for project: $Global:DjangoProjectPath" -ForegroundColor Green
    Write-Host "Use 'dj <command>' to run commands when in the project directory." -ForegroundColor Green
}
"""

    return script
