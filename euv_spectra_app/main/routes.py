import json
import plotly
import os
import zipfile
import io
import itertools
from flask import Blueprint, request, render_template, redirect, url_for, session, flash, current_app, jsonify, send_file, send_from_directory
from flask_mail import Message
from datetime import timedelta
from euv_spectra_app.extensions import *
from euv_spectra_app.main.forms import ManualForm, StarNameForm, PositionForm, ModalForm, ContactForm
from euv_spectra_app.models import StellarObject, PegasusGrid, FlashMessage
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
            flash(FlashMessage(msg, 'warning', 'modal'))
        insert_data_into_form(stellar_object, modal_form)

        # store the object as a json variable for persistence
        session['stellar_object'] = json.dumps(to_json(stellar_object))
        session['modal_show'] = True
        return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_obj=stellar_object)

    flash(FlashMessage('Website is under development. Files are not available for use yet. For testing purposes, try out object GJ 338 B.', 'warning', 'page'))
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
                    unmanual_field = field.name.replace('manual_', '')
                    setattr(stellar_object, unmanual_field, float(field.data))
            session['stellar_object'] = json.dumps(to_json(stellar_object))
            return redirect(url_for('main.return_results'))
    return render_template('home.html', manual_form=manual_form, name_form=name_form, position_form=position_form, modal_form=modal_form, stellar_obj=stellar_object)


@main.route('/manual-submit', methods=['POST'])
def submit_manual_form():
    """Submit route for manual form."""
    form = ManualForm(request.form)
    stellar_object = StellarObject()
    fields_not_to_include = ['dist_unit', 'fuv_flag',
                             'nuv_flag', 'fuv_unit', 'nuv_unit', 'submit', 'csrf_token']
    flux_data = ['fuv', 'fuv_err', 'nuv', 'nuv_err']

    # iterate over each field in the form and set the attributes to the stellar object
    if form.validate_on_submit():
        # STEP 1a: If both flags are null, return flashed error message (with form extended)
        for fieldname, value in form.data.items():
            if fieldname in fields_not_to_include:
                # Deal with the fields not to include
                # (mostly unit checking and conversions and flag functionalities)
                if fieldname == 'dist_unit' and value == 'mas':
                    # CHECK DISTANCE UNIT
                    # if the distance unit is milliarcseconds (mas) convert to parsecs
                    print(f'SETTING THE CONVERTED DISTANCE')
                    stellar_object.dist = int(1 / (form.dist.data / 1000))
                elif fieldname == 'fuv_unit' and value == 'mag':
                    # CHECK GALEX FUV UNIT
                    # if galex unit is in magnitude (mag), convert to flux (in microjanskies)
                    # mag(AB) → erg/s/cm^2/A
                    # FUV = ( ( (10^(mag-18.82))/-2.5 ) * (1.4*10^-15) )
                    fuv = float(form.fuv.data)
                    fuv_mag_to_flux = (
                        (pow(10, ((fuv-18.82)/-2.5))) * (1.4e-15))
                    # erg/s/cm^2/A → uJY
                    fuv_flux_to_uJy = (
                        ((fuv_mag_to_flux * pow(1542.3, 2)) / (3e-5)) * (pow(10, 6)))
                    # set fuv of stellar object fluxes to this flux
                    print(f'SETTING THE CONVERTED FUV FLUX')
                    setattr(stellar_object.fluxes, 'fuv', fuv_flux_to_uJy)
                elif fieldname == 'nuv_unit' and value == 'mag':
                    # CHECK GALEX NUV UNIT
                    # if galex unit is in magnitude (mag), convert to flux (in microjanskies)
                    nuv = float(form.nuv.data)
                    # mag(AB) → erg/s/cm^2/A
                    # NUV = ( ( (10^(mag-20.08))/-2.5 ) * (2.06*10^-16) )
                    nuv_mag_to_flux = (
                        (pow(10, ((nuv-20.08)/-2.5))) * (2.06e-16))
                    # erg/s/cm^2/A → uJY
                    nuv_flux_to_uJy = (
                        ((nuv_mag_to_flux * pow(2274.4, 2)) / (3e-5)) * (pow(10, 6)))
                    # set nuv of stellar object fluxes to this flux
                    print(f'SETTING THE CONVERTED NUV FLUX')
                    setattr(stellar_object.fluxes, 'nuv', nuv_flux_to_uJy)
                elif 'flag' in fieldname:
                    flux = fieldname[:3]
                    flux_err = f'{flux}_err'
                    if value == 'null':
                        # if one flag is null, set fluxes to None so they can be
                        # predicted when predict function is run later
                        print(f'SETTING THE {fieldname} NULL FLUX')
                        setattr(stellar_object.fluxes, flux, None)
                        setattr(stellar_object.fluxes, flux_err, None)
                    elif value == 'saturated':
                        # if the flag is saturated, set flux_is_saturated to True
                        # and assign the saturated flux value so they can be dealt
                        # with in check saturated flux function later on
                        # Also, set the actual flux value to None so it is not used
                        # as an actual detection
                        flux_saturated = f'{flux}_saturated'
                        flux_is_saturated = f'{flux}_is_saturated'
                        form_attr = getattr(form, flux)
                        print(f'SETTING THE {fieldname} SATURATED FLUX')
                        setattr(stellar_object.fluxes, flux, None)
                        setattr(stellar_object.fluxes,
                                flux_saturated, float(form_attr.data))
                        setattr(stellar_object.fluxes, flux_is_saturated, True)
                    elif value == 'upper_limit':
                        # if the flag is upper limit, set flux_is_upper_limit to True
                        # and assign the upper limit flux value so they can be dealt
                        # with in check upper limit fluxes function later on
                        flux_upper_limit = f'{flux}_upper_limit'
                        flux_is_upper_limit = f'{flux}_is_upper_limit'
                        form_attr = getattr(form, flux)
                        print(f'SETTING THE {fieldname} UPPER LIMIT FLUX')
                        setattr(stellar_object.fluxes, flux, None)
                        setattr(stellar_object.fluxes,
                                flux_upper_limit, float(form_attr.data))
                        setattr(stellar_object.fluxes,
                                flux_is_upper_limit, True)
            else:
                # Add all fields to include to the stellar object
                if fieldname in flux_data:
                    # If the field is a flux value, add it to the stellar_object.fluxes object
                    if value is not None:
                        print(f'SETTING THE {fieldname} FLUX')
                        setattr(stellar_object.fluxes, fieldname, float(value))
                    else:
                        print(f'SETTING THE {fieldname} FLUX TO NONE')
                        setattr(stellar_object.fluxes, fieldname, value)
                else:
                    if value is not None:
                        print(f'SETTING THE {fieldname}')
                        setattr(stellar_object, fieldname, float(value))
                    else:
                        print(f'SETTING THE {fieldname} TO NONE')
                        setattr(stellar_object, fieldname, value)
        stellar_object.get_stellar_subtype(
            stellar_object.teff, stellar_object.logg, stellar_object.mass)
        # remove any objects within the stellar object and assign it to fluxes
        stellar_object.fluxes.stellar_obj = remove_objs_from_obj_dict(
            stellar_object.__dict__.copy())
        # run the check null, saturated, and upper limits fluxes
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
        flash(FlashMessage('Whoops, something went wrong. Please check your inputs and try again!', 'danger', 'page'))
        for fieldname, error_msg in form.errors.items():
            for err in error_msg:
                flash(FlashMessage(f'{fieldname}: {err}', 'danger', 'page'))
        return redirect(url_for('main.homepage', form='extended'))


@main.route('/results', methods=['GET', 'POST'])
def return_results():
    """Submit route for results."""
    modal_form = ModalForm()
    name_form = StarNameForm()
    position_form = PositionForm()

    # For populating modal form with stellar object data if user wants to edit parameters
    # Retrieve the JSON formatted string from the session
    target_json = session.get('stellar_object')
    # Deserialize the JSON formatted string back into an object
    stellar_object = from_json(target_json)
    print('STELLAR OBJ RETURN', vars(stellar_object),
          vars(stellar_object.fluxes))
    # Populate the modal form with data from object
    insert_data_into_form(stellar_object, modal_form)

    # STEP 1: Prepare GALEX fluxes for searching the grid
    stellar_object.fluxes.convert_scale_photosphere_subtract_fluxes()
    # STEP 2: Check if all stellar intrinstic parameters are available to start querying pegasus
    if stellar_object.has_all_stellar_parameters():
        print('HAS ALL STELLAR PARAMETERS, CONTINUING')
        '''———————————FOR TESTING PURPOSES (Test file)——————————'''
        # original test filename is M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=4.fits
        test_filepaths = [
            os.path.abspath(f"euv_spectra_app/fits_files/test/original_test.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_0.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_1.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_2.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_3.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_4.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_5.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_6.fits"),
            os.path.abspath(f"euv_spectra_app/fits_files/test/new_test_7.fits")
        ]
        test_filepath_names = [
            "original_test.fits", "new_test.fits", "new_test_0.fits", "new_test_1.fits",
            "new_test_2.fits", "new_test_3.fits", "new_test_4.fits", "new_test_5.fits",
            "new_test_6.fits", "new_test_7.fits"
        ]
        """———————————END TEST FILE DATA——————————"""

        # STEP 2: Create new PegasusGrid object and insert the stellar object with corrected fluxes
        pegasus = PegasusGrid(stellar_object)

        # STEP 3: Search the model_parameter_grid collection to find closest matching stellar subtype
        subtype = pegasus.query_pegasus_subtype()
        stellar_object.model_subtype = subtype['model']
        print('SUBTYPE', stellar_object.model_subtype)

        # STEP 4: Check if model subtype data exists in database
        model_collection = f'{stellar_object.model_subtype.lower()}_grid'
        if model_collection not in db.list_collection_names():
            error_msg = f'The grid for model subtype {stellar_object.model_subtype} is currently unavailable. \
                          Currently available subtypes: M0, M3, M4, M6. \nPlease contact us with your stellar \
                          parameters and returned subtype if you think this is incorrect.'
            return redirect(url_for('main.error', msg=error_msg))

        # STEP 5: Instantiate the following objects
        plot_data = {}  # Dict to hold all data to plot
        using_test_data = False # Bool to determine if we are using test data
        model_index = 0  # Instantiating model index
        return_models = [] # Instantiating list to hold all returned models

        # STEP 6: Add the GALEX fluxes to plot data
        plot_data['galex_fuv'] = {'name': 'GALEX Processed FUV',
                                  'wavelength': 1542}
        plot_data['galex_nuv'] = {'name': 'GALEX Processed NUV',
                                  'wavelength': 2315}
        # GALEX FUV Data
        if stellar_object.fluxes.fuv_is_saturated:
            # plot saturated GALEX FUV flux
            plot_data['galex_fuv']['name'] += ' (Saturated)'
            plot_data['galex_fuv']['flux_density'] = stellar_object.fluxes.processed_fuv_saturated
            plot_data['galex_fuv']['flag'] = 'saturated'
        elif stellar_object.fluxes.fuv_is_upper_limit:
            # plot upper limit GALEX FUV flux
            plot_data['galex_fuv']['name'] += ' (Upper Limit)'
            plot_data['galex_fuv']['flux_density'] = stellar_object.fluxes.processed_fuv_upper_limit
            plot_data['galex_fuv']['flag'] = 'upper_limit'
        else:
            # plot normal GALEX FUV flux
            plot_data['galex_fuv']['flux_density'] = stellar_object.fluxes.processed_fuv
            if stellar_object.fluxes.fuv_err is not None:
                # if there is an error, add to GALEX FUV flux return data
                plot_data['galex_fuv']['flux_density_err'] = stellar_object.fluxes.processed_fuv_err
        # GALEX NUV Data
        if stellar_object.fluxes.nuv_is_saturated:
            # plot saturated GALEX NUV flux
            plot_data['galex_nuv']['name'] += ' (Saturated)'
            plot_data['galex_nuv']['flux_density'] = stellar_object.fluxes.processed_nuv_saturated
            plot_data['galex_nuv']['flag'] = 'saturated'
        elif stellar_object.fluxes.nuv_is_upper_limit:
            # plot upper limit GALEX NUV flux
            plot_data['galex_nuv']['name'] += ' (Upper Limit)'
            plot_data['galex_nuv']['flux_density'] = stellar_object.fluxes.processed_nuv_upper_limit
            plot_data['galex_nuv']['flag'] = 'upper_limit'
        else:
            # plot normal GALEX NUV flux
            plot_data['galex_nuv']['flux_density'] = stellar_object.fluxes.processed_nuv
            if stellar_object.fluxes.nuv_err is not None:
                # if there is an error, add to GALEX NUV flux return data
                plot_data['galex_nuv']['flux_density_err'] = stellar_object.fluxes.processed_nuv_err
        print(plot_data['galex_fuv'])
        print(plot_data['galex_nuv'])
        # STEP 7: Get all possible searchable values of FUV and NUV from the GalexFluxes object
        fuv_dict = {} # Dict to hold all FUV values
        nuv_dict = {} # Dict to hold all NUV values
        for key, val in vars(stellar_object.fluxes).items():
            if 'processed' in key: # Only use processed fluxes
                if 'fuv' in key and 'err' not in key: # Get all values of processed FUV (except error)
                    fuv_dict[key] = {'value': val} # Add the value of the flux
                    fuv_dict[key]['error'] = None # Set the error as None by default
                    if key == 'processed_fuv' and hasattr(stellar_object.fluxes, 'processed_fuv_err'):
                        # If there is an error, this means it is a normal flux. Add flag and error
                        fuv_dict[key]['error'] = stellar_object.fluxes.processed_fuv_err
                        fuv_dict[key]['flag'] = 'normal'
                    elif 'saturated' in key:
                        # If it is saturated, add flag
                        fuv_dict[key]['flag'] = 'saturated'
                    elif 'upper_limit' in key:
                        # If it is upper limit, add flag
                        fuv_dict[key]['flag'] = 'upper_limit'
                    else:
                        # If it is none of these, means it is normal flux w/o error (detection only)
                        fuv_dict[key]['flag'] = 'detection_only'
                elif 'nuv' in key and 'err' not in key: # Get all values of processed NUV (except error)
                    nuv_dict[key] = {'value': val} # Add the value of the flux
                    nuv_dict[key]['error'] = None # Set the error as None by default
                    if key == 'processed_nuv' and hasattr(stellar_object.fluxes, 'processed_nuv_err'):
                        # If there is an error, this means it is a normal flux. Add flag and error
                        nuv_dict[key]['error'] = stellar_object.fluxes.processed_nuv_err
                        nuv_dict[key]['flag'] = 'normal'
                    elif 'saturated' in key:
                        # If it is saturated, add flag
                        nuv_dict[key]['flag'] = 'saturated'
                    elif 'upper_limit' in key:
                        # If it is upper limit, add flag
                        nuv_dict[key]['flag'] = 'upper_limit'
                    else:
                        # If it is none of these, means it is normal flux w/o error (detection only)
                        nuv_dict[key]['flag'] = 'detection_only'
        print(f'FUVS: {fuv_dict}')
        print(f'NUVS: {nuv_dict}')
        # STEP 8: Get all possible combinations of fuv-nuv pairs. These are the pairs of fluxes that will be 
        # used for PEGASUS grid searches.
        fuv_keys = list(fuv_dict)
        nuv_keys = list(nuv_dict)
        key_pairs = list(itertools.product(fuv_keys, nuv_keys))
        # STEP 9: Iterate over each pair and run PEGASUS grid search on each pair
        for fuv_key, nuv_key in key_pairs:
            # STEP 9.1: Retrieve the fuv and nuv values using the keys from the dictionaries
            fuv_value = fuv_dict[fuv_key]
            nuv_value = nuv_dict[nuv_key]
            print(f'SEARCHING USING FUV: {fuv_value}, NUV:{nuv_value}')
            # STEP 9.2: Call the search_db function with the fuv and nuv values
            models = pegasus.query_model_collection(fuv_value, nuv_value)
            print(f'MODELS: {models}')
            # STEP 9.3: Do additional processing on the returned models depending on the flag
            # SATURATED/UPPER LIMIT WORK FLOW:
                # If one val is saturated/upper limit and one val is normal and no models are returned,
                # will need to increase error bars of normal flux by 3 sigma, then by 5 sigma
                # If both fluxes are an upper limit or saturated value, just return the model with the 
                # lowest chi-squared value (which will be the first model because they are already sorted)
            if (fuv_value['flag'] == 'saturated' or fuv_value['flag'] == 'upper_limit') and nuv_value['flag'] == 'normal':
                # For saturated/upper limit FUV flux and a normal NUV flux
                # _ results found within upper and lower limits of the GALEX NUV flux and upper limits of GALEX FUV (upper limit)
                if len(models) > 0:
                    flash(FlashMessage(f'{len(models)} results found within the upper and lower limits of your submitted UV fluxes.', 'success', 'page'))
                if len(models) == 0:
                    print(f'NO MODELS FOUND IN FIRST SAT SEARCH, GROWING BARS BY 3')
                    # grow nuv error bars by three
                    nuv_copy = nuv_value.copy()
                    nuv_copy['error'] = nuv_copy['error'] * 3
                    models = pegasus.query_model_collection(
                        fuv_value, nuv_copy)
                    if len(models) > 0:
                        flash(FlashMessage(f'{len(models)} results found within 3 σ of the GALEX NUV flux.', 'success', 'page'))
                if len(models) == 0:
                    print(f'NO MODELS FOUND IN FIRST SAT SEARCH, GROWING BARS BY 5')
                    # grow nuv error bars by five
                    nuv_copy = nuv_value.copy()
                    nuv_copy['error'] = nuv_copy['error'] * 5
                    models = pegasus.query_model_collection(
                        fuv_value, nuv_copy)
                    if len(models) > 0:
                        flash(FlashMessage(f'{len(models)} results found within 5 σ of the GALEX NUV flux.', 'success', 'page'))
                if len(models) == 0:
                    # if there are still no models, flash error
                    flash(FlashMessage('No models found within 5 σ of the GALEX NUV flux measurements.', 'danger', 'page'))
            elif (nuv_value['flag'] == 'saturated' or nuv_value['flag'] == 'upper_limit') and fuv_value['flag'] == 'normal':
                # For saturated/upper limit NUV flux and a normal FUV flux
                if len(models) > 0:
                    flash(FlashMessage(f'{len(models)} results found within the upper and lower limits of your submitted UV fluxes.', 'success', 'page'))
                if len(models) == 0:
                    # grow fuv error bars by three
                    print(f'NO MODELS FOUND IN FIRST UPPER LIM SEARCH, GROWING BARS BY 3')
                    fuv_copy = fuv_value.copy()
                    fuv_copy['error'] = fuv_copy['error'] * 3
                    models = pegasus.query_model_collection(
                        fuv_copy, nuv_value)
                    if len(models) > 0:
                        flash(FlashMessage(f'{len(models)} results found within 3 σ of the GALEX FUV flux.', 'success', 'page'))
                if len(models) == 0:
                    # grow fuv error bars by three
                    print(f'NO MODELS FOUND IN FIRST UPPER LIM SEARCH, GROWING BARS BY 5')
                    fuv_copy = fuv_value.copy()
                    fuv_copy['error'] = fuv_copy['error'] * 5
                    models = pegasus.query_model_collection(
                        fuv_copy, nuv_value)
                    if len(models) > 0:
                        flash(FlashMessage(f'{len(models)} results found within 5 σ of the GALEX FUV flux.', 'success', 'page'))
                if len(models) == 0:
                    # if there are still no models, flash error
                    flash(FlashMessage('No models found within 5 σ of the GALEX FUV flux measurements.', 'danger', 'page'))
            elif (fuv_value['flag'] == 'saturated' or nuv_value['flag'] == 'saturated') and (fuv_value['flag'] == 'upper_limit' or nuv_value['flag'] == 'upper_limit'):
                # return first model (lowest chi-squared value)
                flash(FlashMessage(f'{len(models)} results found within upper and lower limits of GALEX UV fluxes. Returning model with lowest chi-squared value.', 'success', 'page'))
                models = [models[0]]
            # DETECTION ONLY WORKFLOW
                # The models will be sorted by the diff_flux field, so the first model will have the closest 
                # value to the given detection. Just return the first model.
            if fuv_value['flag'] == 'detection_only' or nuv_value['flag'] == 'detection_only':
                if len(models) != 0: # Check if there are returned models first
                    models = [models[0]]
                    flash(FlashMessage('Returning closest match to GALEX UV fluxes.', 'warning', 'page'))
                else:
                    flash(FlashMessage('No results found within GALEX UV fluxes.', 'danger', 'page'))
            # NORMAL WORKFLOW
                # If no models are found within the error bars of the given fluxes,
                # search for models weighted on the FUV. If no models are returned 
                # weighted on FUV, just return models with lowest chi squared value.
            if fuv_value['flag'] == 'normal' and nuv_value['flag'] == 'normal':
                if len(models) == 0:
                    # Do chi squared test between all models within selected subgrid and corrected observation
                    models_with_chi_squared = pegasus.query_pegasus_chi_square()
                    # If there are no models found within limits, return models ONLY with FUV < NUV, return with chi squared values
                    models_weighted = pegasus.query_pegasus_weighted_fuv()
                    if len(models_weighted) > 0:
                        # If there are weighted results, use those
                        flash(FlashMessage('No results found within upper and lower limits of UV fluxes. Returning document with nearest chi squared value weighted towards the FUV.', 'warning', 'page'))
                        models = [models_weighted[0]]
                    else:
                        # If no weighted results, just use model with lowest chi squared
                        flash(FlashMessage('No results found within upper and lower limits of UV fluxes. No model found with a close FUV match. Returning model with lowest chi-square value.', 'warning', 'page'))
                        models = [models_with_chi_squared[0]]
                else:
                    flash(FlashMessage(f'{len(models)} results found within the upper and lower limits of your submitted UV fluxes.', 'success', 'page'))
            # STEP 10: After getting models for this search, we need to add each model to the plot data and 
            # add any flags the models may have.
            # Flags include:
                # If there are saturated fluxes and this is a saturated search, add saturated option A flag
                # If there are upper limit fluxes and this is a upper limit search, add upper limit option A flag
                # If there are saturated fluxes and this is a normal search, add saturated option B flag
                # If there are upper limit fluxes and this is a normal search, add upper limit option B flag
                # If there are both saturated and upper limit fluxes, add saturated and upper limit option A flag
            # STEP 10.1: Append all models to the return models list for return table
            return_models += models
            # STEP 10.2: Iterate over each model returned and add data and flag (if applicable)
            for doc in models:
                # for each matching model that comes back, get the filepath so we can check if it exists later
                filepath = os.path.abspath(
                    f"euv_spectra_app/fits_files/{stellar_object.model_subtype}/{doc['fits_filename']}")
                key = f'model_{model_index}'
                plot_data[key] = {'index': model_index, # Add index for num tracking on return page
                                  'nuv': doc['nuv'], # Add NUV flux
                                  'fuv': doc['fuv'], # Add FUV flux
                                  'euv': doc['euv']} # Add EUV flux
                model_index += 1 # After adding the model, increment the index
                # Check if the model's filepath exists, if not use a test file
                if os.path.exists(filepath):
                    # if the filepath exists, add to plot data
                    plot_data[key]['filepath'] = filepath
                else:
                    # else if the filepath doesn't exist, add a test file
                    '''——————FOR TESTING PURPOSES (if FITS file is not yet available)—————'''
                    plot_data[key]['filepath'] = test_filepaths[model_index-1]
                    # set using test data to True so test flash message will be sent to return template
                    using_test_data = True
                # Now add the flag if there is one.
                if (stellar_object.fluxes.fuv_is_saturated or stellar_object.fluxes.nuv_is_saturated) and (stellar_object.fluxes.fuv_is_upper_limit or stellar_object.fluxes.nuv_is_upper_limit):
                    # If there are both saturated and upper limit fluxes, add saturated and upper limit option A flag
                    plot_data[key]['flag'] = 'Saturated and Upper Limit Search Option A'
                elif (stellar_object.fluxes.fuv_is_saturated or stellar_object.fluxes.nuv_is_saturated):
                    # If there are saturated fluxes and this is a saturated search, add saturated option A flag
                    if (fuv_value['flag'] == 'saturated' or nuv_value['flag'] == 'saturated'):
                        plot_data[key]['flag'] = 'Saturated Search Option A'
                    # If there are saturated fluxes and this is a normal search, add saturated option B flag
                    if (fuv_value['flag'] == 'normal' and nuv_value['flag'] == 'normal'):
                        plot_data[key]['flag'] = 'Saturated Search Option B'
                elif (stellar_object.fluxes.fuv_is_upper_limit or stellar_object.fluxes.nuv_is_upper_limit):
                    # If there are upper limit fluxes and this is a upper limit search, add upper limit option A flag
                    if (fuv_value['flag'] == 'upper_limit' or nuv_value['flag'] == 'upper_limit'):
                        plot_data[key]['flag'] = 'Upper Limit Search Option A'
                    # If there are upper limit fluxes and this is a normal search, add upper limit option B flag
                    if (fuv_value['flag'] == 'normal' and nuv_value['flag'] == 'normal'):
                        plot_data[key]['flag'] = 'Upper Limit Search Option B'
        # STEP 11: Generate plot using the compiled data
        plotly_fig = create_plotly_graph(plot_data)
        graphJSON = json.dumps(
            plotly_fig, cls=plotly.utils.PlotlyJSONEncoder)
        # STEP 12: If using test data, add flash so user knows that test data is being used
        if using_test_data == True:
            flash(FlashMessage('EUV data not available yet, using test data for viewing purposes. Please contact us for more information.', 'danger', 'page'))
        session['stellar_target'] = json.dumps(to_json(stellar_object))
        print(return_models)
        return render_template('result.html', modal_form=modal_form, name_form=name_form, position_form=position_form, graphJSON=graphJSON, stellar_obj=stellar_object, matching_models=return_models, test_filepaths=test_filepath_names)
    else:
        flash(FlashMessage('Missing required stellar parameters. Submit the required data to view this page.', 'danger', 'page'))
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


@main.route('/download/<filename>/<model>', methods=['GET', 'POST'])
def download(filename, model):
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
    file_path = os.path.join(downloads, filename)
    if not os.path.exists(file_path):
        flash(FlashMessage('File is not available to download because it does not exist yet!', 'danger', 'page'))
    # Create the zip file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zipf:
        # Add the requested file to the zip
        zipf.write(file_path, filename)
        # Add the README file to the zip
        readme_path = os.path.join(
            current_app.root_path, app.config['FITS_FOLDER'], 'README.md')
        zipf.write(readme_path, 'README.txt')
    # Set the file pointer to the beginning of the file
    memory_file.seek(0)
    # Create a Flask response with the zip file
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name=f'{model}.zip')


@main.route('/about', methods=['GET'])
def about():
    """About page."""
    return render_template('about.html')


@main.route('/faqs', methods=['GET'])
def faqs():
    """FAQs page."""
    question_id = request.args.get('question_id')
    return render_template('faqs.html', question_id=question_id)


@main.route('/all-spectra', methods=['GET'])
def index_spectra():
    """View all spectra page."""
    flash(FlashMessage('Model grid is not available to download yet. Please contact us if you need further information.', 'warning', 'page'))
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
        flash(FlashMessage('Email sent!', 'success', 'page'))
        return redirect(url_for('main.homepage'))
    else:
        flash(FlashMessage('error', 'danger', 'page'))
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


@app.route('/apple-touch-icon.png')
def apple_touch_icon():
    return send_from_directory('static', 'apple-touch-icon.png')


@app.route('/apple-touch-icon-precomposed.png')
def apple_touch_icon_precomposed():
    return send_from_directory('static', 'apple-touch-icon-precomposed.png')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico')
