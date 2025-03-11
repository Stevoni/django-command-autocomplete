# Django Command Autocomplete

Shell tab completion for Django management commands. This package generates the autocomplete options for your project to be loaded by your profile.

## Features

- Automatic discovery of all Django management commands in your project
- Generates file to be loaded by your profile for the generated project directory


## WIP
- Make this readme more fancy
- Identify each project by checking the folder name or virtual environment and use specific commands
- Tab completion for command names and their arguments
- Support for argument choices when available
- Supports:
  - [x] PowerShell 
  - [ ] Bash (untested)
- Validate contributors setup
- Review and remove unnecessary requirements

## Installation

```bash
pip install django-command-autocomplete
```

## Usage

1. Add 'django_command_autocomplete' to your INSTALLED_APPS in settings.py:

```python
INSTALLED_APPS = [
    ...
    'django_command_autocomplete',
]
```

2. Generate the completion script for your shell:

For PowerShell:
```bash
python manage.py generate_shell_completion powershell
```

For Bash:
```bash
python manage.py generate_shell_completion bash
```

You can also specify a custom output path:
```bash
python manage.py generate_shell_completion powershell --output ~/.config/django-completion.ps1
python manage.py generate_shell_completion bash --output ~/.config/django-completion.sh
```

3. Set up automatic loading:

### PowerShell Setup

a. First, check if you have a PowerShell profile:
```powershell
Test-Path $PROFILE
```

b. If it returns False, create the profile:
```powershell
New-Item -Path $PROFILE -Type File -Force
```

c. Add the following line to your PowerShell profile:
```powershell
. $PSScriptRoot\django_completion.ps1
```

d. Reload your profile:
```powershell
. $PROFILE
```

### Bash Setup

a. Add the following line to your ~/.bashrc (or ~/.bash_profile on macOS):
```bash
source ~/path/to/django_completion.sh
```

b. Reload your bashrc:
```bash
source ~/.bashrc
```

Alternatively, you can manually source the script in each shell session:

PowerShell:
```powershell
. .\django_completion.ps1
```

Bash:
```bash
source ./django_completion.sh
```

Now you can use the `dj` command (alias for `python manage.py`) with tab completion:

```bash
dj [TAB]  # Shows all available commands
dj runserver --[TAB]  # Shows all available arguments for runserver
```

## How it Works

The package discovers all available Django management commands in your project and their arguments. It generates a shell script that provides tab completion through your shell's native completion mechanism.

The generated script:
- Creates an alias `dj` for `python manage.py`
- Registers a tab completion handler for the `dj` command
- Provides completion for:
  - Command names
  - Command arguments
  - Argument choices (when available)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Local Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Download source
3. Run `uv sync` 
4. Run `uv run pre-commit install`


## License

This project is licensed under the MIT License - see the LICENSE file for details.
