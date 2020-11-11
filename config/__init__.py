import os

dirname = os.path.dirname(os.path.realpath(__file__))
config_file = "config.yml"

with open(f'{dirname}/{config_file}') as f:
    lines = f.read().splitlines()

config = {}
for line in lines:
    key, value = line.split(': ')
    config[key] = value


HANA3D_NAME = config['HANA3D_NAME']
HANA3D_MODELS = config['HANA3D_MODELS']
HANA3D_SCENES = config['HANA3D_SCENES']
HANA3D_MATERIALS = config['HANA3D_MATERIALS']
HANA3D_PROFILE = config['HANA3D_PROFILE']
HANA3D_DESCRIPTION = config['HANA3D_DESCRIPTION']
HANA3D_AUTH_URL = config['HANA3D_AUTH_URL']
HANA3D_AUTH_CLIENT_ID = config['HANA3D_AUTH_CLIENT_ID']
HANA3D_AUTH_AUDIENCE = config['HANA3D_AUTH_AUDIENCE']
HANA3D_PLATFORM_URL = config['HANA3D_PLATFORM_URL']
HANA3D_AUTH_LANDING = config['HANA3D_AUTH_LANDING']
HANA3D_URL = config['HANA3D_URL']
