from cgi import test
from flask import Blueprint, request, render_template, redirect, url_for, session
from collections import defaultdict
from euv_spectra_app.extensions import app
from datetime import timedelta

from euv_spectra_app.main.forms import StarForm, StarNameForm, PositionForm, StarNameParametersForm
from euv_spectra_app.helpers import search_tic, search_nea, search_vizier, search_simbad, search_gaia, search_galex, correct_pm, test_space_motion

main = Blueprint("main", __name__)

'''
————TODO—————
1. Do something about space motion function? For PM
2. Check if either flux is null and make radio choice as not detected (will need to change javascript autofill function for these radio buttons)
3. If no galex data found: flash no galex data was found, somehow let user know theres no galex data, maybe in template?
'''

'''
————NOTE————

'''

@main.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)


@main.route('/', methods=['GET', 'POST'])
def homepage():
    #session.clear()
    #test_space_motion()
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


# '''————————————————————HOME PARAMETER FORM————————————————————'''
        if parameter_form.validate_on_submit():
            print('parameter form validated!')
            print(parameter_form)

            for fieldname, value in parameter_form.data.items():
                print(fieldname, value)

            return redirect(url_for('main.ex_result'))


# '''————————————————————HOME POSITION FORM————————————————————'''
        elif position_form.validate_on_submit():
            print('position form validated!')



# '''————————————————————HOME NAME FORM————————————————————'''
        elif name_form.validate_on_submit():
            # STEP 1: store name data in session
            session["star_name"] = name_form.star_name.data
            star_name = session['star_name']
            print(f'name form validated with star: {star_name}')        

            # STEP 2: Get coordinate and motion info from Simbad
            simbad_data = search_simbad(star_name)
            if simbad_data['error_msg'] != None:
                return render_template('error.html', error_msg=simbad_data['error_msg'])

            # STEP 3: Put PM and Coord info into correction function
            corrected_coords = correct_pm(simbad_data['data'], star_name)
            if corrected_coords['error_msg'] != None:
                return render_template('error.html', error_msg=corrected_coords['error_msg'])

            # STEP 4: Search GALEX with these corrected coordinates
            galex_data = search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])
            print(galex_data)
            
            # STEP 5: Query all catalogs and append them to the final catalogs list if there are no errors
            catalog_data = [search_tic(star_name), search_nea(star_name), search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])]
            final_catalogs = [catalog for catalog in catalog_data if catalog['error_msg'] == None if catalog['catalog_name'] != 'Vizier']+[sub_catalog for catalog in catalog_data for sub_catalog in catalog['data'] if catalog['catalog_name'] == 'Vizier' if sub_catalog['error_msg'] == None]
            #print(f'FINAL CATALOG TEST {final_catalogs}')

            # STEP 6: Create a dictionary that holds all parameters in a list ex: {'teff' : [teff_1, teff_2, teff_3]}
                    # Will be useful for next step, dynamically adding radio buttons to flask wtform
            res = defaultdict(list)
            for dict in final_catalogs:
                for key in dict:
                    if key == 'data':
                        for key_2 in dict[key]:
                            res[key_2].append(dict[key][key_2])
                    else:
                        res[key].append(dict[key])

            # STEP 7: Append a manual option to each parameter
            for key in res:
                res[key].append('Manual')
            print(res)

            # STEP 8: Declare the form and add the radio choices dynamically for each radio input on the form
            star_name_parameters_form = StarNameParametersForm()
            for key in res:
                if key != 'valid_info' and key != 'error_msg':
                    radio_input = getattr(star_name_parameters_form, key)
                    radio_input.choices = [(value, value) for value in res[key]]

            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form, show_modal=True)
            


#'''————————————————————MODAL NAME PARAMETER FORM————————————————————'''
        elif session.get('star_name'):
            print('star name parameter form validated!')
            form_data = request.form

            for key in form_data:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
                    print('form key '+key+" "+form_data[key])
                    session[key] = form_data[key]
                    
            print(session)
            return redirect(url_for('main.homepage'))

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, show_modal=False)




@main.route('/ex-spectra', methods=['GET', 'POST'])
def ex_result():
    return render_template('result.html')




# FOR PAGINATION OF RESULTS OR SEARCH
# from flask_paginate import Pagination, get_page_parameter