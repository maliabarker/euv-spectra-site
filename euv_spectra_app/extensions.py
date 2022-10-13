# for database migrations

from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from flask_migrate import Migrate
from pymongo import MongoClient
from os import environ
from euv_spectra_app.config import Config

app = Flask(__name__)
app.config.from_object(Config)

# ======= DB Setup ==========
uri = environ.get('MONGODB_URI')
client = MongoClient(uri)
my_db = environ.get('MONGODB_DATABASE')
db = client.get_database(my_db)
# ===========================

# ======= Collections ==========
# events = db.events
# descriptions = db.descriptions
# 
# =========================

# db=SQLAlchemy(app)
# migrate = Migrate(app, db)
