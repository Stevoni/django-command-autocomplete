from unittest import TestCase
from unittest.mock import patch, MagicMock
import os
from django.core.management import BaseCommand
from django_command_autocomplete.command_discovery import discover_commands
from django_command_autocomplete.generators.base import BaseGenerator
from django_command_autocomplete.generators.powershell import PowershellGenerator
from django_command_autocomplete.generators.bash import BashGenerator


class MockCommand(BaseCommand):
    help = "Test command help"

    def add_arguments(self, parser):
        parser.add_argument("--test", help="Test argument")
        parser.add_argument("--choice", choices=["a", "b"], help="Choice argument")
        parser.add_argument("positional", help="Positional argument")


class TestCommandDiscovery(TestCase):
    @patch("django_command_autocomplete.command_discovery.get_commands")
    @patch("django_command_autocomplete.command_discovery.load_command_class")
    def test_discover_commands(self, mock_load_command, mock_get_commands):
        # Mock Django's command discovery
        mock_get_commands.return_value = {"testcmd": "testapp"}
        mock_load_command.return_value = MockCommand()

        # Run command discovery
        commands = discover_commands()

        # Verify command was discovered
        self.assertIn("testcmd", commands)
        cmd_info = commands["testcmd"]

        # Verify command metadata
        self.assertEqual(cmd_info["help"], "Test command help")
        self.assertEqual(cmd_info["app"], "testapp")

        # Verify arguments were discovered
        self.assertIn("test", cmd_info["arguments"])
        self.assertIn("choice", cmd_info["arguments"])
        self.assertIn("positional", cmd_info["arguments"])

        # Verify argument details
        choice_arg = cmd_info["arguments"]["choice"]
        self.assertEqual(choice_arg["choices"], ["a", "b"])
        self.assertEqual(choice_arg["help"], "Choice argument")

    @patch("django_command_autocomplete.command_discovery.get_commands")
    @patch("django_command_autocomplete.command_discovery.load_command_class")
    def test_discover_commands_error_handling(
        self, mock_load_command, mock_get_commands
    ):
        # Mock Django's command discovery with a failing command
        mock_get_commands.return_value = {"goodcmd": "testapp", "badcmd": "testapp"}

        def mock_load(app, cmd):
            if cmd == "badcmd":
                raise ImportError("Failed to load command")
            return MockCommand()

        mock_load_command.side_effect = mock_load

        # Run command discovery
        commands = discover_commands()

        # Verify good command was discovered and bad command was skipped
        self.assertIn("goodcmd", commands)
        self.assertNotIn("badcmd", commands)


class TestManagementCommand(TestCase):
    def setUp(self):
        # Mock command discovery
        self.mock_commands = {
            "testcmd": {
                "help": "Test command help",
                "app": "testapp",
                "arguments": {
                    "test": {
                        "flags": ["--test"],
                        "help": "Test argument",
                        "required": False,
                        "choices": None,
                    }
                },
            }
        }
        self.patcher = patch(
            "django_command_autocomplete.command_discovery.discover_commands"
        )
        self.mock_discover = self.patcher.start()
        self.mock_discover.return_value = self.mock_commands

    def tearDown(self):
        self.patcher.stop()

    @patch("builtins.open", create=True)
    def test_command_execution(self, mock_open):
        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Import here to avoid early Django app loading
        from django_command_autocomplete.management.commands.generate_shell_completion import (
            Command,
        )

        # Create command instance
        command = Command()

        # Test PowerShell generation
        command.handle(shell="powershell", output="test.ps1")
        mock_file.write.assert_called()
        script = mock_file.write.call_args[0][0]
        self.assertIn("testcmd", script)
        self.assertIn("--test", script)

        # Test Bash generation
        mock_file.reset_mock()
        command.handle(shell="bash", output="test.sh")
        mock_file.write.assert_called()
        script = mock_file.write.call_args[0][0]
        self.assertIn("testcmd", script)
        self.assertIn("--test", script)

    def test_command_validation(self):
        from django_command_autocomplete.management.commands.generate_shell_completion import (
            Command,
        )

        command = Command()

        # Test invalid shell type
        with self.assertRaises(ValueError):
            command.handle(shell="invalid", output="test.sh")

    @patch("builtins.open", create=True)
    def test_output_file_handling(self, mock_open):
        from django_command_autocomplete.management.commands.generate_shell_completion import (
            Command,
        )

        command = Command()

        # Test default output paths
        command.handle(shell="powershell", output=None)
        mock_open.assert_called_with("django_completion.ps1", "w")

        mock_open.reset_mock()
        command.handle(shell="bash", output=None)
        mock_open.assert_called_with("django_completion.sh", "w")

        # Test custom output path
        mock_open.reset_mock()
        custom_path = os.path.join("custom", "path", "completion.ps1")
        command.handle(shell="powershell", output=custom_path)
        mock_open.assert_called_with(custom_path, "w")


class TestGenerators(TestCase):
    def setUp(self):
        self.project_path = "/test/project/path"
        self.commands = {
            "testcmd": {
                "help": "Test command help",
                "app": "testapp",
                "arguments": {
                    "test": {
                        "flags": ["--test"],
                        "help": "Test argument",
                        "required": False,
                        "choices": None,
                    },
                    "choice": {
                        "flags": ["--choice"],
                        "help": "Choice argument",
                        "required": False,
                        "choices": ["a", "b"],
                    },
                },
            }
        }

    def test_base_generator(self):
        # Test abstract methods
        with self.assertRaises(NotImplementedError):
            BaseGenerator.get_command_flag()

        generator = BaseGenerator()
        with self.assertRaises(NotImplementedError):
            generator.generate_output(commands=None)

        with self.assertRaises(NotImplementedError):
            generator.get_default_output_path()

        # Test generator discovery
        self.assertIn("powershell", BaseGenerator.get_all_command_flags())
        self.assertIn("bash", BaseGenerator.get_all_command_flags())

        # Test generator retrieval
        self.assertIsInstance(
            BaseGenerator.get_generator_by_flag("powershell"), PowershellGenerator
        )
        self.assertIsInstance(
            BaseGenerator.get_generator_by_flag("bash"), BashGenerator
        )
        self.assertIsNone(BaseGenerator.get_generator_by_flag("invalid"))

    @patch("os.path.abspath")
    def test_powershell_generator(self, mock_abspath):
        mock_abspath.return_value = self.project_path
        generator = PowershellGenerator()
        script = generator.generate_powershell_completion(
            self.commands, self.project_path
        )

        # Test PowerShell script content
        self.assertIn(self.project_path, script)
        self.assertIn("testcmd", script)
        self.assertIn("--test", script)
        self.assertIn("--choice", script)
        self.assertIn("'choices' = @('a', 'b')", script)
        self.assertIn("Test-DjangoProjectPath", script)
        self.assertIn("Find-ManagePy", script)

    @patch("os.path.abspath")
    def test_bash_generator(self, mock_abspath):
        mock_abspath.return_value = self.project_path
        generator = BashGenerator()
        script = generator.generate_bash_completion(self.commands, self.project_path)

        # Test Bash script content
        self.assertIn(self.project_path, script)
        self.assertIn("testcmd", script)
        self.assertIn("--test", script)
        self.assertIn("--choice", script)
        self.assertIn("_is_django_project_path", script)
        self.assertIn("complete -F _django_completion", script)

    def test_project_path_validation(self):
        generator = PowershellGenerator()
        script = generator.generate_powershell_completion(
            self.commands, self.project_path
        )

        # Test project path validation in PowerShell
        self.assertIn("Test-DjangoProjectPath", script)
        self.assertIn("$currentPath.StartsWith($projectPath)", script)

        generator = BashGenerator()
        script = generator.generate_bash_completion(self.commands, self.project_path)

        # Test project path validation in Bash
        self.assertIn("_is_django_project_path", script)
        self.assertIn('case "$current_path" in', script)

    def test_powershell_folder_tracking(self):
        generator = PowershellGenerator()
        script = generator.generate_powershell_folder_tracking()

        # Test folder tracking script content
        self.assertIn("Set-Location", script)
        self.assertIn("Invoke-OnDirectoryChange", script)
        self.assertIn("$original_SetLocation", script)
        self.assertIn("Get-Alias", script)

        # Test alias preservation
        self.assertIn("foreach ($alias in $existingAliases)", script)
        self.assertIn("Set-Alias -Name $alias -Value Set-Location", script)

        # Test directory change handling
        self.assertIn("function Invoke-OnDirectoryChange", script)
        self.assertIn("param($newPath)", script)

        # Test initial directory check
        self.assertIn("Invoke-OnDirectoryChange (Get-Location).Path", script)

    def test_help_text_version(self):
        from django_command_autocomplete import __version__

        # Test PowerShell help text
        generator = PowershellGenerator()
        help_text = generator.generate_helptext("test.ps1")
        self.assertIn(
            f"Generated by django-command-autocomplete v{__version__}", help_text
        )

        # Test Bash help text
        generator = BashGenerator()
        help_text = generator.generate_helptext("test.sh")
        self.assertIn(
            f"Generated by django-command-autocomplete v{__version__}", help_text
        )
