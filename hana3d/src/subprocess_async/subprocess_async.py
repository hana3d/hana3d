"""Hana3D subprocess async."""

import asyncio
import functools
import logging
import subprocess  # noqa: S404
from typing import List


class Subprocess(object):  # noqa : WPS214
    """Hana3D subprocess async."""

    def __init__(self):
        """Create a Subprocess object."""

    async def subprocess(self, cmd: List[str]) -> subprocess.CompletedProcess:    # noqa : WPS210
        """Run a command in a non-blocking subprocess.

        Parameters:
            cmd: command to be executed.

        Returns:
            subprocess.CompletedProcess: the return value representing a process that has finished.

        Raises:
            Exception: Subprocess exited in error
        """
        loop = asyncio.get_event_loop()
        partial = functools.partial(subprocess.run, cmd, capture_output=True)
        output = await loop.run_in_executor(None, partial)

        if output.returncode != 0:
            error_msg = output.stderr
            raise Exception(f'Subprocess raised error:\n{error_msg}')

        logging.debug(f'Subprocess {cmd}: {output.stdout}')
        return output
