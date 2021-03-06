# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
import logging
import threading
import time

import bpy
import requests

from . import oauth, paths
from .config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_PROFILE
from .report_tools import execute_wrapper
from .src.async_loop import run_async_function
from .src.preferences.preferences import Preferences
from .src.preferences.profile import Profile
from .src.ui import colors
from .src.ui.main import UI
from .tasks_queue import add_task

AUTH_URL = paths.get_auth_url()
PLATFORM_URL = paths.get_platform_url()
REDIRECT_URL = paths.get_auth_landing_url()
CLIENT_ID = paths.get_auth_client_id()
AUDIENCE = paths.get_auth_audience()
PORTS = [62485, 65425, 55428, 49452]

active_authenticator = None


def login(authenticator: oauth.OAuthAuthenticator):
    oauth_response = authenticator.get_new_token(redirect_url=REDIRECT_URL)
    logging.debug('tokens retrieved')
    add_task(write_tokens, args=(oauth_response,))


def refresh_token(immediate: bool = False) -> dict:
    """Refresh OAuth token.

    Parameters:
        immediate: True if the subsequent operations should be done in the same thread sequentially
    """
    preferences = Preferences().get()
    ui = UI()
    if preferences.refresh_in_progress:
        ui.add_report('Already Refreshing token, will be ready soon.')
        return
    preferences.refresh_in_progress = True
    authenticator = oauth.OAuthAuthenticator(
        auth0_url=AUTH_URL,
        platform_url=PLATFORM_URL,
        client_id=CLIENT_ID,
        ports=PORTS,
        audience=AUDIENCE,
    )
    oauth_response = authenticator.get_refreshed_token(preferences.api_key_refresh)
    if oauth_response['access_token'] is not None and oauth_response['refresh_token'] is not None:
        write_tokens(oauth_response)
    else:
        ui.add_report('Auto-Login failed, please login manually', color=colors.RED)
        reset_tokens()
    return oauth_response


def write_tokens(oauth_response: dict):
    logging.debug('writing tokens')
    logging.debug(oauth_response)

    preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
    preferences.api_key_refresh = oauth_response['refresh_token']
    preferences.api_key = oauth_response['access_token']
    preferences.api_key_timeout = time.time() + oauth_response['expires_in']
    preferences.api_key_life = oauth_response['expires_in']
    preferences.id_token = oauth_response['id_token']
    preferences.login_attempt = False
    preferences.refresh_in_progress = False
    ui = UI()
    ui.add_report(text=f'{HANA3D_DESCRIPTION} Re-Login success')
    profile = Profile()
    run_async_function(profile.update_async)


def reset_tokens():
    preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
    preferences.api_key_refresh = ''
    preferences.api_key = ''
    preferences.api_key_timeout = 0
    preferences.api_key_life = 3600
    preferences.id_token = ''
    preferences.login_attempt = False
    preferences.refresh_in_progress = False
    if HANA3D_PROFILE in bpy.context.window_manager.keys():
        del bpy.context.window_manager[HANA3D_PROFILE]


class RegisterLoginOnline(bpy.types.Operator):
    """Login online on hana3d webpage"""

    bl_idname = f"wm.{HANA3D_NAME}_login"
    bl_label = f"{HANA3D_DESCRIPTION} login or signup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    @execute_wrapper
    def execute(self, context):
        preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        preferences.login_attempt = True
        self.start_login_thread()
        return {'FINISHED'}

    @staticmethod
    def start_login_thread():
        global active_authenticator
        authenticator = oauth.OAuthAuthenticator(
            auth0_url=AUTH_URL,
            platform_url=PLATFORM_URL,
            client_id=CLIENT_ID,
            ports=PORTS,
            audience=AUDIENCE,
        )
        # we store authenticator globally to be able to ping the server if connection fails.
        active_authenticator = authenticator
        thread = threading.Thread(target=login, args=([authenticator]), daemon=True)
        thread.start()


class Logout(bpy.types.Operator):
    """Logout from hana3d immediately"""

    bl_idname = f"wm.{HANA3D_NAME}_logout"
    bl_label = f"{HANA3D_DESCRIPTION} logout"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    @execute_wrapper
    def execute(self, context):
        reset_tokens()
        return {'FINISHED'}


class CancelLoginOnline(bpy.types.Operator):
    """Cancel login attempt."""

    bl_idname = f"wm.{HANA3D_NAME}_login_cancel"
    bl_label = f"{HANA3D_DESCRIPTION} login cancel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    @execute_wrapper
    def execute(self, context):
        global active_authenticator
        preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        preferences.login_attempt = False
        try:
            if active_authenticator is not None:
                requests.get(active_authenticator.redirect_uri)
                active_authenticator = None
        except Exception as e:
            logging.error('stopped login attempt')
            logging.error(e)
        return {'FINISHED'}


classes = (
    RegisterLoginOnline,
    CancelLoginOnline,
    Logout,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
