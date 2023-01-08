from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app, send_from_directory, jsonify
from flask_mail import Message
from euv_spectra_app.extensions import *
from datetime import timedelta
import json
import plotly
import os

from euv_spectra_app.main.forms import ParameterForm, StarNameForm, PositionForm, StarNameParametersForm, ContactForm
from euv_spectra_app.helpers_astropy import search_nea, search_simbad, search_galex, correct_pm, convert_coords
from euv_spectra_app.helper_fits import convert_and_scale_fluxes, create_plotly_graph
from euv_spectra_app.helper_queries import find_matching_subtype, find_matching_photosphere, get_models_with_chi_squared, get_models_within_limits, get_models_with_lowest_fuv

# Used when importing new data into mongodb atlas
# from euv_spectra_app.helpers_db import *

main = Blueprint("main", __name__)


'''————————— HELPER FUNCTION FOR SEARCHING OBJECT/POSITION & RETURNING FOR MODAL POPULATION —————————'''
def populate_modal(search_term, search_type):
    # print(search_term, search_type)

    session["search_term"] = search_term
    galex_coords = None

    return_data = {
        'error_msg': None,
        'radio_choices': None
    }

    if search_type == 'position':
        # STEP 1: Assign search term to coords
        coords = session["search_term"]

        # STEP 2: Change coordinates to ra and dec
        converted_coords = convert_coords(coords)
        if converted_coords['error_msg'] != None:
            return_data['error_msg'] = converted_coords['error_msg']
            return return_data

        galex_coords = converted_coords
        search_term = converted_coords['data']['skycoord_obj']

    elif search_type == 'name':
        # STEP 1: store name data in session
        star_name = session["search_term"]

        # STEP 2: Get coordinate and motion info from Simbad
        simbad_data = search_simbad(star_name)
        if simbad_data['error_msg'] != None:
            return_data['error_msg'] = simbad_data['error_msg']
            return return_data

        # STEP 3: Put PM and Coord info into correction function
        corrected_coords = correct_pm(simbad_data['data'], star_name)
        # print(f'CORRECTED COORDS {corrected_coords}')
        if corrected_coords['error_msg'] != None:
            return_data['error_msg'] = corrected_coords['error_msg']
            return return_data

        galex_coords = corrected_coords
        
    # STEP 4: Search GALEX with corrected or converted coords
    galex_data = search_galex(galex_coords['data']['ra'], galex_coords['data']['dec'])
    if galex_data['error_msg'] != None:
        return_data['error_msg'] = galex_data['error_msg']
        return return_data

    nea_data = search_nea(search_term, search_type)
    if nea_data['error_msg'] != None:
        return_data['error_msg'] = nea_data['error_msg']
        return return_data

    # STEP 5: Query all catalogs and append them to the final catalogs list if there are no errors
    catalog_data = [nea_data, galex_data]
    final_catalogs = [catalog for catalog in catalog_data if catalog['error_msg'] == None]

    # STEP 6: Append each type of data into its own key value pair
    data = {key: dict['data'][key] for dict in final_catalogs for key in dict['data']}
    return_data['radio_choices'] = data

    # print(return_data['radio_choices'])

    # STEP 7: Store this data for later use (repopulating model, validation)
    session['modal_choices'] = json.dumps(return_data['radio_choices'], allow_nan=True)
    return return_data



@main.context_processor
def inject_form():
    return dict(contact_form=ContactForm())


@main.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=20)
    if not session.get('modal_show'):
        session['modal_show'] = False


@main.route('/', methods=['GET', 'POST'])
def homepage():
    # session.clear()
    print(session)
    session['modal_show'] = False

    parameter_form = ParameterForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    star_name_parameters_form = StarNameParametersForm()

    autofill_data = db.mast_galex_times.distinct('target')

    if request.method == 'POST':
# '''————————————————————HOME POSITION FORM————————————————————'''
        if position_form.validate_on_submit():
            print('position form validated!')

            # STEP 1: Run the helper function to get a dynamic WTForm instance with your data
            res = populate_modal(position_form.coords.data, 'position')

            if res['error_msg'] != None:
                return redirect(url_for('main.error', msg=res['error_msg']))

            # STEP 2: Declare the form and add the radio choices dynamically for each radio input on the form
            for key, val in res['radio_choices'].items():
                radio_input = getattr(star_name_parameters_form, key)
                radio_input.choices.insert(0, (val, val))

            # STEP 3: Set modal show to true
            session['modal_show'] = True
            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form, targets=autofill_data)
            

# '''————————————————————HOME NAME FORM————————————————————'''
        elif name_form.validate_on_submit():
            print(f'name form validated!')
            
            # STEP 1: Run the helper function to get a dynamic WTForm instance with your data
            res = populate_modal(name_form.star_name.data, 'name')
            
            if res['error_msg'] != None:
                return redirect(url_for('main.error', msg=res['error_msg']))

            # STEP 2: Declare the form and add the radio choices dynamically for each radio input on the form
            for key, val in res['radio_choices'].items():
                radio_input = getattr(star_name_parameters_form, key)
                radio_input.choices.insert(0, (val, val))

            # STEP 3: Set modal show to true
            session['modal_show'] = True
            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form, targets=autofill_data)
    flash('Website is under development. Files are not available for use yet. For testing purposes, try out object GJ 338 B.', 'warning')
    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, targets=autofill_data)



'''————————————SUBMIT ROUTE FOR MODAL FORM————————————'''
@main.route('/modal-submit', methods=['GET', 'POST'])
def submit_modal_form():
    parameter_form_1 = ParameterForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    parameter_form = StarNameParametersForm()

    autofill_data = db.mast_galex_times.distinct('target')
    
    choices = json.loads(session['modal_choices'])

    for key, val in choices.items():
        radio_input = getattr(parameter_form, key)
        radio_input.choices.insert(0, (val, val))
    
    parameter_form.populate_obj(request.form)

    if request.method == 'POST':
        if parameter_form.validate_on_submit():
            # print('star name parameter form validated!')

            for field in parameter_form:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if field.data == 'No Detection':
                    # set flux to null if it equals --
                    session[field.name] = 'null'
                elif 'manual' in field.name and field.data != None:
                    unmanual_field = field.name.replace('manual_', '')
                    session[unmanual_field] = float(field.data)
                elif 'manual' not in field.name and 'submit' not in field.name and 'csrf_token' not in field.name and 'Manual' not in field.data:
                    # print('form key '+field.name+" "+field.data)
                    session[field.name] = float(field.data)

            return redirect(url_for('main.return_results'))
    return render_template('home.html', parameter_form=parameter_form_1, name_form=name_form, position_form=position_form, star_name_parameters_form=parameter_form, targets=autofill_data)



'''————————————SUBMIT ROUTE FOR MANUAL INPUT————————————'''
@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    form = ParameterForm(request.form)
    if form.validate_on_submit():
        # print('parameter form validated!')

        for fieldname, value in form.data.items():
            #CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
            if fieldname == "dist_unit" or "flag" in fieldname or "csrf_token" in fieldname:
                if value == 'mas':
                    session['dist'] = int(1 / (form.dist.data / 1000))
                if value == 'null':
                    which_flux = fieldname[0:2]
                    session[which_flux] = 'null'
                    session[f'{which_flux}_err'] = 'null'
            else:
                # print(f'form key: {fieldname}, value: {value}')
                session[fieldname] = float(value)
        return redirect(url_for('main.return_results'))
    else:
        flash('Whoops, something went wrong. Please check your inputs and try again!', 'danger')
        return redirect(url_for('main.homepage'))



'''————————————SUBMIT ROUTE FOR RESULTS————————————'''
@main.route('/results', methods=['GET', 'POST'])
def return_results():
    parameter_form = StarNameParametersForm()
    name_form = StarNameForm()
    position_form = PositionForm()

    autofill_data = db.mast_galex_times.distinct('target')

    choices = json.loads(session['modal_choices'])
    for key, val in choices.items():
        radio_input = getattr(parameter_form, key)
        radio_input.choices.insert(0, (val, val))
    

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
        # print('CORRECTED FLUXES')
        # print(session)

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{session["model_subtype"].lower()}_grid'
        if model_collection not in db.list_collection_names():
            return redirect(url_for('main.error', msg=f'The grid for model subtype {session["model_subtype"]} is currently unavailable. Currently available subtypes: M0, M3, M4, M6. Please contact us with your stellar parameters and returned subtype if you think this is incorrect.'))
        
        # STEP 5: Do chi squared test between all models within selected subgrid and corrected observation ** this is on models with subtracted photospheric flux
        models_with_chi_squared = list(get_models_with_chi_squared(session, model_collection))
        # print(models_with_chi_squared[:5])

        models_with_lowest_fuv = list(get_models_with_lowest_fuv(session, model_collection))
        # print('FUV ONLY')
        # print(models_with_lowest_fuv[:5])

        '''————————————————————'''
        # TODO 
        # if no models within limits, check for FUV and NUV chi squared values
        # if chi squared FUV < chi squared NUV, return minimum chi squared of both added
        # ONLY looking at models that have FUV x^2 < NUV x^2
        '''————————————————————'''

        # STEP 6: Find all matches in model grid within upper and lower limits of galex fluxes
        models_in_limits = list(get_models_within_limits(session, model_collection, models_with_chi_squared))

        test_filepath = os.path.abspath(f"euv_spectra_app/fits_files/M0/M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits")
        test_filename = "M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits"

        # TODO return from lowest chi squared -> highest
        # TODO return euv flux as <euv_flux> +/- difference from model
        
        if len(list(models_in_limits)) == 0:
            # STEP 7.1: If there are no models found within limits, return model with lowest chi squared value
            # print('Nothing found within limits, MODEL W CHI SQUARED')
            # print(models_with_chi_squared[0])

            #STEP 8.1: Read FITS file from matching model and create graph from data
            filename = models_with_chi_squared[0]['fits_filename']
            filepath = os.path.abspath(f"euv_spectra_app/fits_files/{session['model_subtype']}/{filename}")

            if os.path.exists(filepath) == False:
                flash('EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger')
                filepath = test_filepath
                filename = test_filename

            data = [{'chi_squared': models_with_chi_squared[0]['chi_squared'], 'fuv': models_with_chi_squared[0]['fuv'], 'nuv': models_with_chi_squared[0]['nuv']}]

            plotly_fig = create_plotly_graph([filepath], data)
            graphJSON = json.dumps(plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)

            flash('No results found within upper and lower limits of UV fluxes. Returning document with nearest chi squared value.', 'warning')
            return render_template('result.html', subtype=matching_subtype, star_name_parameters_form=parameter_form, name_form=name_form, position_form=position_form, targets=autofill_data, graphJSON=graphJSON, files=[filename])
        else:
            # STEP 7.2: If there are models found within limits, map the id's to the models with chi squared
            # print(f'MODELS WITHIN LIMITS: {len(list(models_in_limits))}')
            # for doc in models_in_limits:
            #     print(doc)

            results = []
            for x in models_in_limits:
                for y in models_with_chi_squared:
                    if x['_id'] == y['_id']:
                        results.append(y)

            #STEP 8.2: Read all FITS files from matching models and create graph from data
            filenames = []
            filepaths = []
            data = []
            for doc in results:
                # print('DOC')
                # print(doc)
                filepath = os.path.abspath(f"euv_spectra_app/fits_files/{session['model_subtype']}/{doc['fits_filename']}")
                if os.path.exists(filepath):
                    filenames.append(doc['fits_filename'])
                    filepaths.append(filepath)
                    file_data = {
                        'chi_squared': doc['chi_squared'],
                        'fuv': doc['fuv'],
                        'nuv': doc['nuv']
                    }
                    data.append(file_data)
                else:
                    file_data = {
                        'chi_squared': doc['chi_squared'],
                        'fuv': doc['fuv'],
                        'nuv': doc['nuv']
                    }
                    data.append(file_data)
                    filepaths.append(test_filepath)
                    filenames.append(test_filename)
                    flash('EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger')
            
            plotly_fig = create_plotly_graph(filepaths, data)
            graphJSON = json.dumps(plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)
            flash(f'{len(list(models_in_limits))} results found within your submitted parameters', 'success')
            return render_template('result.html', subtype=matching_subtype, star_name_parameters_form=parameter_form, name_form=name_form, position_form=position_form, targets=autofill_data, graphJSON=graphJSON, files=filenames)
    else:
        flash('Submit the required data to view this page.', 'warning')
        return redirect(url_for('main.homepage'))


@app.route('/check-directory/<filename>')
def check_directory(filename):
    downloads = os.path.join(current_app.root_path, app.config['FITS_FOLDER'], session['model_subtype'])
    if os.path.exists(os.path.join(downloads, filename)):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})


@app.route('/download/<filename>', methods=['GET', 'POST'])
def download(filename):
    downloads = os.path.join(current_app.root_path, app.config['FITS_FOLDER'], session['model_subtype'])
    if not os.path.exists(os.path.join(downloads, filename)):
        flash('File is not available to download because it does not exist yet!')
    return send_from_directory(downloads, filename, as_attachment=True, download_name=filename)




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

'''————————————Acknowledgements PAGE————————————'''
@main.route('/acknowledgements', methods=['GET'])
def acknowledgements():
    return render_template('acknowledgements.html')
    



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
        # print(form.errors)
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

@main.app_errorhandler(503)
def internal_error(e):
    session['modal_show'] = False
    return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (503)', contact_form=ContactForm()), 503

@main.app_errorhandler(404)
def page_not_found(e):
    session['modal_show'] = False
    return render_template('error.html', error_msg='Page not found!', contact_form=ContactForm()), 404
