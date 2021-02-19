"""Upload validation module."""
from enum import Enum
from typing import Callable, Tuple


class Category(str, Enum):  # noqa : WPS600
    """Category enum class (WARNING | ERROR)."""
    warning = 'WARNING'
    error = 'ERROR'


def dummy_fix_function():
    """Fix validation error.

    Does nothing.
    """
    pass  # noqa: WPS420


def dummy_validation_function() -> Tuple[bool, str]:
    """Check if validator passes test.

    Returns:
        is_valid, message: whether check passed and a report message
    """
    return True, 'All ok!'


class BaseValidator(object):
    """Base validator class."""

    name: str
    category: Category
    description: str
    validation_result: Tuple[bool, str]
    validation_function: Callable[..., Tuple[bool, str]]
    fix_function: Callable

    def __init__(  # noqa: WPS211
        self,
        name: str,
        category: Category,
        description: str,
        validation_function: Callable = dummy_validation_function,
        fix_function: Callable = dummy_fix_function,
    ):
        """Check if validator passes test.

        Parameters:
            name: validation name
            category: one of 'WARNING' or 'ERROR'
            description: short description of what is begin checked
            validation_function: function that checks for issues - returns a boolean and a message
            fix_function: function that automatically corrects issues

        Returns:
            BaseValidator instance
        """
        self.name = name
        self.category = category
        self.description = description
        self.validation_function = validation_function  # type: ignore
        self.fix_function = fix_function  # type: ignore
        self.validation_result = (False, 'Validation has yet to be run')


    def get_validation_result(self) -> Tuple[bool, str]:
        """Get validation result.

        Returns:
            is_valid, message: whether check passed and a report message
        """
        return self.validation_result


    def run_validation(self):
        """Run checks for this validator."""
        self.validation_result = self.validation_function()


    def run_fix(self):
        """Run fix function for this validator."""
        self.fix_function()
        self.run_validation()
        assert self.validation_result[0], 'Could not fix the problem automatically'


    def ignore(self):
        """Ignore validator result."""
        self.validation_result = (True, 'Ignored')
