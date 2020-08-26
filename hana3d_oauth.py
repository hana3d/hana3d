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

if 'bpy' in locals():
    from importlib import reload

    colors = reload(colors)
    oauth = reload(oauth)
    paths = reload(paths)
    search = reload(search)
    tasks_queue = reload(tasks_queue)
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import colors, oauth, paths, search, tasks_queue, ui, utils

import threading
import time

import bpy
import requests

AUTH_URL = paths.get_auth_url()
PLATFORM_URL = paths.get_platform_url()
REDIRECT_URL = paths.get_auth_landing_url()
CLIENT_ID = paths.get_auth_client_id()
AUDIENCE = paths.get_auth_audience()
PORTS = [62485, 65425, 55428, 49452]

active_authenticator = None


def login_thread():
    global active_authenticator
    authenticator = oauth.SimpleOAuthAuthenticator(
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


def login(authenticator):
    auth_token, refresh_token, oauth_response = authenticator.get_new_token(
        redirect_url=REDIRECT_URL
    )
    utils.p('tokens retrieved')
    tasks_queue.add_task((write_tokens, (auth_token, refresh_token, oauth_response)))


def refresh_token_thread():
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    if len(preferences.api_key_refresh) > 0 and not preferences.refresh_in_progress:
        preferences.refresh_in_progress = True
        thread = threading.Thread(
            target=refresh_token,
            args=([preferences.api_key_refresh]),
            daemon=True
        )
        thread.start()
    else:
        ui.add_report('Already Refreshing token, will be ready soon.')


def refresh_token(api_key_refresh):
    authenticator = oauth.SimpleOAuthAuthenticator(
        auth0_url=AUTH_URL,
        platform_url=PLATFORM_URL,
        client_id=CLIENT_ID,
        ports=PORTS,
        audience=AUDIENCE,
    )
    auth_token, refresh_token, oauth_response = authenticator.get_refreshed_token(api_key_refresh)
    if auth_token is not None and refresh_token is not None:
        tasks_queue.add_task((write_tokens, (auth_token, refresh_token, oauth_response)))
    else:
        tasks_queue.add_task((fail_refresh, ()))
    return auth_token, refresh_token, oauth_response


def write_tokens(auth_token, refresh_token, oauth_response):
    utils.p('writing tokens')
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    preferences.api_key_refresh = refresh_token
    preferences.api_key = auth_token
    preferences.api_key_timeout = time.time() + oauth_response['expires_in']
    preferences.api_key_life = oauth_response['expires_in']
    preferences.login_attempt = False
    preferences.refresh_in_progress = False
    props = utils.get_search_props()
    if props is not None:
        props.report = ''
    ui.add_report('Hana3D Re-Login success')
    search.get_profile()


def fail_refresh():
    ui.add_report('Auto-Login failed, please login manually', color=colors.RED)
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    preferences.api_key_refresh = ''
    preferences.api_key = ''
    preferences.api_key_timeout = 0
    preferences.api_key_life = 3600
    preferences.login_attempt = False
    preferences.refresh_in_progress = False
    if 'hana3d profile' in bpy.context.window_manager.keys():
        del bpy.context.window_manager['hana3d profile']


class RegisterLoginOnline(bpy.types.Operator):
    """Login online on hana3d webpage"""

    bl_idname = "wm.hana3d_login"
    bl_label = "hana3d login or signup"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        preferences.login_attempt = True
        login_thread()
        return {'FINISHED'}


class Logout(bpy.types.Operator):
    """Logout from hana3d immediately"""

    bl_idname = "wm.hana3d_logout"
    bl_label = "hana3d logout"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        preferences.api_key_refresh = ''
        preferences.api_key = ''
        preferences.api_key_timeout = 0
        preferences.api_key_life = 3600
        preferences.login_attempt = False
        preferences.refresh_in_progress = False
        if 'hana3d profile' in bpy.context.window_manager.keys():
            del bpy.context.window_manager['hana3d profile']
        return {'FINISHED'}


class CancelLoginOnline(bpy.types.Operator):
    """Cancel login attempt."""

    bl_idname = "wm.hana3d_login_cancel"
    bl_label = "hana3d login cancel"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        global active_authenticator
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        preferences.login_attempt = False
        try:
            if active_authenticator is not None:
                requests.get(active_authenticator.redirect_uri)
                active_authenticator = None
        except Exception as e:
            print('stopped login attempt')
            print(e)
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
