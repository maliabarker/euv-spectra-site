from typing import Optional
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField, validators, RadioField
from wtforms.validators import DataRequired, Length

class StarForm(FlaskForm):
    teff = IntegerField('T𝘦𝘧𝘧 — Stellar Effective Temperature (K)', validators=[DataRequired()])
    logg = IntegerField('log g — Surface Gravity (cm/s²)', validators=[DataRequired()])
    mass = IntegerField('M ☉ - Mass (Solar Masses)', validators=[DataRequired()])
    stell_rad = IntegerField('R ☉ — Stellar Radius (Solar Radii)', validators=[DataRequired()])
    dist = IntegerField('d — Distance', validators=[DataRequired()])
    dist_unit = SelectField('d Unit', validators=[DataRequired()], choices=[('pc', 'Parsecs (pc)'), ('mas', 'Milliarcseconds (mas)')])
    fuv = IntegerField('FUV — Far Ultraviolet Spectra (μJy)', validators=[validators.Optional()])
    fuv_flag = RadioField('FUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    nuv = IntegerField('NUV — Near Ultraviolet Spectra (μJy)', validators=[validators.Optional()])
    nuv_flag = RadioField('NUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit')])
    submit = SubmitField('Next →')

class StarNameForm(FlaskForm):
    name = StringField('Star Name', validators=[DataRequired()])
    submit = SubmitField('Next →')

class PositionForm(FlaskForm):
    ra = IntegerField('RA — Right Ascension (deg)', validators=[DataRequired()])
    dec = IntegerField('Dec — Declination (deg)', validators=[DataRequired()])
    submit = SubmitField('Next →')