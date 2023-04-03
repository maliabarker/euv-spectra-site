from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app, send_from_directory, jsonify
from flask_mail import Message
from datetime import timedelta
import json
import plotly
import os
import math
from euv_spectra_app.extensions import *
from euv_spectra_app.main.forms import ManualForm, StarNameForm, PositionForm, ModalForm, ContactForm
from euv_spectra_app.models import StellarObject, PegasusGrid
from euv_spectra_app.helpers import insert_data_into_form, to_json, from_json, create_plotly_graph, remove_objs_from_obj_dict
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
    manual_form = ManualForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    modal_form = ModalForm()

    if request.method == 'POST':
        if position_form.validate_on_submit():
            # Home position form
            print('position form validated!')
            stellar_object.position = position_form.coords.data
            stellar_object.get_stellar_parameters()

        elif name_form.validate_on_submit():
            # Home name form
            print(f'name form validated!')
            stellar_object.star_name = name_form.star_name.data
            stellar_object.get_stellar_parameters()

        if hasattr(stellar_object, 'modal_error_msg'):
            # check if there were any errors returned from searching databases
            return redirect(url_for('main.error', msg=stellar_object.modal_error_msg))
        
        for msg in stellar_object.modal_galex_error_msgs:
            flash(msg, 'warning')

        insert_data_into_form(stellar_object, modal_form)

        # store the object as a json variable for persistence
        session['stellar_object'] = json.dumps(to_json(stellar_object))

        session['modal_show'] = True
        return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_obj=stellar_object)

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
    target_json = session.get('stellar_object')
    # Deserialize the JSON formatted string back into an object
    stellar_object = from_json(target_json)
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)
    modal_form.populate_obj(request.form)

    if request.method == 'POST':
        if modal_form.validate_on_submit():
            for field in modal_form:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' in field.name and field.data is not None:
                    # if a manual parameter is submitted, add that data to the object
                    print('MANUAL DETECTED')
                    unmanual_field = field.name.replace('manual_', '')
                    setattr(stellar_object, unmanual_field, float(field.data))
            session['stellar_object'] = json.dumps(to_json(stellar_object))
            return redirect(url_for('main.return_results'))
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_obj=stellar_object)


@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    """Submit route for manual form."""
    if request.args.get('form') == 'extended':
        extend_form = True
    else:
        extend_form = False

    form = ManualForm(request.form)
    stellar_object = StellarObject()
    fields_not_to_include = ['dist_unit', 'fuv_flag', 'nuv_flag', 'j_band_unit', 'submit', 'csrf_token']
    flux_data = ['fuv', 'fuv_err', 'nuv', 'nuv_err', 'j_band']

    # iterate over each field in the form and set the attributes to the stellar object
    # if a flag indicates null field, make sure specified fluxes are None and run check null fluxes
    # if a flag indicates 

    if form.validate_on_submit():
        # STEP 1a: If both flags are null, return flashed error message (with form extended) 
        for fieldname, value in form.data.items():
            # CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
            if fieldname in fields_not_to_include:
                if fieldname == 'dist_unit' and value == 'mas':
                    # if the distance unit is milliarcseconds (mas) convert to parsecs
                    stellar_object.dist = int(1 / (form.dist.data / 1000))
                elif fieldname == 'j_band_unit' and value == 'flux':
                    # TODO convert flux density (ujy) to mag
                    ZEROPOINT = 1594
                    stellar_object.fluxes.j_band = -2.5 * ( math.log(form.j_band.data) - math.log(ZEROPOINT) )/ math.log(10.0)
                elif 'flag' in fieldname:
                    # if one flag is null, predict that flux using the other
                    # if the flag is saturated, predict the flux and take
                    flux = fieldname[:3]
                    flux_err = f'{flux}_err'
                    print(fieldname, 'value is', value)
                    if value == 'null':
                        print(fieldname, 'is null')
                        # set fluxes to None
                        setattr(stellar_object.fluxes, flux, None)
                        setattr(stellar_object.fluxes, flux_err, None)
                    elif value == 'saturated':
                        print(fieldname, 'is saturated')
                        flux_aper = f'{flux}_aper'
                        # set flux_aper to a large unit so it is detected as saturated
                        setattr(stellar_object.fluxes, flux_aper, 1000)
                    elif value == 'upper_limit':
                        # TODO what to do if upper limit?
                        print(fieldname, 'is upper limit')
            else:
                if fieldname in flux_data:
                    # deal with fluxes
                    print('FLUX')
                    print(fieldname, value)
                    if value is not None:
                        setattr(stellar_object.fluxes, fieldname, float(value))
                    else:
                        setattr(stellar_object.fluxes, fieldname, value)
                else:
                    print('NORMAL')
                    print(fieldname, value)
                    if value is not None:
                        setattr(stellar_object, fieldname, float(value))
                    else:
                        setattr(stellar_object, fieldname, value)
        # assign stellar object to fluxes
        stellar_object.fluxes.stellar_obj = remove_objs_from_obj_dict(stellar_object.__dict__.copy())
        
        stellar_object.fluxes.check_null_fluxes()
        print(stellar_object.fluxes.check_null_fluxes())
        stellar_object.fluxes.check_saturated_fluxes()
        print('FINAL')
        print(vars(stellar_object))
        print(vars(stellar_object.fluxes))
        session['stellar_object'] = json.dumps(to_json(stellar_object))
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
    target_json = session.get('stellar_object')
    # Deserialize the JSON formatted string back into an object
    stellar_object = from_json(target_json)
    print('STELLAR OBJ RETURN', vars(stellar_object))
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)
    # for attribute in vars(stellar_target):
    #     if hasattr(modal_form, attribute):
    #         radio_input = getattr(modal_form, attribute)
    #         attribute_value = getattr(stellar_target, attribute)
    #         radio_input.choices.insert(0, (attribute_value, attribute_value))

    # check if required data is avaialable for use before continuing
    if stellar_object.can_query_pegasus():
        '''———————————FOR TESTING PURPOSES (Test file)——————————'''
        # original test filename is M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits
        test_filepaths = [
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/original_test.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test.fits")
        ]

        # STEP 1: Prepare GALEX fluxes for searching the grid
        stellar_object.fluxes.convert_scale_photosphere_subtract_fluxes()

        # STEP 2: Create new PegasusGrid object and insert the stellar object with corrected fluxes
        pegasus = PegasusGrid(stellar_object)

        # STEP 3: Search the model_parameter_grid collection to find closest matching subtype
        subtype = pegasus.query_pegasus_subtype()
        stellar_object.model_subtype = subtype['model']
        print('SUBTYPE', stellar_object.model_subtype)

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{stellar_object.model_subtype.lower()}_grid'
        if model_collection not in db.list_collection_names():
            return redirect(url_for('main.error', msg=f'The grid for model subtype {stellar_object.model_subtype} is currently unavailable. Currently available subtypes: M0, M3, M4, M6. \nPlease contact us with your stellar parameters and returned subtype if you think this is incorrect.'))

        # STEP 5: Do chi squared test between all models within selected subgrid and corrected observation
        models_with_chi_squared = pegasus.query_pegasus_chi_square()

        # STEP 6: Find all matches in model grid within upper and lower limits of galex fluxes
        models_in_limits = pegasus.query_pegasus_models_in_limits()
        if len(models_in_limits) == 0:
            model_ratios = pegasus.query_pegasus_flux_ratio()

            # STEP 7.1: If there are no models found within limits, return models ONLY with FUV < NUV, return with chi squared values
            models_weighted = pegasus.query_pegasus_weighted_fuv()

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
                f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{filename}")

            '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
            if os.path.exists(filepath) == False:
                flash('EUV data not available yet, using test data for viewing purposes.\
                      Please contact us for more information.', 'danger')
                filepath = test_filepaths[0]

            plotly_fig = create_plotly_graph([filepath])
            graphJSON = json.dumps(
                plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)

            session['stellar_target'] = json.dumps(to_json(stellar_object))
            return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_obj=stellar_object, matching_models=matching_models)
        else:
            flash(f'{len(models_in_limits)} results found within your\
                 submitted parameters', 'success')
            # STEP 7.2: If there are models found within limits, map the id's to the models with chi squared
            # STEP 8.2: Read all FITS files from matching models and create graph from data
            filepaths = []
            for doc in models_in_limits:
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{doc['fits_filename']}")
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
            session['stellar_target'] = json.dumps(to_json(stellar_object))
            return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_obj=stellar_object, matching_models=models_in_limits)
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
    show_nexsci_error_msg = False
    if 'NExSci' in msg:
        show_nexsci_error_msg = True
    session['modal_show'] = False
    return render_template('error.html', error_msg=msg, manual_form_error_msg=show_nexsci_error_msg)


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
