"""Hana3D Profile."""
import logging

import bpy

from ..requests_async.basic_request import BasicRequest
from ... import config, paths


class Profile(object):
    """Hana3D user profile."""

    def __init__(self) -> None:
        """Create a Profile object."""

    def get(self) -> dict:
        """Get User Profile object.

        Returns:
            dict: user_profile
        """
        return bpy.context.window_manager.get(config.HANA3D_PROFILE)

    async def update_async(self) -> None:
        """Update the User Profile asynchronously."""
        request = BasicRequest()
        logging.info('update_profile')  # noqa: WPS421
        url = paths.get_api_url('me')
        headers = request.get_headers(include_id_token=True)
        response = await request.get(url, headers=headers)

        if not response.ok:
            logging.error(f'Failed to get profile data: {response.text}')  # noqa: WPS421

        bpy.context.window_manager[config.HANA3D_PROFILE] = response.json()

        operator = getattr(bpy.ops.object, f'{config.HANA3D_NAME}_refresh_libraries')
        operator()
