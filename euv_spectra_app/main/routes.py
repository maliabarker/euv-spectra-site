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

        if hasattr(stellar_object, 'modal_page_error_msg'):
            # check if there were any errors returned from searching databases
            return redirect(url_for('main.error', msg=stellar_object.modal_page_error_msg))
        for msg in stellar_object.modal_error_msgs:
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
    fields_not_to_include = ['dist_unit', 'fuv_flag', 'nuv_flag', 'submit', 'csrf_token']
    flux_data = ['fuv', 'fuv_err', 'nuv', 'nuv_err']

    # iterate over each field in the form and set the attributes to the stellar object
    if form.validate_on_submit():
        # STEP 1a: If both flags are null, return flashed error message (with form extended) 
        for fieldname, value in form.data.items():
            if fieldname in fields_not_to_include:
                # Deal with the fields not to include 
                # (mostly unit checking and conversions and flag functionalities)
                if fieldname == 'dist_unit' and value == 'mas':
                    # CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
                    # if the distance unit is milliarcseconds (mas) convert to parsecs
                    stellar_object.dist = int(1 / (form.dist.data / 1000))
                elif 'flag' in fieldname:
                    flux = fieldname[:3]
                    flux_err = f'{flux}_err'
                    if value == 'null':
                        # if one flag is null, set fluxes to None so they can be 
                        # predicted when predict function is run later
                        print(fieldname, 'is null')
                        setattr(stellar_object.fluxes, flux, None)
                        setattr(stellar_object.fluxes, flux_err, None)
                    elif value == 'saturated':
                        # if the flag is saturated, set flux_is_saturated to True 
                        # and assign the saturated flux value so they can be dealt 
                        # with in check saturated flux function later on
                        print(fieldname, 'is saturated')
                        flux_saturated = f'{flux}_saturated'
                        flux_is_saturated = f'{flux}_is_saturated'
                        form_attr = getattr(form, flux)
                        setattr(stellar_object.fluxes, flux_saturated, float(form_attr.data))
                        setattr(stellar_object.fluxes, flux_is_saturated, True)
                    elif value == 'upper_limit':
                        # if the flag is upper limit, set flux_is_upper_limit to True 
                        # and assign the upper limit flux value so they can be dealt 
                        # with in check upper limit fluxes function later on
                        print(fieldname, 'is upper limit')
                        flux_upper_limit = f'{flux}_upper_limit'
                        flux_is_upper_limit = f'{flux}_is_upper_limit'
                        form_attr = getattr(form, flux)
                        setattr(stellar_object.fluxes, flux_upper_limit, float(form_attr.data))
                        setattr(stellar_object.fluxes, flux_is_upper_limit, True)
            else:
                # Add all fields to include to the stellar object
                if fieldname in flux_data:
                    # If the field is a flux value, add it to the stellar_object.fluxes object
                    if value is not None:
                        setattr(stellar_object.fluxes, fieldname, float(value))
                    else:
                        setattr(stellar_object.fluxes, fieldname, value)
                else:
                    if value is not None:
                        setattr(stellar_object, fieldname, float(value))
                    else:
                        setattr(stellar_object, fieldname, value)
        print('SETTING STELLAR SUBTYPE')
        stellar_object.get_stellar_subtype()
        # remove any objects within the stellar object and assign it to fluxes
        stellar_object.fluxes.stellar_obj = remove_objs_from_obj_dict(stellar_object.__dict__.copy())
        # run the check null, saturated, and upper limits fluxes
        print('RUNNING NULL FLUX STUFF')
        stellar_object.fluxes.check_null_fluxes()
        stellar_object.fluxes.check_saturated_fluxes()
        stellar_object.fluxes.check_upper_limit_fluxes()
        print('FINAL')
        print(vars(stellar_object))
        print(vars(stellar_object.fluxes))
        # store stellar object is session as json
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
    print('STELLAR OBJ RETURN', vars(stellar_object), vars(stellar_object.fluxes))
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)
    # STEP 1: Prepare GALEX fluxes for searching the grid
    stellar_object.fluxes.convert_scale_photosphere_subtract_fluxes()

    # STEP 1: check if all stellar intrinstic parameters are available to start querying pegasus
    if stellar_object.has_all_stellar_parameters():
        print('HAS ALL STELLAR PARAMETERS, CONTINUING')
        '''———————————FOR TESTING PURPOSES (Test file)——————————'''
        # original test filename is M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits
        test_filepaths = [
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/original_test.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_0.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_1.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_2.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_3.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_4.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_5.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_6.fits"),
            os.path.abspath(
                f"euv_spectra_app/fits_files/test/new_test_7.fits")
        ]
        """———————————END TEST FILE DATA——————————"""
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

        saturated_models = []
        upper_limit_models = []
        normal_models = []
        plot_data = {}
        filepaths = []
        using_test_data = False
        model_index = 0

        # STEP 5: Check for saturated fluxes and do special saturated grid search w/ flags
        if stellar_object.has_saturated_fluxes():
            print('HAS SATURATED VALUES, CONTINUING')
            # run special saturated flux search and flag with option a, don't run normal search
            if stellar_object.fluxes.fuv_is_saturated:
                # add the saturated fuv value to be plotted
                plot_data['galex_fuv_saturated'] = {'name': 'GALEX Processed FUV (Saturated)',
                                                    'flux_density': stellar_object.fluxes.processed_fuv_saturated,
                                                    'wavelength': 1542,
                                                    'flag': 'saturated'}
                # keep track of nuv_err for multiplying error bars if needed
                nuv_err = stellar_object.fluxes.processed_nuv_err
                saturated_models = pegasus.query_pegasus_saturated_fuv()
                if len(saturated_models) == 0:
                    # if nothing found in the first query, grow NUV error bars by 3 and try again
                    stellar_object.fluxes.processed_nuv_err = nuv_err * 3
                    saturated_models = pegasus.query_pegasus_saturated_fuv()
                if len(saturated_models) == 0:
                    # if nothing found in the first query, grow NUV error bars by 5 and try again
                    stellar_object.fluxes.processed_nuv_err = nuv_err * 5
                    saturated_models = pegasus.query_pegasus_saturated_fuv()
            elif stellar_object.fluxes.nuv_is_saturated:
                plot_data['galex_nuv_saturated'] = {'name': 'GALEX Processed NUV (Saturated)',
                                                    'flux_density': stellar_object.fluxes.processed_nuv_saturated,
                                                    'wavelength': 2315,
                                                    'flag': 'saturated'}
                # keep track of fuv_err for multiplying error bars if needed
                fuv_err = stellar_object.fluxes.processed_fuv_err
                saturated_models = pegasus.query_pegasus_saturated_nuv()
                if len(saturated_models) == 0:
                    # if nothing found in the first query, grow FUV error bars by 3 and try again
                    stellar_object.fluxes.processed_fuv_err = fuv_err * 3
                    saturated_models = pegasus.query_pegasus_saturated_nuv()
                if len(saturated_models) == 0:
                    # if nothing found in the first query, grow NUV error bars by 5 and try again
                    stellar_object.fluxes.processed_fuv_err = fuv_err * 5
                    saturated_models = pegasus.query_pegasus_saturated_nuv()
            
            for doc in saturated_models:
                # for each matching model that comes back, get the filepath
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{doc['fits_filename']}")
                key = f'model_{model_index}'
                plot_data[key] = {'index': model_index,
                                  'nuv': doc['nuv'],
                                  'fuv': doc['fuv'],
                                  'euv': doc['euv'],
                                  'flag': 'Saturated Option A'}
                model_index += 1
                if os.path.exists(filepath):
                    # if the filepath exists, append the data with appropriate flags to plot data
                    filepaths.append(filepath)
                    plot_data[key]['filepath'] = filepath
                else:
                    # else if the filepath doesn't exist, append dat with appropriate flags and a test file
                    '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                    i = list(saturated_models).index(doc)
                    filepaths.append(test_filepaths[i])
                    plot_data[key]['filepath'] = test_filepaths[i]
                    # set using test data to True so test flash message will be sent to return template
                    using_test_data = True
        
        # STEP 6: Check for upper limit fluxes and do special upper limit grid search w/ flags
        if stellar_object.has_upper_limit_fluxes():
            print('HAS UPPER LIMIT VALUES, CONTINUING')
            # run special upper limit flux search and flag with option a, don't run normal search
            if stellar_object.fluxes.fuv_is_upper_limit:
                # add the upper limit fuv value to be plotted
                plot_data['galex_fuv_upper_limit'] = {'name': 'GALEX Processed FUV (Upper Limit)',
                                                      'flux_density': stellar_object.fluxes.processed_fuv_upper_limit,
                                                      'wavelength': 1542,
                                                      'flag': 'upper_limit'}
                # keep track of nuv_err for multiplying error bars if needed
                nuv_err = stellar_object.fluxes.processed_nuv_err
                upper_limit_models = pegasus.query_pegasus_upper_limit_fuv()
                if len(upper_limit_models) == 0:
                    print('No upper limit models found in first run, trying again (*3)')
                    # if nothing found in the first query, grow NUV error bars by 3 and try again
                    stellar_object.fluxes.processed_nuv_err = nuv_err * 3
                    upper_limit_models = pegasus.query_pegasus_upper_limit_fuv()
                if len(upper_limit_models) == 0:
                    print('No upper limit models found in first run, trying again (*5)')
                    # if nothing found in the first query, grow NUV error bars by 5 and try again
                    stellar_object.fluxes.processed_nuv_err = nuv_err * 5
                    upper_limit_models = pegasus.query_pegasus_upper_limit_fuv()
            elif stellar_object.fluxes.nuv_is_upper_limit:
                plot_data['galex_nuv_upper_limit'] = {'name': 'GALEX Processed NUV (Upper Limit)',
                                                      'flux_density': stellar_object.fluxes.processed_nuv_upper_limit,
                                                      'wavelength': 2315,
                                                      'flag': 'upper_limit'}
                # keep track of fuv_err for multiplying error bars if needed
                fuv_err = stellar_object.fluxes.processed_fuv_err
                upper_limit_models = pegasus.query_pegasus_upper_limit_nuv()
                print('widyqgoefuyqeofyiughq 4pnirulhn1pci4rnxh43o;')
                print('BEEP BOOP')
                print(len(upper_limit_models))
                print(upper_limit_models)
                if len(upper_limit_models) == 0:
                    # if nothing found in the first query, grow FUV error bars by 3 and try again
                    stellar_object.fluxes.processed_fuv_err = fuv_err * 3
                    upper_limit_models = pegasus.query_pegasus_upper_limit_nuv()
                if len(upper_limit_models) == 0:
                    # if nothing found in the first query, grow NUV error bars by 5 and try again
                    stellar_object.fluxes.processed_fuv_err = fuv_err * 5
                    upper_limit_models = pegasus.query_pegasus_upper_limit_nuv()
            for doc in upper_limit_models:
                # for each matching model that comes back, get the filepath
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{doc['fits_filename']}")
                key = f'model_{model_index}'
                plot_data[key] = {'index': model_index,
                                  'nuv': doc['nuv'],
                                  'fuv': doc['fuv'],
                                  'euv': doc['euv'],
                                  'flag': 'Upper Limit Option A'}
                model_index += 1
                if os.path.exists(filepath):
                    # if the filepath exists, append the data with appropriate flags to plot data
                    filepaths.append(filepath)
                    plot_data[key]['filepath'] = filepath
                else:
                    # else if the filepath doesn't exist, append dat with appropriate flags and a test file
                    '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                    i = list(upper_limit_models).index(doc)
                    filepaths.append(test_filepaths[i])
                    plot_data[key]['filepath'] = test_filepaths[i]
                    # set using test data to True so test flash message will be sent to return template
                    using_test_data = True

        # STEP 7: Check that all normal and processed fluxes exist and do grid search on them
        if stellar_object.has_all_processed_fluxes():
            print('HAS ALL PROCESSED FLUXES, CONTINUING')
            # STEP 8: Do chi squared test between all models within selected subgrid and corrected observation
            models_with_chi_squared = pegasus.query_pegasus_chi_square()
            # STEP 9: Find all matches in model grid within upper and lower limits of galex fluxes
            models_in_limits = pegasus.query_pegasus_models_in_limits()
            if len(models_in_limits) == 0:
                # model_ratios = pegasus.query_pegasus_flux_ratio()
                # STEP 9A.1: If there are no models found within limits, return models ONLY with FUV < NUV, return with chi squared values
                models_weighted = pegasus.query_pegasus_weighted_fuv()
                # STEP 9A.2: Check if there are any results from weighted search
                if len(models_weighted) == 0:
                    # STEP 9A.3: if no weighted results, just use model with lowest chi squared
                    flash('No results found within upper and lower limits of UV fluxes. No model found\
                        with a close FUV match. Returning model with lowest chi-square value.', 'warning')
                    filename = models_with_chi_squared[0]['fits_filename']
                    normal_models = [models_with_chi_squared[0]]
                else:
                    # STEP 9A.4: if there are weighted results, use those
                    flash('No results found within upper and lower limits of UV fluxes.\
                        Returning document with nearest chi squared value weighted towards the FUV.', 'warning')
                    filename = models_weighted[0]['fits_filename']
                    normal_models = [models_weighted[0]]
                # STEP 9A.5: Read FITS file from matching model and add data to plot_data dictionary
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{filename}")
                '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                if os.path.exists(filepath) == False:
                    # STEP 9A.6 If the filepath does not exist, use test data and put using_test_data to True
                    filepath = test_filepaths[0]
                    using_test_data = True
                filepaths.append(filepath)
                key = f'model_{model_index}'
                plot_data[key] = {'index': model_index,
                                    'filepath': filepath,
                                    'nuv': normal_models[0]['nuv'],
                                    'fuv': normal_models[0]['fuv'],
                                    'euv': normal_models[0]['euv']}
                model_index += 1
                if stellar_object.has_saturated_fluxes():
                    # STEP 9A.7: If there are saturated fluxes, this will be option B, add proper flag
                    plot_data[key]['flag'] = 'Saturated Option B'
                elif stellar_object.has_upper_limit_fluxes():
                    # STEP 9A.8: If there are upper limit fluxes, this will be option B, add proper flag
                    plot_data[key]['flag'] = 'Upper Limit Option B'
            else:
                flash(f'{len(models_in_limits)} results found within your\
                    submitted parameters', 'success')
                # STEP 9B.1: If there are models found within limits, read all FITS files from matching 
                # models and create graph from data
                normal_models = models_in_limits
                for doc in models_in_limits:
                    # STEP 9B.2: Iterate over each model in returned models_in_limits and add each to the plot data dict
                    filepath = os.path.abspath(
                        f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{doc['fits_filename']}")
                    key = f'model_{model_index}'
                    plot_data[key] = {'index': model_index,
                                      'nuv': doc['nuv'],
                                      'fuv': doc['fuv'],
                                      'euv': doc['euv']}
                    model_index += 1
                    if stellar_object.has_saturated_fluxes():
                        # STEP 9B.3: If there are saturated fluxes, this will be option B, add proper flag
                        plot_data[key]['flag'] = 'Saturated Option B'
                    if stellar_object.has_upper_limit_fluxes():
                        # STEP 9B.4: If there are upper limit fluxes, this will be option B, add proper flag
                        plot_data[key]['flag'] = 'Upper Limit Option B'
                    if os.path.exists(filepath):
                        # STEP 9B.5: If the filepath exists, add this data to plot data
                        filepaths.append(filepath)
                        plot_data[key]['filepath'] = filepath
                    else:
                        # STEP 9B.6: If the filepath does not exists, add test data to plot data
                        '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                        i = list(models_in_limits).index(doc)
                        filepaths.append(test_filepaths[i])
                        plot_data[key]['filepath'] = test_filepaths[i]
                        using_test_data = True
            # STEP 10: Add the GALEX fuv and nuv flux densities to the plot data
            if 'galex_fuv' not in plot_data:
                plot_data['galex_fuv'] = {'name': 'GALEX Processed FUV',
                                        'flux_density': stellar_object.fluxes.processed_fuv,
                                        'flux_density_err': stellar_object.fluxes.processed_fuv_err,
                                        'wavelength': 1542}
            if 'galex_nuv' not in plot_data:
                plot_data['galex_nuv'] = {'name': 'GALEX Processed NUV',
                                        'flux_density': stellar_object.fluxes.processed_nuv,
                                        'flux_density_err': stellar_object.fluxes.processed_nuv_err,
                                        'wavelength': 2315}
        # print('PLOT DATA:', plot_data)
        # print(plot_data)
        plotly_fig = create_plotly_graph(plot_data)
        graphJSON = json.dumps(
            plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)
        session['stellar_target'] = json.dumps(to_json(stellar_object))
        if using_test_data == True:
            flash('EUV data not available yet, using test data for viewing purposes.\
                   Please contact us for more information.', 'danger')
        # print('NORMAL MODELS:', normal_models, 'SATURATED_MODLES:', saturated_models, 'UPPER LIMIT MODELS:', upper_limit_models)
        return_models = normal_models + saturated_models + upper_limit_models
        return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_obj=stellar_object, matching_models=return_models)
    else:
        flash('Missing required stellar parameters. Submit the required data to view this page.', 'danger')
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
