from cgitb import text
from typing import Optional
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DecimalField, validators, RadioField, widgets
from wtforms.validators import DataRequired, Length

class StarForm(FlaskForm):
    teff = DecimalField('T𝘦𝘧𝘧 — Stellar Effective Temperature (K)', validators=[DataRequired()])
    logg = DecimalField('log g — Surface Gravity (cm/s²)', validators=[DataRequired()])
    mass = DecimalField('M ☉ - Mass (Solar Masses)', validators=[DataRequired()])
    stell_rad = DecimalField('R ☉ — Stellar Radius (Solar Radii)', validators=[DataRequired()])
    dist = DecimalField('d — Distance', validators=[DataRequired()])
    dist_unit = SelectField('d Unit', validators=[DataRequired()], choices=[('pc', 'Parsecs (pc)'), ('mas', 'Milliarcseconds (mas)')])
    submit = SubmitField('Next →')

class StarNameForm(FlaskForm):
    star_name = StringField('Star Name', validators=[DataRequired()])
    submit = SubmitField('Next →')

class PositionForm(FlaskForm):
    ra = DecimalField('RA — Right Ascension (deg)', validators=[DataRequired()])
    dec = DecimalField('Dec — Declination (deg)', validators=[DataRequired()])
    submit = SubmitField('Next →')

class StarNameParametersForm(FlaskForm):
    catalog_name = RadioField(u'Catalog Name')
    teff = RadioField(u'Stellar Effective Temp (K)')
    logg = RadioField(u'Surface Gravity (cm/s²)')
    mass = RadioField(u'Mass (Solar Masses)')
    stell_rad = RadioField(u'Stellar Rad (Solar Radii)')
    dist = RadioField(u'Distance (pc)')
    submit = SubmitField('Next →')

class FluxForm(FlaskForm):
    fuv = DecimalField('FUV — Far Ultraviolet Spectra (μJy)', validators=[validators.Optional()])
    fuv_flag = RadioField('FUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    nuv = DecimalField('NUV — Near Ultraviolet Spectra (μJy)', validators=[validators.Optional()])
    nuv_flag = RadioField('NUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    submit = SubmitField('Next →')