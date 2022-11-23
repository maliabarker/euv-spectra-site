# configuring environment variables

import os

from dotenv import load_dotenv

load_dotenv()

class Config(object):
    SECRET_KEY = os.getenv("SECRET_KEY")
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = os.getenv("MAIL_PORT")
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FAIL_SILENTLY = False