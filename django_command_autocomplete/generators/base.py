import abc
from typing import List, TypeVar, Dict

T = TypeVar("T", bound="BaseGenerator")


class BaseGenerator:
    @staticmethod
    @abc.abstractmethod
    def get_command_flag() -> str:
        """
        Get the flag for the command line
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def generate_output(self, commands: Dict[str, Dict], **kwargs) -> str:
        """
        Generate the output for the shell
        """
        raise NotImplementedError()

    def generate_helptext(self, output_file: str, **kwargs) -> str:
        """
        Returns the help text for the command
        """
        internal_output_file: str = output_file or self.get_default_output_path()
        internal_command_example: str = kwargs.pop(
            "command_example",
            ". .\\{}" if self.get_command_flag() == "powershell" else "source ./{}",
        )

        return (
            f"{self.get_command_flag().title()} completion script generated at {internal_output_file}\n"
            "To use it, run the following command:\n"
            f"{internal_command_example.format(internal_output_file)}"
        )

    @abc.abstractmethod
    def get_default_output_path(self) -> str:
        """
        Get the default output path for the shell
        """
        raise NotImplementedError()

    @classmethod
    def derived(cls):
        """
        Returns all derived classes
        """
        return [c for c in cls.__subclasses__()]

    @classmethod
    def get_all_command_flags(cls) -> List[str]:
        """
        Returns all derived command flags
        """
        return [c.get_command_flag() for c in cls.__subclasses__()]

    @classmethod
    def get_generator_by_flag(cls, flag: str) -> T:
        """
        Returns the generator for the given flag
        Args:
            flag: The flag of the generator to find
        """
        for c in cls.derived():
            if flag in c.get_command_flag():
                return c()

        return None
