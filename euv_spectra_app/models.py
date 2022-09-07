# database models (SQL)
from euv_spectra_app import db
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import enum

class FormEnum(enum.Enum):
    """Helper class to make it easier to use enums with forms."""
    @classmethod
    def choices(cls):
        return [(choice.name, choice) for choice in cls]

    def __str__(self):
        return str(self.value)

# ~TODO~
# model for models database

# QUESTIONS:
# what unit do we want to specifically store distance in?

class Star(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    # what do we put for model (ex: M0, M4, etc)
    model = db.Column(db.String(120), nullable=False)
    teff = db.Column(db.Integer, nullable=False)
    logg = db.Column(db.Integer, nullable=False)
    mass = db.Column(db.Integer, nullable=False)
    stell_rad = db.Column(db.Integer, nullable=False)
    dist = db.Column(db.Integer, nullable=False)
    fuv = db.Column(db.Integer, nullable=False)
    fuv_flag = db.Column(db.String(120))
    nuv = db.Column(db.Integer, nullable=False)
    nuv_flag = db.Column(db.String(120))

class ModelImport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(120), nullable=False)
    fits_filename = db.Column(db.String(240), nullable=False)
    teff = db.Column(db.Integer, nullable=False)
    logg = db.Column(db.Integer, nullable=False)    
    mass = db.Column(db.Integer, nullable=False)
    trgrad = db.Column(db.Integer, nullable=False)
    cmtop = db.Column(db.Integer, nullable=False)
    cmin = db.Column(db.Integer, nullable=False)
    euv = db.Column(db.Integer, nullable=False)
    fuv = db.Column(db.Integer, nullable=False)
    nuv = db.Column(db.Integer, nullable=False)
    j = db.Column(db.Integer, nullable=False)
