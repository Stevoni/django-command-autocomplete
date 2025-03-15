import os
from typing import Dict

from django_command_autocomplete.generators.base import BaseGenerator


class PowershellGenerator(BaseGenerator):
    def get_default_output_path(self) -> str:
        return "django_completion.ps1"

    @staticmethod
    def get_command_flag() -> str:
        return "powershell"

    def generate_output(self, commands: Dict[str, Dict], **kwargs) -> str:
        return self.generate_powershell_completion(commands, **kwargs)

    def generate_powershell_completion(self, commands, project_path) -> str:
        """
        Generate PowerShell script for command completion.

        Returns:
            String containing the PowerShell completion script
        """
        project_path = os.path.abspath(project_path)

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

    def generate_powershell_folder_tracking(self) -> str:
        """
        Generate PowerShell script for folder tracking.

        Returns:
            String containing the PowerShell folder tracking script
        """

        script = """
    # Get all existing aliases for Set-Location before overriding
    $existingAliases = Get-Alias | Where-Object { $_.Definition -eq "Set-Location" } | ForEach-Object { $_.Name }

    # Store the original Set-Location command
    $original_SetLocation = (Get-Item function:Set-Location).ScriptBlock

    # Create a function to run when directory changes
    function Invoke-OnDirectoryChange {
        param($newPath)

        # TODO: Add processing here
    }

    # Override the Set-Location command
    function Set-Location {
        param(
            [Parameter(Position=0, ValueFromPipeline=$true)]
            [string] $Path,

            [Parameter(ValueFromPipelineByPropertyName=$true)]
            [string] $LiteralPath,

            [switch] $PassThru
        )

        # Call the original Set-Location function
        if ($LiteralPath) {
            & $original_SetLocation -LiteralPath $LiteralPath -PassThru:$PassThru
        } else {
            & $original_SetLocation $Path -PassThru:$PassThru
        }

        # After changing directory, call our custom function
        Invoke-OnDirectoryChange (Get-Location).Path
    }

    # Re-apply all original aliases to point to our new Set-Location
    foreach ($alias in $existingAliases) {
        Set-Alias -Name $alias -Value Set-Location -Option AllScope -Force
        Write-Host "Preserved alias: $alias -> Set-Location"
    }

    # Run once for the current directory
    Invoke-OnDirectoryChange (Get-Location).Path
    """
        return script
