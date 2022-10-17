from flask import Blueprint, request, render_template, redirect, url_for, session, flash, g
from flask_mail import Message
from collections import defaultdict
from euv_spectra_app.extensions import *
from datetime import timedelta

from euv_spectra_app.main.forms import StarForm, StarNameForm, PositionForm, StarNameParametersForm, ContactForm
from euv_spectra_app.helpers_astropy import search_tic, search_nea, search_vizier, search_simbad, search_gaia, search_galex, correct_pm, test_space_motion
#from euv_spectra_app.helpers_db import *
from euv_spectra_app.helper_fits import *
from euv_spectra_app.helper_queries import *
main = Blueprint("main", __name__)

'''
————TODO—————
1. Autofill null flux flag in parameter form if flux is null in search results (will need to change javascript autofill function for these radio buttons)
2. If no galex data found: flash no galex data was found, somehow let user know theres no galex data, maybe in template?
3. Change all form submissions to own routes
'''

'''
————NOTE————
- Will we be searching for photosphere models under the specified model subtype? Or will we search this same start photosphere flux file?
- what is point of multiplying fluxes by the dist^2/rad^2 number? do we then subtract photospheric fluxes from fluxes multiplied by this number?
- do we find matching photospheric flux with temp, logg, and mass?
- What are units for photospheric fluxes? Seem pretty large
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
    contact_form = ContactForm()
    
    
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
            for fieldname, value in parameter_form.data.items():
                print(fieldname, value)

            # STEP 1: Search the model_parameter_grid collection to find closest matching subtype
            matching_subtype = find_matching_subtype(session)
            session['model_subtype'] = matching_subtype['model']

            #STEP 2: Find closest matching photosphere model and get flux values
            matching_photospheric_flux = find_matching_photosphere(session)

            # want to add numbers to queries (diff value) then add the values and return query with lowest value?
            matching_photospheric_flux_test = starter_photosphere_models.aggregate([
                {'$facet': {
                    'matchedTeff': [
                        {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],

                    'matchedLogg': [
                        {'$project': {'diff': {'$abs': {'$subtract': [session['logg'], '$logg']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],
                }},
                # get them together. Should list all rules from above  
                {'$project': {'doc': {'$concatArrays': ["$matchedTeff", "$matchedLogg"]}}},
                # split them apart, order by weight & desc, return top document
                # {'$unwind': "$doc"}, {}
                # {'$unwind': "$doc"}, {'$sort': {"doc.diff": -1}}, 
                {'$limit': 1},
                # reshape to retrieve documents in its original format 
                #{'$project': {'_id': "$doc._id", 'fits_filename': "$doc.doc.fits_filename", 'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass", 'euv': "$doc.doc.euv", 'nuv': "$doc.doc.nuv", 'fuv': "$doc.doc.fuv"}}
            ])
            print('TESTING')
            for doc in matching_photospheric_flux_test:
                print(doc)

            #STEP 3: Multiply FUV and NUV by dist^2/rad^2
            dist_sqr = pow(session['dist'], 2)
            rad_sqr = pow(session['stell_rad'], 2)
            arb_num = dist_sqr/rad_sqr
            print(arb_num)

            session['fuv'] = session['fuv'] * arb_num
            session['nuv'] = session['nuv'] * arb_num
            print(session)

            #STEP 4: Subtract photospheric fluxes from FUV and NUV
            #ERROR: This gives huge negative value, are units the same?
            session['fuv'] = session['fuv'] - matching_photospheric_flux['fuv']
            session['nuv'] = session['nuv'] - matching_photospheric_flux['nuv']
            print(session)

            #STEP 5: Do chi squared test between all models within selected subgrid and corrected observation to find (3?) closest matching data points
            # final_models = find_models()

            #STEP 6: Read FITS file from matching models and create graph from data
            #file = find_fits_file(<filename>)
            file = find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
            fig = create_graph(file, session)

            #STEP 7: Convert graph into html component and send to front end
            html_string = convert_fig_to_html(fig)
            #print(html_string)

            flash('_ Results were found within your submitted parameters')
            return render_template('result.html', subtype=matching_subtype, contact_form=contact_form, graph=html_string)


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

            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form, show_modal=True, contact_form=contact_form)
            


#'''————————————————————MODAL NAME PARAMETER FORM————————————————————'''
        elif session.get('star_name'):
            print('star name parameter form validated!')
            form_data = request.form

            for key in form_data:
                # ignoring all manual parameters, submit, csrf token, and catalog names
                if 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
                    print('form key '+key+" "+form_data[key])
                    session[key] = float(form_data[key])
                    
            print(session)
            return redirect(url_for('main.homepage'))

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, show_modal=False, contact_form=contact_form)



@main.route('/ex-spectra', methods=['GET', 'POST'])
def ex_result():
    contact_form = ContactForm()
    return render_template('result.html', contact_form=contact_form)


@main.route('/about', methods=['GET'])
def about():
    contact_form = ContactForm()
    return render_template('about.html', contact_form=contact_form)


@main.route('/faqs', methods=['GET'])
def faqs():
    contact_form = ContactForm()
    return render_template('faqs.html', contact_form=contact_form)


@main.route('/all-spectra', methods=['GET'])
def index_spectra():
    contact_form = ContactForm()
    return render_template('index-spectra.html', contact_form=contact_form)


@main.route('/contact', methods=['POST'])
def send_email():
    form = ContactForm(request.form)
    print(form)
    if form.validate_on_submit():
        # send email
        msg = Message(form.subject.data, sender=form.email.data, recipients=['phoenixpegasusgrid@gmail.com'])
        msg.body = form.message.data
        mail.send(msg)
        flash('Email sent!')
        return redirect(url_for('main.homepage'))




# FOR PAGINATION OF RESULTS OR SEARCH
# from flask_paginate import Pagination, get_page_parameter