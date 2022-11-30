from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DecimalField, validators, RadioField, TextAreaField
from wtforms.validators import DataRequired, Email, Optional
from flask import Markup


class RequiredIf(DataRequired):
    """Validator which makes a field required if another field is set and has a truthy value."""
    field_flags = ('requiredif',)

    def __init__(self, *args, **kwargs):
        super(RequiredIf).__init__()
        self.message = "Manual input required."
        self.conditions = kwargs

    # field is requiring that name field in the form is data value in the form
    def __call__(self, form, field):
        for name, data in self.conditions.items():
            other_field = form[name]
            if other_field is None:
                raise Exception('no field named "%s" in form' % name)
            if other_field.data == data and not field.data:
                DataRequired.__call__(self, form, field)
            Optional()(form, field)


teff_label = Markup('T<sub>eff</sub> (K)')
mass_label = Markup('Mass (M<sub>sun</sub>)')
rad_label = Markup('Radius (R<sub>sun</sub>)')

class ParameterForm(FlaskForm):
    teff = DecimalField('T𝘦𝘧𝘧 — Stellar Effective Temperature (K)', validators=[DataRequired()])
    logg = DecimalField('log(g) — Surface Gravity (cm/s²)', validators=[DataRequired()])
    mass = DecimalField('M ☉ - Mass (Solar Masses)', validators=[DataRequired()])
    stell_rad = DecimalField('R ☉ — Stellar Radius (Solar Radii)', validators=[DataRequired()])
    dist = DecimalField('d — Distance', validators=[DataRequired()])
    dist_unit = SelectField('d Unit', validators=[DataRequired()], choices=[('pc', 'Parsecs (pc)'), ('mas', 'Milliarcseconds (mas)')])
    fuv = DecimalField('FUV (μJy)', validators=[DataRequired()])
    fuv_err = DecimalField('FUV err (μJy)', validators=[DataRequired()])
    fuv_flag = RadioField('FUV Flag', validators=[validators.Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit'), ('saturated', 'Saturated')])
    nuv = DecimalField('NUV (μJy)', validators=[DataRequired()])
    nuv_err = DecimalField('NUV err (μJy)', validators=[DataRequired()])
    nuv_flag = RadioField('NUV Flag', validators=[Optional()], choices=[('null', 'Not Detected'), ('upper_limit', 'Upper Limit'), ('saturated', 'Saturated')])
    submit = SubmitField('Submit and Find EUV Spectrum')

class StarNameForm(FlaskForm):
    star_name = StringField('Star Name', validators=[DataRequired()])
    submit = SubmitField('Search →')

class PositionForm(FlaskForm):
    # CHANGE THIS, NOT DECIMAL FIELD
    coords = StringField('hh mm ss.ss +/- dd mm ss.ss', validators=[DataRequired()])
    submit = SubmitField('Search →')

class StarNameParametersForm(FlaskForm):
    # IDEA: add manual text inputs for each option that are required if radio choice is Manual
    teff = RadioField(teff_label, choices=[('Manual', 'Manual')])
    manual_teff = DecimalField('T𝘦𝘧𝘧 — Stellar Effective Temperature (K)', validators=[RequiredIf(teff='Manual')])
    logg = RadioField(u'log(g) (cm/s²)', choices=[('Manual', 'Manual')])
    manual_logg = DecimalField('log(g) — Surface Gravity (cm/s²)', validators=[RequiredIf(logg='Manual')])
    mass = RadioField(mass_label, choices=[('Manual', 'Manual')])
    manual_mass = DecimalField('M ☉ - Mass (Solar Masses)', validators=[RequiredIf(mass='Manual')])
    stell_rad = RadioField(rad_label, choices=[('Manual', 'Manual')])
    manual_stell_rad = DecimalField('R ☉ — Stellar Radius (Solar Radii)', validators=[RequiredIf(stell_rad='Manual')])
    dist = RadioField(u'Distance (pc)', choices=[('Manual', 'Manual')])
    manual_dist = DecimalField('d - Distance', validators=[RequiredIf(dist='Manual')])
    fuv = RadioField('FUV Flux (μJy)', choices=[('Manual', 'Manual')])
    manual_fuv = DecimalField('FUV Flux (μJy)', validators=[RequiredIf(fuv='Manual')])
    fuv_err = RadioField('FUV Flux Error (μJy)', choices=[('Manual', 'Manual')])
    manual_fuv_err = DecimalField('FUV Flux Error (μJy)', validators=[RequiredIf(fuv_err='Manual')])
    nuv = RadioField('NUV Flux (μJy)', choices=[('Manual', 'Manual')])
    manual_nuv = DecimalField('NUV Flux (μJy)', validators=[RequiredIf(nuv='Manual')])
    nuv_err = RadioField('NUV Flux Error (μJy)', choices=[('Manual', 'Manual')])
    manual_nuv_err = DecimalField('NUV Flux Error (μJy)', validators=[RequiredIf(nuv_err='Manual')])
    submit = SubmitField('Next →')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email(granular_message=True)])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')