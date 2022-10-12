from cgitb import text
from typing import Optional
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DecimalField, validators, RadioField, widgets
from wtforms.validators import DataRequired, Length
from flask import Markup

teff_label = Markup('T<sub>eff</sub> (K)')
mass_label = Markup('Mass (M<sub>sun</sub>)')
rad_label = Markup('Radius (R<sub>sun</sub>)')

class StarForm(FlaskForm):
    teff = DecimalField('T𝘦𝘧𝘧 — Stellar Effective Temperature (K)', validators=[DataRequired()])
    logg = DecimalField('log(g) — Surface Gravity (cm/s²)', validators=[DataRequired()])
    mass = DecimalField('M ☉ - Mass (Solar Masses)', validators=[DataRequired()])
    stell_rad = DecimalField('R ☉ — Stellar Radius (Solar Radii)', validators=[DataRequired()])
    dist = DecimalField('d — Distance', validators=[DataRequired()])
    dist_unit = SelectField('d Unit', validators=[DataRequired()], choices=[('pc', 'Parsecs (pc)'), ('mas', 'Milliarcseconds (mas)')])
    fuv = DecimalField('FUV — Far Ultraviolet Spectra (μJy)', validators=[DataRequired()])
    fuv_flag = RadioField('FUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    nuv = DecimalField('NUV — Near Ultraviolet Spectra (μJy)', validators=[DataRequired()])
    nuv_flag = RadioField('NUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    submit = SubmitField('Submit and Find EUV Spectrum')

class StarNameForm(FlaskForm):
    star_name = StringField('Star Name', validators=[DataRequired()])
    submit = SubmitField('Search →')

class PositionForm(FlaskForm):
    # CHANGE THIS, NOT DECIMAL FIELD
    ra = DecimalField('RA — Right Ascension (h:m:s)', validators=[DataRequired()])
    dec = DecimalField('Dec — Declination (h:m:s)', validators=[DataRequired()])
    submit = SubmitField('Search →')

class StarNameParametersForm(FlaskForm):
    catalog_name = RadioField(u'Catalog Name')
    teff = RadioField(teff_label)
    logg = RadioField(u'log(g) (cm/s²)')
    mass = RadioField(mass_label)
    stell_rad = RadioField(rad_label)
    dist = RadioField(u'Distance (pc)')
    submit = SubmitField('Next →')