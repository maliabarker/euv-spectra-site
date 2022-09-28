from cmath import nan
from flask import Blueprint, request, render_template, redirect, url_for, jsonify, session
from flask_session import Session
from collections import defaultdict

from euv_spectra_app.models import Star
from euv_spectra_app.main.forms import StarForm, StarNameForm, PositionForm, StarNameParametersForm, FluxForm

# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Catalogs
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.vizier import Vizier
from astroquery.mast import Observations
import astropy.units as u
import numpy as np

import pprint
pp = pprint.PrettyPrinter(indent=4)


main = Blueprint("main", __name__)


# ——————————— HELPER FUNCTIONS ————————————— #
def search_galex(search_input):
    galex_data = Catalogs.query_object(search_input, radius=.02, catalog="GALEX")
    return_info = {
        'name' : 'GALEX',
        'data' : None,
        'error_msg' : None
    }
    if len(galex_data) > 0:
        MIN_DIST = galex_data['distance_arcmin'] < 0.3 # can try 0.5 as well
        if len(galex_data[MIN_DIST]) > 0:
            filtered_data = galex_data[MIN_DIST][0]
            # add dist arcmin value
            fluxes = {
                'fuv' : filtered_data['fuv_flux'],
                'nuv' : filtered_data['nuv_flux']
            }
            return_info['data'] = fluxes
        else:
            return_info['error_msg'] = 'No data points with distance arcmin under 0.1'
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return return_info


def search_tic(search_input):
    tic_data = Catalogs.query_object(search_input, radius=.02, catalog="TIC")
    return_info = {
        'name' : 'TESS Input Catalog',
        'valid_info' : 0,
        'data' : {},
        'error_msg' : None
    }
    if len(tic_data) > 0:
        data = tic_data[0]
        star_info = {
            'teff' : float(data['Teff']),
            'logg' : float(data['logg']),
            'mass' : float(data['mass']),
            'rad' : float(data['rad']),
            'dist' : float(data['d'])
        }
        return_info['data'] = star_info
        for value in star_info.values():
            if str(value) != 'nan':
                return_info['valid_info'] += 1
        # print('———————————————————————————')
        # print('TIC')
        # print(data)
        # print(star_info)
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return(return_info)


def search_nea(search_input):
    nea_data = NasaExoplanetArchive.query_criteria(table="pscomppars", where=f"hostname like '%{search_input}%'", order="hostname")
    return_info = {
        'name' : 'NASA Exoplanet Archive',
        'valid_info' : 0,
        'data' : {},
        'error_msg' : None
    }
    if len(nea_data) > 0:
        data = nea_data[0]
        # print('———————————————————————————')
        # print('Exoplanet Archive')
        # print(data)
        star_info = {
            'teff' : data['st_teff'].unmasked.value,
            'logg' : data['st_logg'],
            'mass' : data['st_mass'].unmasked.value,
            'rad' : data['st_rad'].unmasked.value,
            'dist' : data['sy_dist'].unmasked.value
        }
        return_info['data'] = star_info
        for value in star_info.values():
            if str(value) != 'nan':
                return_info['valid_info'] += 1
        # print(star_info)
        # print(f'VALID INFO: {valid_info}')
    else:
        return_info['error_msg'] = 'Nothing found for this target'

    return(return_info)


def search_vizier(search_input):
    tables = []
    keywords = ['teff', 'logg', 'mass', 'rad', 'dist']

    return_info = {
        'name' : 'Vizier',
        'data' : [],
        'error_msg' : None
    }

    vizier_catalogs = Vizier.query_object(search_input)

    for table_name in vizier_catalogs.keys():
        table = vizier_catalogs[table_name]
        cols = list(col.lower() for col in table.columns)

        if all(elem in cols for elem in keywords):
            if table_name not in tables:
                tables.append(table_name)

    # print(f'VIZIER TABLES: {tables}')
    if tables:
        for table_name in tables:
            table = vizier_catalogs[table_name][0]
            # print('————————————————————————')
            # print(f'TABLE NAME: {table_name}')
            # print(table)
            valid_info = 0
            star_info = {
                'teff' : float(table['Teff']),
                'logg' : float(table['logg']),
                'mass' : float(table['Mass']),
                'rad' : float(table['Rad']),
                'dist' : float(table['Dist'])
            }

            for value in star_info.values():
                if str(value) != 'nan':
                    valid_info += 1

            # print(star_info)
            # print(f'VALID INFO: {valid_info}')
            table_dict = {
                'name' : f'Vizier catalog: {table_name}',
                'data' : star_info,
                'valid_info' : valid_info,
                'error_msg' : None
            }

            if valid_info == 0:
                table_dict['error_msg'] = 'No data found'

            return_info['data'].append(table_dict)
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return(return_info)


# ——————————— END HELPER FUNCTIONS ————————————— #
'''
————TODO—————
1. implement axios for the following:
    a. when searching by name or position, return all found parameters and allow for editing then submit
    b. when manually entering parameters, continue onto flux/galex inputs
    QUESTION: do we want to allow ppl to have choice of manually entering/searching for flux for NAME SEARCH also?

2. create front end for flux input options/search galex (maybe w page anchor tags/scroll?)

3. run searches for imported models w weights


'''

@main.route('/', methods=['GET', 'POST'])
def homepage():

    parameter_form = StarForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    flux_form = FluxForm()
    
    if request.method == 'POST':
        print('————————POSTING...————————')
        print('—————————FORM DATA START—————————')
        form_data = request.form
        for key in form_data:
            print ('form key '+key+" "+form_data[key])
        print('—————————FORM DATA END—————————')

        if parameter_form.validate_on_submit():
            print('parameter form validated!')
            print(parameter_form)

            for fieldname, value in parameter_form.data.items():
                print(fieldname, value)

            
            return redirect(url_for('main.ex_result'))

        elif position_form.validate_on_submit():
            print('position form validated!')


        elif name_form.validate_on_submit():
            # store name data in session
            session["star_name"] = name_form.name.data
            star_name = session['star_name']
            print(f'name form validated with star: {star_name}')

            global star_name_parameters_form
            star_name_parameters_form = StarNameParametersForm()

            # galex_data = search_galex(star_name)
            # print(galex_data)

            catalog_data = [search_tic(star_name), search_nea(star_name), search_vizier(star_name)]

            final_catalogs = [catalog for catalog in catalog_data if catalog['error_msg'] == None if catalog['name'] != 'Vizier']+[sub_catalog for catalog in catalog_data for sub_catalog in catalog['data'] if catalog['name'] == 'Vizier' if sub_catalog['error_msg'] == None]
            
            print(f'FINAL CATALOG TEST {final_catalogs}')

            res = defaultdict(list)
            for dict in final_catalogs:
                for key in dict:
                    if key == 'data':
                        for key_2 in dict[key]:
                            res[key_2].append(dict[key][key_2])
                    else:
                        res[key].append(dict[key])

            for key in res:
                res[key].append('Manual')

            print(res)

            star_name_parameters_form.catalog_name.choices = [(value, value) for value in res['name']]
            star_name_parameters_form.teff.choices = [(value, value) for value in res['teff']]
            star_name_parameters_form.logg.choices = [(value, value) for value in res['logg']]
            star_name_parameters_form.mass.choices = [(value, value) for value in res['mass']]
            star_name_parameters_form.stell_rad.choices = [(value, value) for value in res['rad']]
            star_name_parameters_form.dist.choices = [(value, value) for value in res['dist']]

            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, flux_form=flux_form, star_name_parameters_form=star_name_parameters_form, show_modal=True, last_num=str(len(res['name']) - 1))


        elif session['star_name']:
            print('star name parameter form validated!')
            form_data = request.form
            for key in form_data:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
                    # print ('form key '+key+" "+form_data[key])
                    session[key] = form_data[key]
                    
            print(session)
            #return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, show_modal=False)
            return redirect(url_for('main.homepage'))

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, flux_form=flux_form, show_modal=False)


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