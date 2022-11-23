from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from flask_mail import Message, Mail
from collections import defaultdict
from euv_spectra_app.extensions import *
from datetime import timedelta
import json

from euv_spectra_app.main.forms import ParameterForm, StarNameForm, PositionForm, StarNameParametersForm, ContactForm
from euv_spectra_app.helpers_astropy import search_tic, search_nea, search_vizier, search_simbad, search_gaia, search_galex, correct_pm, test_space_motion, search_vizier_galex, convert_coords
from euv_spectra_app.helpers_db import *
from euv_spectra_app.helper_fits import *
from euv_spectra_app.helper_queries import *
main = Blueprint("main", __name__)

'''
————TODO—————

'''

'''
————NOTE————
- photosphere subtract fluxes are much larger than the galex photosphere subtracted fluxes (ex: 89.15518504954082 vs 2903269277063.380)
'''
@main.context_processor
def inject_form():
    form_dict = dict(contact_form=ContactForm())
    #print(form_dict)
    return dict(contact_form=ContactForm())


@main.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=20)
    if not session.get('modal_show'):
        session['modal_show'] = False


@main.route('/', methods=['GET', 'POST'])
def homepage():
    #session.clear()
    #test_space_motion()
    print(session)
    session['modal_show'] = False
    parameter_form = ParameterForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    star_name_parameters_form = StarNameParametersForm()
    

    if request.method == 'POST':
        print('————————POSTING...————————')
        print('—————————FORM DATA START—————————')
        form_data = request.form
        for key in form_data:
            print ('form key '+key+" "+form_data[key])
        print('—————————FORM DATA END—————————')


# '''————————————————————HOME POSITION FORM————————————————————'''
        if position_form.validate_on_submit():
            print('position form validated!')
            # STEP 1: Change coordinates to ra and dec
            session["search_term"] = position_form.coords.data
            coords = session["search_term"]

            # STEP 2: Change coordinates to ra and dec
            converted_coords = convert_coords(coords)
            if converted_coords['error_msg'] != None:
                return redirect(url_for('main.error', msg=converted_coords['error_msg']))

            # STEP 3: Search GALEX with coordinates
            galex_data = search_galex(converted_coords['data']['ra'], converted_coords['data']['dec'])
            if galex_data['error_msg'] != None:
                return redirect(url_for('main.error', msg=galex_data['error_msg']))

            print(galex_data)
            
            # STEP 4: Query all catalogs and append them to the final catalogs list if there are no errors
            catalog_data = [search_tic(f"{converted_coords['data']['ra']} {converted_coords['data']['dec']}", 'position'), search_nea(converted_coords['data']['skycoord_obj'], 'position'), galex_data]
            final_catalogs = [catalog for catalog in catalog_data if catalog['error_msg'] == None]
            #print(f'FINAL CATALOG TEST {final_catalogs}')

            # STEP 5: Create a dictionary that holds all parameters in a list ex: {'teff' : [teff_1, teff_2, teff_3]}
                    # Will be useful for next step, dynamically adding radio buttons to flask wtform
            res = defaultdict(list)
            for dict in final_catalogs:
                for key in dict:
                    if key == 'data':
                        for key_2 in dict[key]:
                            if key_2 != 'error_msg' and key_2 != 'valid_info':
                                res[key_2].append(dict[key][key_2])
                    else:
                        if key != 'error_msg' and key != 'valid_info':
                            res[key].append(dict[key])

            # STEP 6: Append a manual option to each parameter
            for key in res:
                res[key].append('Manual')
            print(res)

            session['modal_choices'] = json.dumps(res, allow_nan=True)

            # STEP 8: Declare the form and add the radio choices dynamically for each radio input on the form
            for key in res:
                radio_input = getattr(star_name_parameters_form, key)
                radio_input.choices = [(value, value) for value in res[key]]

            session['modal_show'] = True
            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form)
            

# '''————————————————————HOME NAME FORM————————————————————'''
        elif name_form.validate_on_submit():
            # STEP 1: store name data in session
            session["search_term"] = name_form.star_name.data
            star_name = session["search_term"]
            print(f'name form validated with star: {star_name}')

            # STEP 2: Get coordinate and motion info from Simbad
            simbad_data = search_simbad(star_name)
            print('simbad ran with no errors')
            if simbad_data['error_msg'] != None:
                return redirect(url_for('main.error', msg=simbad_data['error_msg']))

            # STEP 3: Put PM and Coord info into correction function
            corrected_coords = correct_pm(simbad_data['data'], star_name)
            print('coordinate correction ran with no errors')
            if corrected_coords['error_msg'] != None:
                return redirect(url_for('main.error', msg=corrected_coords['error_msg']))

            # STEP 4: Search GALEX with these corrected coordinates
            galex_data = search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])
            print(galex_data)
            
            # STEP 5: Query all catalogs and append them to the final catalogs list if there are no errors
            catalog_data = [search_tic(star_name, 'name'), search_nea(star_name, 'name'), search_galex(corrected_coords['data']['ra'], corrected_coords['data']['dec'])]
            final_catalogs = [catalog for catalog in catalog_data if catalog['error_msg'] == None]
            #print(f'FINAL CATALOG TEST {final_catalogs}')

            # STEP 6: Create a dictionary that holds all parameters in a list ex: {'teff' : [teff_1, teff_2, teff_3]}
                    # Will be useful for next step, dynamically adding radio buttons to flask wtform
            res = defaultdict(list)
            for dict in final_catalogs:
                for key in dict:
                    if key == 'data':
                        for key_2 in dict[key]:
                            if key_2 != 'error_msg' and key_2 != 'valid_info':
                                res[key_2].append(dict[key][key_2])
                    else:
                        if key != 'error_msg' and key != 'valid_info':
                            res[key].append(dict[key])

            # STEP 7: Append a manual option to each parameter
            for key in res:
                res[key].append('Manual')
            print(res)

            session['modal_choices'] = json.dumps(res, allow_nan=True)

            # STEP 8: Declare the form and add the radio choices dynamically for each radio input on the form
            for key in res:
                radio_input = getattr(star_name_parameters_form, key)
                radio_input.choices = [(value, value) for value in res[key]]

            session['modal_show'] = True
            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form)

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form)



'''————————————SUBMIT ROUTE FOR MODAL FORM————————————'''
@main.route('/modal-submit', methods=['GET', 'POST'])
def submit_modal_form():
    parameter_form_1 = ParameterForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    parameter_form = StarNameParametersForm()
    
    choices = json.loads(session['modal_choices'])
    print(choices)

    for key in choices:
        radio_input = getattr(parameter_form, key)
        radio_input.choices = [(value, value) for value in choices[key]]
    
    parameter_form.populate_obj(request.form)
    print(request.form)
    print(parameter_form)

    if request.method == 'POST':
        if parameter_form.validate_on_submit():
            print('star name parameter form validated!')

            for field in parameter_form:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                print('AHHHHHHH')
                print(field)
                print(field.name, field.data)
                if field.data == 'No Detection':
                    # set flux to null if it equals --
                    print(f'null flux detected in {field.name}')
                    session[field.name] = 'null'
                elif 'manual' in field.name and field.data != None:
                    print('MANUAL INPUT DETECTED')
                    print(field.name, field.data)
                    unmanual_field = field.name.replace('manual_', '')
                    session[unmanual_field] = float(field.data)
                elif 'manual' not in field.name and 'submit' not in field.name and 'csrf_token' not in field.name and 'catalog_name' not in field.name and 'Manual' not in field.data:
                    print('form key '+field.name+" "+field.data)
                    session[field.name] = float(field.data)
            
            print(session)

            return redirect(url_for('main.return_results'))
        else:
            print('NOT VALIDATED')
            print(parameter_form.errors)
    return render_template('home.html', parameter_form=parameter_form_1, name_form=name_form, position_form=position_form, star_name_parameters_form=parameter_form)



'''————————————SUBMIT ROUTE FOR MANUAL INPUT————————————'''
@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    form = ParameterForm(request.form)
    if form.validate_on_submit():
        print('parameter form validated!')

        for fieldname, value in form.data.items():
            #CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
            # mas_to_pc = 1/ (X mas / 1000)
            if fieldname == "dist_unit" or "flag" in fieldname or "csrf_token" in fieldname:
                if value == 'mas':
                    session['dist'] = int(1 / (form.dist.data / 1000))
                if value == 'null':
                    which_flux = fieldname[0:2]
                    session[which_flux] = 'null'
                    session[f'{which_flux}_err'] = 'null'
            else:
                print(f'form key: {fieldname}, value: {value}')
                session[fieldname] = float(value)
        return redirect(url_for('main.return_results'))
    else:
        flash('Whoops, something went wrong. Please check your inputs and try again!', 'danger')
        return redirect(url_for('main.homepage'))



'''————————————SUBMIT ROUTE FOR RESULTS————————————'''
@main.route('/results', methods=['GET', 'POST'])
def return_results():
    #TODO find a better way to check that all data needed is here before continuing
    if session.get('teff') and session.get('logg') and session.get('mass') and session.get('stell_rad') and session.get('dist'):
        # STEP 1: Search the model_parameter_grid collection to find closest matching subtype
        matching_subtype = find_matching_subtype(session)
        session['model_subtype'] = matching_subtype['model']

        #STEP 2: Find closest matching photosphere model and get flux values
        matching_photospheric_flux = find_matching_photosphere(session)

        #STEP 3: Convert, scale, and subtract photospheric contribution from fluxes (more detail in function)
        corrected_fluxes = convert_and_scale_fluxes(session, matching_photospheric_flux)
        session['corrected_nuv'] = corrected_fluxes['nuv']
        session['corrected_nuv_err'] = corrected_fluxes['nuv_err']
        session['corrected_fuv'] = corrected_fluxes['fuv']
        session['corrected_fuv_err'] = corrected_fluxes['fuv_err']
        print(session)

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{session["model_subtype"].lower()}_grid'
        if model_collection not in db.list_collection_names():
            return redirect(url_for('main.error', msg=f'The grid for model subtype {session["model_subtype"]} is currently unavailable. Please contact us with your stellar parameters and returned subtype.'))
        
        # STEP 5: Do chi squared test between all models within selected subgrid and corrected observation ** this is on models with subtracted photospheric flux
        models_with_chi_squared = list(get_models_with_chi_squared(session, model_collection))

        # STEP 6: Find all matches in model grid within upper and lower limits of galex fluxes
        models_in_limits = list(get_models_within_limits(session, model_collection, models_with_chi_squared))

        # TODO return from lowest chi squared -> highest
        # TODO return euv flux as <euv_flux> +/- difference from model
        
        if len(list(models_in_limits)) == 0:
            # STEP 7.1: If there are no models found within limits, return model with lowest chi squared value
            print('Nohting found within limits, MODEL W CHI SQUARED')
            print(models_with_chi_squared[0])

            #STEP 8.1: Read FITS file from matching model and create graph from data
            filename = models_with_chi_squared[0]['fits_filename']
            print(filename)
            file = find_fits_file(filename)

            # CATCH: For testing purposes, if fits file is not available yet, flash warning and use test file
            test_file = find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits') # TEST FILE
            if file == None:
                flash('EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger')
                file = test_file

            fig = create_graph([file], [models_with_chi_squared[0]['chi_squared']], session)

            #STEP 9.1: Convert graph into html component and send to front end
            html_string = convert_fig_to_html(fig)

            flash('No results found within upper and lower limits of UV fluxes. Returning document with nearest chi squared value.', 'warning')
            return render_template('result.html', subtype=matching_subtype, graph=html_string)
        else:
            # STEP 7.2: If there are models found within limits, map the id's to the models with chi squared
            print(f'MODELS WITHIN LIMITS: {len(list(models_in_limits))}')
            for doc in models_in_limits:
                print(doc)

            results = []
            for x in models_in_limits:
                for y in models_with_chi_squared:
                    if x['_id'] == y['_id']:
                        results_test.append(y)

            #STEP 8.2: Read all FITS files from matching models and create graph from data
            files = []
            chi_squared_vals = []
            for doc in results:
                file = find_fits_file(doc['fits_filename'])
                if file:
                    files.append()
                    chi_squared_vals.append(doc['chi_squared'])

            fig = create_graph(files, chi_squared_vals, session)

            #STEP 9.2: Convert graph into html component and send to front end
            html_string = convert_fig_to_html(fig)
            flash(len(list(models_in_limits)) + 'results found within your submitted parameters')
            return render_template('result.html', subtype=matching_subtype, graph=html_string)
    else:
        flash('Submit the required data to view this page.', 'warning')
        return redirect(url_for('main.homepage'))



'''————————————ABOUT PAGE————————————'''
@main.route('/about', methods=['GET'])
def about():
    
    return render_template('about.html')



'''————————————FAQ PAGE————————————'''
@main.route('/faqs', methods=['GET'])
def faqs():
    
    return render_template('faqs.html')



'''————————————ALL SPECTRA PAGE————————————'''
@main.route('/all-spectra', methods=['GET'])
def index_spectra():
    return render_template('index-spectra.html')



'''————————————CONTACT SUBMIT————————————'''
@main.route('/contact', methods=['POST'])
def send_email():
    form = ContactForm(request.form)

    if form.validate_on_submit():
        # send email
        msg = Message(form.subject.data,
                      sender=(form.name.data, form.email.data),
                      recipients=['phoenixpegasusgrid@gmail.com'],
                      body=f'FROM {form.name.data}, {form.email.data}\n MESSAGE: {form.message.data}')
        mail.send(msg)
        flash('Email sent!', 'success')
        return redirect(url_for('main.homepage'))
    else:
        print(form.errors)
        flash('error', 'danger')
        return redirect(url_for('main.error', msg='Contact form unavailable at this time, please email phoenixpegasusgrid@gmail.com directly.'))


@main.route('/clear-session')
def clear_session():
    session.clear()
    return redirect(url_for('main.homepage'))

''' ————————————ERROR HANDLING FOR HTML ERRORS———————————— '''
@main.route('/error/<msg>')
def error(msg):
    session['modal_show'] = False
    return render_template('error.html', error_msg=msg)

# @main.app_errorhandler(500)
# def internal_error(e):
#     print(e)
#     session['modal_show'] = False
#     return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (500)', contact_form=ContactForm()), 500

@main.app_errorhandler(503)
def internal_error(e):
    print(e)
    session['modal_show'] = False
    return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (503)', contact_form=ContactForm()), 503

@main.app_errorhandler(404)
def page_not_found(e):
    print(e)
    session['modal_show'] = False
    return render_template('error.html', error_msg='Page not found!', contact_form=ContactForm()), 404
