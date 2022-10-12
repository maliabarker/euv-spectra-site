from flask import Blueprint, request, render_template, redirect, url_for, session
from flask_session import Session
from collections import defaultdict
from euv_spectra_app.extensions import app
from datetime import timedelta

from euv_spectra_app.main.forms import StarForm, StarNameForm, PositionForm, StarNameParametersForm
from euv_spectra_app.helpers import search_tic, search_nea, search_vizier, search_simbad, search_gaia, search_galex, correct_pm

main = Blueprint("main", __name__)

'''
————TODO—————
1. Double check Gaia return info and make sure PM calculations are correct

'''

'''
————NOTE————
- Gaia data is a little messy, does not return accurate info, SIMBAD returns good quality info, should we use??
- Two different ways of querying Gaia data, choose one
'''

@main.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)


@main.route('/', methods=['GET', 'POST'])
def homepage():
    #session.clear()
    print(session)

    parameter_form = StarForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    
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
            # STEP 1: store name data in session
            session["star_name"] = name_form.star_name.data
            star_name = session['star_name']
            print(f'name form validated with star: {star_name}')        

            # STEP 2: Get coordinate and motion info from Gaia
            gaia_data = search_gaia(star_name)

            # STEP 3: Put PM and Coord info into correction function
            corrected_coords = correct_pm(gaia_data['data'], star_name)

            # STEP 4: Search GALEX with these corrected coordinates
            galex_data = search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])
            print(galex_data)
            
            # STEP 5: 
            catalog_data = [search_tic(star_name), search_nea(star_name), search_vizier(star_name), search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])]
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

            global star_name_parameters_form
            star_name_parameters_form = StarNameParametersForm()

            star_name_parameters_form.catalog_name.choices = [(value, value) for value in res['name']]
            star_name_parameters_form.teff.choices = [(value, value) for value in res['teff']]
            star_name_parameters_form.logg.choices = [(value, value) for value in res['logg']]
            star_name_parameters_form.mass.choices = [(value, value) for value in res['mass']]
            star_name_parameters_form.stell_rad.choices = [(value, value) for value in res['rad']]
            star_name_parameters_form.dist.choices = [(value, value) for value in res['dist']]
            star_name_parameters_form.fuv.choices = [(value, value) for value in res['fuv']]
            star_name_parameters_form.nuv.choices = [(value, value) for value in res['nuv']]
            
            # session['fuv'] = galex_data['data']['fuv']
            # session['nuv'] = galex_data['data']['nuv']

            # check if either flux is null and make radio choice as not detected (will need to change javascript autofill function for these radio buttons)
            print(len(res['name']))
            last_num=str(len(res['name']) - 2)
            galex_num=str(len(res['name']) - 2)
            print(last_num)
            print(galex_num)

            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form, show_modal=True, last_num=last_num, galex_num=galex_num)
            

        elif session.get('star_name'):
            print('star name parameter form validated!')

            form_data = request.form
            print(form_data)

            for key in form_data:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                # to_ignore = ['manual', 'submit', 'csrf_token', 'catalog_name']
                # print(bool([ele for ele in ['manual', 'submit', 'csrf_token', 'catalog_name'] if(ele in key)]))
                
                if 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
                    print('form key '+key+" "+form_data[key])
                    session[key] = form_data[key]
                    
            print(session)
            return redirect(url_for('main.homepage'))

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, show_modal=False)


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