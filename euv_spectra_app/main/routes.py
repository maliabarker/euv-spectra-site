from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app, send_from_directory, jsonify
from flask_mail import Message
from datetime import timedelta
import json
import plotly
import os
from euv_spectra_app.extensions import *
from euv_spectra_app.main.forms import ManualForm, StarNameForm, PositionForm, ModalForm, ContactForm
from euv_spectra_app.helpers_astroquery import StellarTarget
from euv_spectra_app.helpers_flux import GalexFlux
from euv_spectra_app.helpers_graph import create_plotly_graph
from euv_spectra_app.helpers_json import to_json, from_json, from_json_new
from euv_spectra_app.helpers_dbqueries import find_matching_subtype, find_matching_photosphere, get_models_with_chi_squared, get_models_within_limits, get_models_with_weighted_fuv, get_flux_ratios
from euv_spectra_app.models import StellarObject, PegasusGrid, PhoenixModel
from euv_spectra_app.helpers import insert_data_into_form
main = Blueprint("main", __name__)


@main.context_processor
def inject_form():
    return dict(contact_form=ContactForm())


@main.before_request
def make_session_permanent():
    """Initialize session."""
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=60)
    if not session.get('modal_show'):
        session['modal_show'] = False


@main.route('/', methods=['GET', 'POST'])
def homepage():
    """Home and submit route for search bar forms."""
    if request.args.get('form') == 'extended':
        extend_form = True
    else:
        extend_form = False

    session['modal_show'] = False
    stellar_object = StellarObject()

    stellar_target = StellarTarget()

    manual_form = ManualForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    modal_form = ModalForm()

    if request.method == 'POST':
        if position_form.validate_on_submit():
            # Home position form
            print('position form validated!')
            stellar_target.position = position_form.coords.data
            stellar_target.search_dbs()

            stellar_object.position = position_form.coords.data
            stellar_object.get_stellar_parameters()
            print('——————————OLD——————————')
            print(vars(stellar_target))
            print('——————————NEW——————————')
            print(vars(stellar_object))
            print('—————————————————————')

        elif name_form.validate_on_submit():
            # Home name form
            print(f'name form validated!')
            stellar_target.star_name = name_form.star_name.data
            stellar_target.search_dbs()

            stellar_object.star_name = name_form.star_name.data
            stellar_object.get_stellar_parameters()
            print('——————————OLD——————————')
            print(vars(stellar_target))
            print('——————————NEW——————————')
            print(vars(stellar_object))
            print(vars(stellar_object.fluxes))
            print('—————————————————————')

        if hasattr(stellar_object, 'modal_error_msg'):
            # check if there were any errors returned from searching databases
            if 'GALEX' in stellar_object.modal_error_msg:
                flash(stellar_object.modal_error_msg, 'warning')
            else:
                return redirect(url_for('main.error', msg=stellar_object.modal_error_msg))
                    

        insert_data_into_form(stellar_object, modal_form)
        # if hasattr(stellar_target, 'modal_error_msg'):
        #     # check if there were any errors returned from searching databases
        #     if 'GALEX' in stellar_target.modal_error_msg:
        #         flash(stellar_target.modal_error_msg, 'warning')
        #     else:
        #         return redirect(url_for('main.error', msg=stellar_target.modal_error_msg))

        # for attribute in vars(stellar_target):
        #     # add the data returned from queries to the model form object
        #     if hasattr(modal_form, attribute):
        #         radio_input = getattr(modal_form, attribute)
        #         attribute_value = getattr(stellar_target, attribute)
        #         radio_input.choices.insert(
        #             0, (attribute_value, attribute_value))

        # store the object as a json variable for persistence
        session['stellar_target'] = json.dumps(to_json(stellar_target))
        session['stellar_object'] = json.dumps(to_json(stellar_object))

        session['modal_show'] = True
        return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_target=stellar_target)

    flash('Website is under development. Files are not available for use yet. For testing purposes, try out object GJ 338 B.', 'warning')
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, extend_form=extend_form)


@main.route('/modal-submit', methods=['GET', 'POST'])
def submit_modal_form():
    """Submit route for modal form."""
    manual_form = ManualForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    modal_form = ModalForm()

    # Retrieve the JSON formatted string from the session
    target_json = session.get('stellar_target')
    object_json = session.get('stellar_object')
    # Deserialize the JSON formatted string back into an object
    stellar_target = from_json(target_json)
    stellar_object = from_json_new(object_json)
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)

    # for attribute in vars(stellar_target):
    #     if hasattr(modal_form, attribute):
    #         radio_input = getattr(modal_form, attribute)
    #         attribute_value = getattr(stellar_target, attribute)
    #         radio_input.choices.insert(0, (attribute_value, attribute_value))
    modal_form.populate_obj(request.form)

    if request.method == 'POST':
        if modal_form.validate_on_submit():
            for field in modal_form:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' in field.name and field.data is not None:
                    # if a manual parameter is submitted, add that data to the object
                    print('MANUAL DETECTED')
                    unmanual_field = field.name.replace('manual_', '')
                    setattr(stellar_target, unmanual_field, float(field.data))
                    setattr(stellar_object, unmanual_field, float(field.data))
            session['stellar_target'] = json.dumps(to_json(stellar_target))
            session['stellar_object'] = json.dumps(to_json(stellar_object))
            return redirect(url_for('main.return_results'))
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_target=stellar_target)


@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    """Submit route for manual form."""
    if request.args.get('form') == 'extended':
        extend_form = True
    else:
        extend_form = False

    form = ManualForm(request.form)
    stellar_target = StellarTarget()
    fields_not_to_include = ['dist_unit', 'fuv_flag', 'nuv_flag', 'submit', 'csrf_token']
    if form.validate_on_submit():
        # STEP 1: Check the values of the flux flags
        fuv_flag = form.fuv_flag
        nuv_flag = form.nuv_flag
        print(form.nuv_flag, 'value is', form.nuv_flag.data)
        print(form.fuv_flag, 'value is', form.fuv_flag.data)
        # STEP 1a: If both flags are null, return flashed error message (with form extended) 
        for fieldname, value in form.data.items():
            # CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
            if fieldname in fields_not_to_include:
                if fieldname == 'dist_unit' and value == 'mas':
                    stellar_target.dist = int(1 / (form.dist.data / 1000))
                elif 'flag' in fieldname:
                    # TODO: deal with flags if they happen
                    # if one flag is null, predict that flux using the other
                    # if the flag is saturated, predict the flux and take
                    which_flux = fieldname[:3]
                    print(which_flux)
                    print(fieldname, 'value is', value)
                    # TODO: add catch for null value
                    # TODO: add catch for saturated value
                    if value == 'null':
                        print(fieldname, 'is null')
            else:
                print(fieldname, value)
                setattr(stellar_target, fieldname, float(value))
        session['stellar_target'] = json.dumps(to_json(stellar_target))
        return redirect(url_for('main.return_results'))
    else:
        flash('Whoops, something went wrong. Please check your inputs and try again!', 'danger')
        for fieldname, error_msg in form.errors.items():
            for err in error_msg:
                flash(f'{fieldname}: {err}', 'danger')
        return redirect(url_for('main.homepage', form='extended'))


@main.route('/results', methods=['GET', 'POST'])
def return_results():
    """Submit route for results."""
    modal_form = ModalForm()
    name_form = StarNameForm()
    position_form = PositionForm()

    # Retrieve the JSON formatted string from the session
    target_json = session.get('stellar_target')
    object_json = session.get('stellar_object')
    # Deserialize the JSON formatted string back into an object
    stellar_target = from_json(target_json)
    stellar_object = from_json_new(object_json)
    print('STELLAR OBJ RETURN', vars(stellar_object))
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)
    # for attribute in vars(stellar_target):
    #     if hasattr(modal_form, attribute):
    #         radio_input = getattr(modal_form, attribute)
    #         attribute_value = getattr(stellar_target, attribute)
    #         radio_input.choices.insert(0, (attribute_value, attribute_value))

    # check if required data is avaialable for use before continuing
    if hasattr(stellar_target, 'teff') and hasattr(stellar_target, 'logg') and hasattr(stellar_target, 'mass') and hasattr(stellar_target, 'rad') and hasattr(stellar_target, 'dist') and hasattr(stellar_target, 'fuv') and hasattr(stellar_target, 'nuv'):
        '''———————————FOR TESTING PURPOSES (Test file)——————————'''
        # original test filename is M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits
        test_filepaths = [
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/original_test.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test.fits")
        ]

        #prepare fluxes for searching the grid
        stellar_object.fluxes.convert_scale_photosphere_subtract_fluxes()

        # create new pegasusgrid object
        pegasus = PegasusGrid(stellar_object)

        # STEP 1: Search the model_parameter_grid collection to find closest matching subtype
        matching_subtype = find_matching_subtype(
            stellar_target.teff, stellar_target.logg, stellar_target.mass)
        stellar_target.model_subtype = matching_subtype['model']

        subtype = pegasus.query_pegasus_subtype()
        stellar_object.model_subtype = subtype['model']
        print('SUBTYPE', stellar_object.model_subtype)

        # STEP 2: Find closest matching photosphere model and get flux values
        matching_photosphere_model = find_matching_photosphere(
            stellar_target.teff, stellar_target.logg, stellar_target.mass)

        # STEP 3: Convert, scale, and subtract photospheric contribution from fluxes
        nuv_obj = GalexFlux(stellar_target.nuv, stellar_target.nuv_err,
                            matching_photosphere_model['nuv'], stellar_target.dist, stellar_target.rad, wv=2274.4)
        fuv_obj = GalexFlux(stellar_target.fuv, stellar_target.fuv_err,
                            matching_photosphere_model['fuv'], stellar_target.dist, stellar_target.rad, wv=1542.3)

        stellar_target.corrected_nuv = nuv_obj.return_new_flux()
        stellar_target.corrected_nuv_err = nuv_obj.return_new_err()
        stellar_target.corrected_fuv = fuv_obj.return_new_flux()
        stellar_target.corrected_fuv_err = fuv_obj.return_new_err()

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{stellar_target.model_subtype.lower()}_grid'
        model_collection_new = f'{stellar_object.model_subtype.lower()}_grid'
        print('MODEL COLLECTION', model_collection_new)
        if model_collection not in db.list_collection_names():
            return redirect(url_for('main.error', msg=f'The grid for model subtype {stellar_target.model_subtype} is currently unavailable. Currently available subtypes: M0, M3, M4, M6. \nPlease contact us with your stellar parameters and returned subtype if you think this is incorrect.'))

        # STEP 5: Do chi squared test between all models within selected subgrid and corrected observation
        models_with_chi_squared = list(get_models_with_chi_squared(
            stellar_target.corrected_nuv, stellar_target.corrected_fuv, model_collection))
        
        models_w_x_2 = pegasus.query_pegasus_chi_square()
        print('CHI SQUARED', models_w_x_2)
        # STEP 6: Find all matches in model grid within upper and lower limits of galex fluxes
        models_in_limits = list(get_models_within_limits(stellar_target.corrected_nuv, stellar_target.corrected_fuv,
                                stellar_target.corrected_nuv_err, stellar_target.corrected_fuv_err, model_collection))
        m_in_lims = pegasus.query_pegasus_models_in_limits()
        print('IN LIMITS', m_in_lims)
        if len(models_in_limits) == 0:
            model_ratios = list(get_flux_ratios(
                stellar_target.corrected_nuv, stellar_target.corrected_fuv, model_collection))
            model_r = pegasus.query_pegasus_flux_ratio()
            print('MODELS W RATIOS', model_r)

            # STEP 7.1: If there are no models found within limits, return models ONLY with FUV < NUV, return with chi squared values
            models_weighted = get_models_with_weighted_fuv(
                stellar_target.corrected_nuv, stellar_target.corrected_fuv, model_collection)
            model_w = pegasus.query_pegasus_weighted_fuv()
            print('MODELS WEIGTHED', model_w)

            # STEP 8.1: Check if there are any results from weighted search
            if len(models_weighted) == 0:
                # if no weighted results, just use model with lowest chi squared
                flash('No results found within upper and lower limits of UV fluxes. No model found\
                     with a close FUV match. Returning model with lowest chi-square value.', 'warning')
                filename = models_with_chi_squared[0]['fits_filename']
                matching_models = models_with_chi_squared[0]
            else:
                flash('No results found within upper and lower limits of UV fluxes.\
                      Returning document with nearest chi squared value weighted towards the FUV.', 'warning')
                filename = models_weighted[0]['fits_filename']
                matching_models = [models_weighted[0]]

            # STEP 9.1: Read FITS file from matching model and create graph from data
            filepath = os.path.abspath(
                f"euv_spectra_app/fits_files/{stellar_target.model_subtype}/{filename}")

            '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
            if os.path.exists(filepath) == False:
                flash('EUV data not available yet, using test data for viewing purposes.\
                      Please contact us for more information.', 'danger')
                filepath = test_filepaths[0]

            plotly_fig = create_plotly_graph([filepath])
            graphJSON = json.dumps(
                plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)

            session['stellar_target'] = json.dumps(to_json(stellar_target))
            return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_target=stellar_target, matching_models=matching_models)
        else:
            flash(f'{len(list(models_in_limits))} results found within your\
                 submitted parameters', 'success')
            # STEP 7.2: If there are models found within limits, map the id's to the models with chi squared
            # STEP 8.2: Read all FITS files from matching models and create graph from data
            filepaths = []
            for doc in models_in_limits:
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_target.model_subtype}/{doc['fits_filename']}")
                if os.path.exists(filepath):
                    filepaths.append(filepath)
                else:
                    '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                    i = list(models_in_limits).index(doc)
                    filepaths.append(test_filepaths[i])
                    flash('EUV data not available yet, using test data for viewing purposes.\
                        Please contact us for more information.', 'danger')

            plotly_fig = create_plotly_graph(filepaths)
            graphJSON = json.dumps(
                plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)
            session['stellar_target'] = json.dumps(to_json(stellar_target))
            return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_target=stellar_target, matching_models=list(models_in_limits))
    else:
        flash('Submit the required data to view this page.', 'warning')
        return redirect(url_for('main.homepage'))


@main.route('/check-directory/<filename>')
def check_directory(filename):
    """Checks if a FITS file exists."""
    if 'test' in filename:
        downloads = os.path.join(
            current_app.root_path, app.config['FITS_FOLDER'], 'test')
    else:
        # Retrieve the JSON formatted string from the session
        target_json = session.get('stellar_target')
        # Deserialize the JSON formatted string back into an object
        stellar_target = from_json(target_json)
        downloads = os.path.join(
            current_app.root_path, app.config['FITS_FOLDER'], stellar_target.model_subtype)
    if os.path.exists(os.path.join(downloads, filename)):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})


@main.route('/download/<filename>', methods=['GET', 'POST'])
def download(filename):
    """Downloading FITS file on button click."""
    if 'test' in filename:
        downloads = os.path.join(
            current_app.root_path, app.config['FITS_FOLDER'], 'test')
    else:
        # Retrieve the JSON formatted string from the session
        target_json = session.get('stellar_target')
        # Deserialize the JSON formatted string back into an object
        stellar_target = from_json(target_json)
        downloads = os.path.join(
            current_app.root_path, app.config['FITS_FOLDER'], stellar_target.model_subtype)
    if not os.path.exists(os.path.join(downloads, filename)):
        flash('File is not available to download because it does not exist yet!')
    return send_from_directory(downloads, filename, as_attachment=True, download_name=filename)


@main.route('/about', methods=['GET'])
def about():
    """About page."""
    return render_template('about.html')


@main.route('/faqs', methods=['GET'])
def faqs():
    """FAQs page."""
    return render_template('faqs.html')


@main.route('/all-spectra', methods=['GET'])
def index_spectra():
    """View all spectra page."""
    return render_template('index-spectra.html')


@main.route('/acknowledgements', methods=['GET'])
def acknowledgements():
    """Acknowledgments page."""
    return render_template('acknowledgements.html')


@main.route('/contact', methods=['POST'])
def send_email():
    """Submit email form and send email."""
    form = ContactForm(request.form)
    if form.validate_on_submit():
        msg = Message(form.subject.data,
                      sender=(form.name.data, form.email.data),
                      recipients=['phoenixpegasusgrid@gmail.com'],
                      body=f'FROM {form.name.data}, {form.email.data}\n MESSAGE: {form.message.data}')
        mail.send(msg)
        flash('Email sent!', 'success')
        return redirect(url_for('main.homepage'))
    else:
        flash('error', 'danger')
        return redirect(url_for('main.error', msg='Contact form unavailable at this time, please email phoenixpegasusgrid@gmail.com directly.'))


@main.route('/error/<msg>')
def error(msg):
    """Custom error page."""
    session['modal_show'] = False
    return render_template('error.html', error_msg=msg)


@main.app_errorhandler(503)
def internal_error(e):
    """503 error page."""
    session['modal_show'] = False
    return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (503)', contact_form=ContactForm()), 503


@main.app_errorhandler(404)
def page_not_found(e):
    """404 error page."""
    session['modal_show'] = False
    return render_template('error.html', error_msg='Page not found!', contact_form=ContactForm()), 404
