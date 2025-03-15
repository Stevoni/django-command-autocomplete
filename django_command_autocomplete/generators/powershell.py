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
        # TODO: Merge project paths and allow multiple projects in a single file
        script = f"""
    # Django Command Completion for PowerShell
    # Generated for projects: {project_path}

    # Setting tab complete functionality:
	Set-PSReadlineKeyHandler -Key Tab -Function MenuComplete

    # Store project path and command information in global variables
    $Global:DjangoProjectPaths = @('{project_path}')
    $Global:DjangoCommandInfo = @{{
    """
        # TODO: Refactor to allow generator arguments to be provided in the same order regardless of the order of the generator?
        # TODO: Add the project as a higher key so that it can be used to determine the project path when completing commands
        # TODO: Deduplicate commands available in multiple projects?
        # Add commands and their arguments to the global variable (already sorted from discover_commands)
        for cmd_name, cmd_info in commands.items():
            script += f"    '{cmd_name}' = @{{\n"
            help_text = cmd_info["help"].replace("'", "''") if cmd_info["help"] else ""
            script += f"        'help' = '{help_text}'\n"
            script += "        'arguments' = @{\n"

            # Sort arguments alphabetically
            for arg_name, arg_info in cmd_info["arguments"].items():
                help_text = (
                    arg_info["help"].replace("'", "''") if arg_info["help"] else ""
                )
                flags = "', '".join(sorted(arg_info["flags"]))
                script += f"            '{arg_name}' = @{{\n"
                script += f"                'flags' = @('{flags}')\n"
                script += f"                'help' = '{help_text}'\n"
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
        return Get-CurrentDjangoProjectPath -eq $null
    }

    # Function to get the current project path
    function Get-CurrentDjangoProjectPath {
        $currentPath = (Get-Location).Path

        # Find which project path we're in
        foreach ($projectPath in $Global:DjangoProjectPaths) {
            if ($currentPath.StartsWith($projectPath)) {
                return $projectPath
            }
        }
        return $null
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

    # Register the argument completer
    Register-ArgumentCompleter -CommandName @("dj","Invoke-DjangoManage") -ScriptBlock {
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

        # If we're completing arguments for a command
        elseif ($commandAst.CommandElements.Count -ge 2) {
            $cmd = $commandAst.CommandElements[1].Extent.Text
            if ($Global:DjangoCommandInfo.ContainsKey($cmd)) {
                $cmdInfo = $Global:DjangoCommandInfo[$cmd]
                # If word starts with -, --, or is empty, show available flags
                if ($wordToComplete.Length -eq 0 -or $wordToComplete.StartsWith("--") -or $wordToComplete.StartsWith("-")) {
                    $optionToComplete = $wordToComplete.TrimStart('-')
                    
					# Get all available flags and their help text
					return $cmdInfo.arguments.GetEnumerator() | 
						ForEach-Object { 
							$argInfo = $_.Value
							$help = if ($argInfo.help) { $argInfo.help } else { "No help available" }
							if ($argInfo.flags.Count -eq 1 -and $argInfo.flags[0] -eq '') {
								# Handle positional arguments (empty flags)
								[System.Management.Automation.CompletionResult]::new(
									$_.Key,
									$_.Key,
									'ParameterValue',
									$help
								)
							} else {
								# Handle flag arguments
								$argInfo.flags | ForEach-Object {
									[System.Management.Automation.CompletionResult]::new(
										$_,
										$_,
										'ParameterValue',
										$help
									)
								}
							}
						} |
						Where-Object { $_.CompletionText.TrimStart('-') -like "$optionToComplete*" }
                }
                # If previous word was a flag with choices, show available choices
                elseif ($commandAst.CommandElements.Count -gt 2) {
                    $prevArg = $commandAst.CommandElements[-2].Extent.Text
                    foreach ($argName in $cmdInfo.arguments.Keys) {
                        $argInfo = $cmdInfo.arguments[$argName]
                        if ($prevArg -in $argInfo.flags -and $argInfo.choices) {
                            return $argInfo.choices | Sort-Object | Where-Object { 
                                $_ -like "$wordToComplete*" 
                            } | ForEach-Object {
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
	# Create the Invoke-DjangoManage function that we'll alias with dj
    function Invoke-DjangoManage {
        param([Parameter(ValueFromRemainingArguments=$true)]$args)

		if (-not (Test-DjangoProjectPath)){
			Write-Host "Not in a generated directory: $Global:DjangoProjectPaths"
			return
		}
		# TODO: Automatically activate virtual environment
		python (Find-ManagePy) $args
    }

    # Create the dj alias for Invoke-DjangoManage
    Set-Alias -Name dj -Value Invoke-DjangoManage -ErrorAction SilentlyContinue
    Write-Host "Django command completion registered for projects: $Global:DjangoProjectPaths" -ForegroundColor Green
    Write-Host "Use 'dj <command>' to run commands when in the project directory." -ForegroundColor Green
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
