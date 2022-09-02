from flask import Blueprint, request, render_template, redirect, url_for
from datetime import date, datetime

from euv_spectra_app.models import Star
from euv_spectra_app.main.forms import StarForm, StarNameForm

'''
# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Mast, Observations

obs_table = Observations.query_object("2MASS 11315526-3436272",radius=".02 deg")

import requests
from urllib.parse import quote as urlencode

from astropy.table import Table
import numpy as np

import pprint
pp = pprint.PrettyPrinter(indent=4)
'''


# FOR PAGINATION OF RESULTS OR SEARCH
# from flask_paginate import Pagination, get_page_parameter

from euv_spectra_app.extensions import app, db

# TODO (stretch challenge) allow for file uploads to AWS bucket if adding new models/spectra
# from werkzeug.utils import secure_filename
# from data_app.util.helpers import upload_file_to_s3, read_csv_from_s3
# for uploading files
# ALLOWED_EXTENSIONS = {'png', 'csv'}

main = Blueprint("main", __name__)

'''
TODO

style form error better
if there is a form error, keep the fuv and nuv inputs visible
add flashes if there are form errors

IDEA
put fluxes as optional (meaning fields are empty) and check to see if there is any data for fluxes through API
'''

@main.route('/', methods=['GET', 'POST'])
def homepage():
    # print(obs_table[:10][0])
    form = StarForm()
    name_form = StarNameForm()

    if request.method == 'POST':
        print('————————POSTING————————')

        if form.validate_on_submit():
            print('form validated!')
            print(form)

            for fieldname, value in form.data.items():
                print(fieldname, value)
            
            return redirect(url_for('main.ex_result', formname='main'))

        elif name_form.validate_on_submit():
            print('name form validated!')
            print(name_form)
            
            for fieldname, value in name_form.data.items():
                print(fieldname, value)

            return redirect(url_for('main.ex_result', formname='name'))

    return render_template('home.html', form=form, name_form=name_form)

@main.route('/ex-spectra', methods=['GET', 'POST'])
def ex_result():
    return render_template('result.html')