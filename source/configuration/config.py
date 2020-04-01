import os

# General
PAGE_SIZE = 20

def ENV_VARIABLE(key):
    if key not in os.environ:
        #fallback for local
        from ..secrets.secrets import secrets_dict
        return secrets_dict[key]
    return os.environ[key]

def ENV_NAME():
    if 'environment_type' not in os.environ:
        return ''

    return os.environ['environment_type']

def IS_PROD_ENV():
    if 'environment_type' not in os.environ:
        return False

    return os.environ['environment_type'] != ''

LOCAL_DB = 'mysql+pymysql://root:COVID1234@localhost:3306/dbCOVID'
EB_PROD_DB = ENV_VARIABLE('EB_PROD_DB')
EB_DEV_DB = ENV_VARIABLE('EB_DEV_DB')

def DB_URL():
    if 'environment_type' not in os.environ:
        return LOCAL_DB

    ENVIRO_NAME = os.environ['environment_type']
    if ENVIRO_NAME == '':
        return LOCAL_DB
    elif ENVIRO_NAME == 'prod':
        return EB_PROD_DB
    elif ENVIRO_NAME == 'dev':
        return EB_DEV_DB

S3_BUCKET = 'covid-dc-images'
S3_KEY = ENV_VARIABLE('S3_KEY')
S3_SECRET = ENV_VARIABLE('S3_SECRET')
S3_LOCATION = 'https://{}.s3.us-east-2.amazonaws.com/'.format(S3_BUCKET)

def PASSWORD_SECRET_KEY():
    if IS_PROD_ENV():
        return ENV_VARIABLE('PASSWORD_SECRET_KEY')

    return 'adwadawdpom2130e-?cqw'

PASSWORD_SECRET_KEY = PASSWORD_SECRET_KEY()
