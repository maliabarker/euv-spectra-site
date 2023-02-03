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
from euv_spectra_app.helpers_dbqueries import find_matching_subtype, find_matching_photosphere, get_models_with_chi_squared, get_models_within_limits, get_models_with_weighted_fuv, get_flux_ratios

main = Blueprint("main", __name__)


def to_json(obj):
    # Serialize the object into a JSON formatted string
    return json.dumps(obj.__dict__)


def from_json(json_str):
    # Deserialize the JSON formatted string back into an object
    data = json.loads(json_str)
    target = StellarTarget(data["search_input"], data["search_format"])
    for key, value in data.items():
        setattr(target, key, value)
    return target


@main.context_processor
def inject_form():
    return dict(contact_form=ContactForm())


@main.before_request
def make_session_permanent():
    """Initialize session."""
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=20)
    if not session.get('modal_show'):
        session['modal_show'] = False


@main.route('/', methods=['GET', 'POST'])
def homepage():
    """Home and submit route for search bar forms."""
    session['modal_show'] = False

    manual_form = ManualForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    modal_form = ModalForm()
    autofill_data = db.mast_galex_times.distinct('target')

    if request.method == 'POST':
        if position_form.validate_on_submit():
            # Home position form
            print('position form validated!')
            stellar_target = StellarTarget(
                position_form.coords.data, 'position')
            stellar_target.search_dbs()

        elif name_form.validate_on_submit():
            # Home name form
            print(f'name form validated!')
            stellar_target = StellarTarget(name_form.star_name.data, 'name')
            stellar_target.search_dbs()

        if hasattr(stellar_target, 'modal_error_msg'):
            # check if there were any errors returned from searching databases
            if 'GALEX error:' in stellar_target.modal_error_msg:
                flash(stellar_target.modal_error_msg, 'warning')
            else:
                return redirect(url_for('main.error', msg=stellar_target.modal_error_msg))

        for attribute in vars(stellar_target):
            # add the data returned from queries to the model form object
            if hasattr(modal_form, attribute):
                radio_input = getattr(modal_form, attribute)
                attribute_value = getattr(stellar_target, attribute)
                radio_input.choices.insert(
                    0, (attribute_value, attribute_value))

        # store the object as a json variable for persistence
        session['stellar_target'] = to_json(stellar_target)
        session['modal_show'] = True
        return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, targets=autofill_data, stellar_target=stellar_target)

    flash('Website is under development. Files are not available for use yet. For testing purposes, try out object GJ 338 B.', 'warning')
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, targets=autofill_data)


@main.route('/modal-submit', methods=['GET', 'POST'])
def submit_modal_form():
    """Submit route for modal form."""
    manual_form = ManualForm()
    name_form = StarNameForm()
    position_form = PositionForm()
    modal_form = ModalForm()
    autofill_data = db.mast_galex_times.distinct('target')

    # Retrieve the JSON formatted string from the session
    target_json = session.get('stellar_target')
    # Deserialize the JSON formatted string back into an object
    stellar_target = from_json(target_json)
    # Populate the modal form with data from object
    for attribute in vars(stellar_target):
        if hasattr(modal_form, attribute):
            radio_input = getattr(modal_form, attribute)
            attribute_value = getattr(stellar_target, attribute)
            radio_input.choices.insert(0, (attribute_value, attribute_value))
    modal_form.populate_obj(request.form)

    if request.method == 'POST':
        if modal_form.validate_on_submit():
            for field in modal_form:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' in field.name and field.data != None:
                    # if a manual parameter is submitted, add that data to the object
                    print('MANUAL DETECTED')
                    unmanual_field = field.name.replace('manual_', '')
                    setattr(stellar_target, unmanual_field, float(field.data))
                    print(vars(stellar_target))
            session['stellar_target'] = to_json(stellar_target)
            return redirect(url_for('main.return_results'))
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, targets=autofill_data, stellar_target=stellar_target)


@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    """Submit route for manual form."""
    form = ManualForm(request.form)
    if form.validate_on_submit():
        for fieldname, value in form.data.items():
            # CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
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


@main.route('/results', methods=['GET', 'POST'])
def return_results():
    """Submit route for results."""
    modal_form = ModalForm()
    name_form = StarNameForm()
    position_form = PositionForm()

    # Retrieve the JSON formatted string from the session
    target_json = session.get('stellar_target')
    # Deserialize the JSON formatted string back into an object
    stellar_target = from_json(target_json)
    # Populate the modal form with data from object
    for attribute in vars(stellar_target):
        if hasattr(modal_form, attribute):
            radio_input = getattr(modal_form, attribute)
            attribute_value = getattr(stellar_target, attribute)
            radio_input.choices.insert(0, (attribute_value, attribute_value))

    autofill_data = db.mast_galex_times.distinct('target')

    # check if required data is avaialable for use before continuing
    if hasattr(stellar_target, 'teff') and hasattr(stellar_target, 'logg') and hasattr(stellar_target, 'mass') and hasattr(stellar_target, 'rad') and hasattr(stellar_target, 'dist') and hasattr(stellar_target, 'fuv') and hasattr(stellar_target, 'nuv'):
        '''———————————FOR TESTING PURPOSES (Test file)——————————'''
        test_filepath = os.path.abspath(
            f"euv_spectra_app/fits_files/M0/M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits")
        test_filename = "M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits"

        # STEP 1: Search the model_parameter_grid collection to find closest matching subtype
        matching_subtype = find_matching_subtype(
            stellar_target.teff, stellar_target.logg, stellar_target.mass)
        stellar_target.model_subtype = matching_subtype['model']

        # STEP 2: Find closest matching photosphere model and get flux values
        matching_photospheric_flux = find_matching_photosphere(
            stellar_target.teff, stellar_target.logg)

        # STEP 3: Convert, scale, and subtract photospheric contribution from fluxes
        nuv_obj = GalexFlux(stellar_target.nuv, stellar_target.nuv_err,
                            matching_photospheric_flux['nuv'], stellar_target.dist, stellar_target.rad, wv=2274.4)
        fuv_obj = GalexFlux(stellar_target.fuv, stellar_target.fuv_err,
                            matching_photospheric_flux['fuv'], stellar_target.dist, stellar_target.rad, wv=1542.3)

        stellar_target.corrected_nuv = nuv_obj.return_new_flux()
        stellar_target.corrected_nuv_err = nuv_obj.return_new_err()
        stellar_target.corrected_fuv = fuv_obj.return_new_flux()
        stellar_target.corrected_fuv_err = fuv_obj.return_new_err()

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{stellar_target.model_subtype.lower()}_grid'
        if model_collection not in db.list_collection_names():
            return redirect(url_for('main.error', msg=f'The grid for model subtype {stellar_target.model_subtype} is currently unavailable. Currently available subtypes: M0, M3, M4, M6. \nPlease contact us with your stellar parameters and returned subtype if you think this is incorrect.'))

        # STEP 5: Do chi squared test between all models within selected subgrid and corrected observation
        models_with_chi_squared = list(get_models_with_chi_squared(
            stellar_target.corrected_nuv, stellar_target.corrected_fuv, model_collection))
        # STEP 6: Find all matches in model grid within upper and lower limits of galex fluxes
        models_in_limits = list(get_models_within_limits(stellar_target.corrected_nuv, stellar_target.corrected_fuv,
                                stellar_target.corrected_nuv_err, stellar_target.corrected_fuv_err, model_collection))

        if len(list(models_in_limits)) == 0:
            # STEP 7.1: If there are no models found within limits, return models ONLY with FUV < NUV, return with chi squared values
            models_weighted = get_models_with_weighted_fuv(
                stellar_target.corrected_nuv, stellar_target.corrected_fuv, model_collection)

            print(models_weighted)

            # STEP 8.1: Read FITS file from matching model and create graph from data
            filename = models_weighted[0]['fits_filename']
            filepath = os.path.abspath(
                f"euv_spectra_app/fits_files/{stellar_target.model_subtype}/{filename}")

            # flux_ratios = list(get_flux_ratios(session, model_collection))
            # print(flux_ratios[:5])
            # for i in flux_ratios:
            #     flux_ratio_chi_sqaured =

            '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
            if os.path.exists(filepath) == False:
                flash('EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger')
                filepath = test_filepath
                filename = test_filename

            data = [{'chi_squared': models_with_chi_squared[0]['chi_squared'],
                     'fuv': models_with_chi_squared[0]['fuv'], 'nuv': models_with_chi_squared[0]['nuv']}]
            plotly_fig = create_plotly_graph([filepath], data)
            graphJSON = json.dumps(
                plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)

            flash('No results found within upper and lower limits of UV fluxes. Returning document with nearest chi squared value.', 'warning')
            return render_template('result.html', subtype=matching_subtype, modal_form=modal_form, name_form=name_form, position_form=position_form, targets=autofill_data, graphJSON=graphJSON, files=[filename], stellar_target=stellar_target)
        else:
            # STEP 7.2: If there are models found within limits, map the id's to the models with chi squared
            results = []
            for x in models_in_limits:
                for y in models_with_chi_squared:
                    if x['_id'] == y['_id']:
                        results.append(y)

            # STEP 8.2: Read all FITS files from matching models and create graph from data
            filenames = []
            filepaths = []
            data = []
            for doc in results:
                # print('DOC')
                # print(doc)
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{session['model_subtype']}/{doc['fits_filename']}")
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
                    '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                    file_data = {
                        'chi_squared': doc['chi_squared'],
                        'fuv': doc['fuv'],
                        'nuv': doc['nuv']
                    }
                    data.append(file_data)
                    filepaths.append(test_filepath)
                    filenames.append(test_filename)
                    flash(
                        'EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger')

            plotly_fig = create_plotly_graph(filepaths, data)
            graphJSON = json.dumps(
                plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)
            flash(
                f'{len(list(models_in_limits))} results found within your submitted parameters', 'success')
            return render_template('result.html', subtype=matching_subtype, modal_form=modal_form, name_form=name_form, position_form=position_form, targets=autofill_data, graphJSON=graphJSON, files=filenames, stellar_target=stellar_target)
    else:
        flash('Submit the required data to view this page.', 'warning')
        return redirect(url_for('main.homepage'))


@app.route('/check-directory/<filename>')
def check_directory(filename):
    """Checks if a FITS file exists."""
    downloads = os.path.join(
        current_app.root_path, app.config['FITS_FOLDER'], session['model_subtype'])
    if os.path.exists(os.path.join(downloads, filename)):
        return jsonify({'exists': True})
    else:
        return jsonify({'exists': False})


@app.route('/download/<filename>', methods=['GET', 'POST'])
def download(filename):
    """Downloading FITS file on button click."""
    downloads = os.path.join(
        current_app.root_path, app.config['FITS_FOLDER'], session['model_subtype'])
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
