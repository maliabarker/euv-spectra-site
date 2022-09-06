from flask import Blueprint, request, render_template, redirect, url_for
from datetime import date, datetime

from euv_spectra_app.models import Star
from euv_spectra_app.main.forms import StarForm, StarNameForm

# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Mast, Catalogs
from astroquery.vizier import Vizier

import pprint
pp = pprint.PrettyPrinter(indent=4)

main = Blueprint("main", __name__)

'''
————TODO—————

1. style form errors
    if there is a form error, keep the fuv and nuv inputs visible
    add flashes if there are form errors
    outline incorrect form inputs in red? (stretch)

2. query GALEX db when not searching by name

3. create GALEX search function instead of direct code under form submission
        # def search_galex_db():

4. change front end for fluxes from buttons to simply optional inputs

IDEAS
put fluxes as optional (meaning fields are empty) and check to see if there is any data for fluxes through API

QUESTIONS
how are we going to search galex DB without a name? (ex: when searching with first form)
what should we put as radius (also don't have to put radius)
'''

@main.route('/', methods=['GET', 'POST'])
def homepage():
    
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

            star_name = name_form.name.data
            print(star_name)

            '''GETTING FLUX VALUES FROM GALEX'''
            flux_catalog_data = Catalogs.query_object(name_form.name.data, radius=.02, catalog="GALEX")
            MIN_DIST = flux_catalog_data['distance_arcmin'] < 0.1
            
            filtered_data = flux_catalog_data[MIN_DIST]
            # filtered_data.pprint()

            fuv = filtered_data['fuv_flux']
            nuv = filtered_data['nuv_flux']

            print(f'FLUXES {fuv}, {nuv}')


            '''GETTING OTHER VALUES'''
            # info_catalog_data = Catalogs.query_object(name_form.name.data, radius=.02, catalog="TIC")
            # # print(info_catalog_data[0].columns)

            # info_row = info_catalog_data[0]

            # teff = info_row['Teff']
            # logg = info_row['logg']
            # mass = info_row['mass']
            # rad = info_row['rad']
            # dist = info_row['d']

            # print(f'INFO {teff}, {logg}, {mass}, {rad}, {dist}')

            return redirect(url_for('main.ex_result', formname='name'))

    return render_template('home.html', form=form, name_form=name_form)

@main.route('/ex-spectra', methods=['GET', 'POST'])
def ex_result():
    return render_template('result.html')




# TODO (stretch challenge) allow for file uploads to AWS bucket if adding new models/spectra, pagination
# from werkzeug.utils import secure_filename
# from data_app.util.helpers import upload_file_to_s3, read_csv_from_s3
# for uploading files
# ALLOWED_EXTENSIONS = {'png', 'csv'}
# FOR PAGINATION OF RESULTS OR SEARCH
# from flask_paginate import Pagination, get_page_parameter