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
model_parameter_grid = db.model_parameter_grid
m0_grid = db.m0_grid
m1_grid = db.m1_grid
m2_grid = db.m2_grid
m3_grid = db.m3_grid
m4_grid = db.m4_grid
m5_grid = db.m5_grid
m6_grid = db.m6_grid
m7_grid = db.m7_grid
m8_grid = db.m8_grid
# =========================

# db=SQLAlchemy(app)
# migrate = Migrate(app, db)



# read_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M0_models.csv')
# read_model_parameter_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/model_parameter_grid.csv')
