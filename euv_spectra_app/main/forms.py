from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length

class StarForm(FlaskForm):
    teff = IntegerField('T𝘦𝘧𝘧 — Stellar Effective Temperature  (K)', validators=[DataRequired()])
    logg = IntegerField('log g — Surface Gravity (cm/s²)', validators=[DataRequired()])
    mass = IntegerField('M ☉ - Mass in Solar Masses', validators=[DataRequired()])
    stell_rad = IntegerField('R ☉ — Stellar Radius in Solar Radian', validators=[DataRequired()])
    dist = IntegerField('d — Distance', validators=[DataRequired()])
    dist_unit = SelectField('d Unit', validators=[DataRequired()], choices=[('pc', 'Parsecs (pc)'), ('mas', 'Milliarcseconds (mas)')])
    fuv = IntegerField('FUV — Far Ultraviolet Spectra', validators=[DataRequired()])
    fuv_flag = SelectField('FUV Flag', validators=[DataRequired()], choices=[('none', 'None'), ('null', 'Null'), ('upper_limit', 'Upper Limit')])
    nuv = IntegerField('NUV — Near Ultraviolet Spectra', validators=[DataRequired()])
    nuv_flag = SelectField('NUV Flag', validators=[DataRequired()], choices=[('none', 'None'), ('null', 'Null'), ('upper_limit', 'Upper Limit')])

class StarNameForm(FlaskForm):
    name = StringField('Star Name', validators=[DataRequired()])
    submit = SubmitField('Next →')