from flask import Flask
from flask_mail import Mail
from pymongo import MongoClient
from os import environ
from euv_spectra_app.config import Config
import gridfs


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = environ.get('SECRET_KEY')
mail = Mail(app)
app.jinja_env.filters['zip'] = zip

# ======= DB Setup ==========
uri = environ.get('MONGODB_URI')
client = MongoClient(uri)
my_db = environ.get('MONGODB_DATABASE')
db = client.get_database(my_db)
grid_fs = gridfs.GridFS(db)
# ===========================

# ======= Collections ==========
model_parameter_grid = db.model_parameter_grid
starter_photosphere_models = db.starter_photosphere_models
photosphere_models = db.photosphere_models
fits_files = db.fits_files
mast_galex_times = db.mast_galex_times
m0_grid = db.m0_grid
m1_grid = db.m1_grid
m2_grid = db.m2_grid
m3_grid = db.m3_grid
m4_grid = db.m4_grid
m5_grid = db.m5_grid
m6_grid = db.m6_grid
m7_grid = db.m7_grid
m8_grid = db.m8_grid