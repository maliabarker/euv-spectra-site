# initializing main and database

from flask import Flask
from euv_spectra_app.config import Config
from flask_session import Session
import os

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.urandom(24)

Session(app)

from euv_spectra_app.main.routes import main
app.register_blueprint(main)
