from flask import Blueprint, request, render_template, redirect, url_for, session, flash, g
from flask_mail import Message
from collections import defaultdict
from euv_spectra_app.extensions import *
from datetime import timedelta

from euv_spectra_app.main.forms import ParameterForm, StarNameForm, PositionForm, StarNameParametersForm, ContactForm
from euv_spectra_app.helpers_astropy import search_tic, search_nea, search_vizier, search_simbad, search_gaia, search_galex, correct_pm, test_space_motion
from euv_spectra_app.helpers_db import *
from euv_spectra_app.helper_fits import *
from euv_spectra_app.helper_queries import *
main = Blueprint("main", __name__)

'''
————TODO—————
1. If no galex data found: flash no galex data was found, somehow let user know theres no galex data, maybe in template?
'''

'''
————NOTE————
- Do we subtract photospheric flux from errors too?
- STILL GETTING NEG VALUES FOR CORRECTED FLUXES
'''

@main.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)
    if not session.get('modal_show'):
        session['modal_show'] = False

@main.context_processor
def inject_form():
    form_dict = dict(contact_form=ContactForm())
    #print(form_dict)
    return dict(contact_form=ContactForm())


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


# '''————————————————————HOME NAME FORM————————————————————'''
        elif name_form.validate_on_submit():
            # STEP 1: store name data in session
            session["star_name"] = name_form.star_name.data
            star_name = session['star_name']
            print(f'name form validated with star: {star_name}')        

            # STEP 2: Get coordinate and motion info from Simbad
            simbad_data = search_simbad(star_name)
            if simbad_data['error_msg'] != None:
                return redirect(url_for('main.error', msg=simbad_data['error_msg']))

            # STEP 3: Put PM and Coord info into correction function
            corrected_coords = correct_pm(simbad_data['data'], star_name)
            if corrected_coords['error_msg'] != None:
                return redirect(url_for('main.error', msg=corrected_coords['error_msg']))

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
            # star_name_parameters_form = StarNameParametersForm()
            
            for key in res:
                if key != 'valid_info' and key != 'error_msg':
                    radio_input = getattr(star_name_parameters_form, key)
                    radio_input.choices = [(value, value) for value in res[key]]

            session['modal_show'] = True
            #return redirect(url_for('main.homepage'))
            flash('success!', 'success')
            return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form, star_name_parameters_form=star_name_parameters_form)

    return render_template('home.html', parameter_form=parameter_form, name_form=name_form, position_form=position_form)



'''————————————SUBMIT ROUTE FOR MODAL FORM————————————'''
@main.route('/modal-submit', methods=['POST'])
def submit_modal_form():
    if request.method == 'POST':
        print('star name parameter form validated!')
        form = request.form

        for key in form:
            # ignoring all manual parameters, submit, csrf token, and catalog names
            if form[key] == '--':
                session[key] = 'null'
            elif 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
                print('form key '+key+" "+form[key])
                session[key] = float(form[key])
        
        # session['modal_show'] = False
        print(session)
        return redirect(url_for('main.homepage'))
    flash('Submit a name or position to see this page.', 'warning')
    return redirect(url_for('main.homepage'))

    # parameter_form = StarNameParametersForm()
    # for key in res:
    #     if key != 'valid_info' and key != 'error_msg':
    #         radio_input = getattr(parameter_form, key)
    #         radio_input.choices = [(value, value) for value in res[key]]
    
    # parameter_form.populate_obj(request.form)
    # print(request.form)
    # print(parameter_form)

    # print('MEEEEEEEEEEP')
    # for key in request.form:
    #     print(key)
    #     print(request.form['key'])
    #     if 'manual' in key and request.form['key'] != None:
    #         radio_input = getattr(parameter_form, )


    # if parameter_form.validate_on_submit():
    #     print('star name parameter form validated!')
        # for key in form:
        #     # ignoring all manual parameters, submit, csrf token, and catalog names
        #     if form[key] == '--':
        #         session[key] = 'null'
        #     elif 'manual' not in key and 'submit' not in key and 'csrf_token' not in key and 'catalog_name' not in key:
        #         print('form key '+key+" "+form[key])
        #         session[key] = float(form[key])
        # print(session)

        # return redirect(url_for('main.homepage'))
    # else:
    #     print('NOT VALIDATED')
    #     print(parameter_form.errors)
    #     flash('Whoops, something went wrong. Please check your form and try again.', 'danger')
    #     return redirect(url_for('main.homepage'))



'''————————————SUBMIT ROUTE FOR RESULTS————————————'''
@main.route('/results', methods=['GET', 'POST'])
def return_results():
    if request.method == 'POST':
        form = ParameterForm(request.form)
        
        if form.validate_on_submit():
            print('parameter form validated!')
            for fieldname, value in form.data.items():
                print(fieldname, value)

            #CHECK DISTANCE UNIT: if distance unit is mas, convert to parsecs
            # mas_to_pc = 1/ (X mas / 1000)

            # STEP 1: Search the model_parameter_grid collection to find closest matching subtype
            matching_subtype = find_matching_subtype(session)
            session['model_subtype'] = matching_subtype['model']

            #STEP 2: Find closest matching photosphere model and get flux values
            matching_photospheric_flux = find_matching_photosphere(session)

            # want to add numbers to queries (diff value) then add the values and return query with lowest value?
            # matching_photospheric_flux_test = starter_photosphere_models.aggregate([
            #     {'$facet': {
            #         'matchedTeff': [
            #             {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],

            #         'matchedLogg': [
            #             {'$project': {'diff': {'$abs': {'$subtract': [session['logg'], '$logg']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],
            #     }},
            #     # get them together. Should list all rules from above  
            #     {'$project': {'doc': {'$concatArrays': ["$matchedTeff", "$matchedLogg"]}}},
            #     # split them apart, order by weight & desc, return top document
            #     # {'$unwind': "$doc"}, {}
            #     # {'$unwind': "$doc"}, {'$sort': {"doc.diff": -1}}, 
            #     {'$limit': 1},
            #     # reshape to retrieve documents in its original format 
            #     #{'$project': {'_id': "$doc._id", 'fits_filename': "$doc.doc.fits_filename", 'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass", 'euv': "$doc.doc.euv", 'nuv': "$doc.doc.nuv", 'fuv': "$doc.doc.fuv"}}
            # ])
            # print('TESTING')
            # for doc in matching_photospheric_flux_test:
            #     print(doc)

            #STEP 3: Convert, scale, and subtract photospheric contribution from fluxes (more detail in function)
            corrected_fluxes = convert_and_scale_fluxes(session, matching_photospheric_flux)
            session['corrected_nuv'] = corrected_fluxes['nuv']
            session['corrected_nuv_err'] = corrected_fluxes['nuv_err']
            session['corrected_fuv'] = corrected_fluxes['fuv']
            session['corrected_fuv_err'] = corrected_fluxes['fuv_err']
            print(session)

            #STEP 5: Do chi squared test between all models within selected subgrid and corrected observation ** this is on models with subtracted photospheric flux
            # final_models = find_models()
            # chisq2= sum((modelflux[i]- GALEX[i])**2 / GALEX[i])
            # catch if there's no fuv/nuv detection, chi squared JUST over one flux
            # return all results within upper and lower limits of fluxes (w/ chi squared values)
                # compute upper lim and lower lim for each flux and find within those values
            # return from lowest chi squared -> highest
            # return euv flux as <euv_flux> +/- difference from model

            #STEP 6: Read FITS file from matching models and create graph from data
            #file = find_fits_file(<filename>)
            file = find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
            fig = create_graph(file, session)

            #STEP 7: Convert graph into html component and send to front end
            html_string = convert_fig_to_html(fig)

            flash('_ Results were found within your submitted parameters', 'success')
            return render_template('result.html', subtype=matching_subtype, graph=html_string)
        else:
            flash('Whoops, something went wrong. Please check your inputs and try again!', 'danger')
            return redirect(url_for('main.homepage'))
    else:
        flash('Submit the required data through the manual parameters form to view this page.', 'warning')
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
    print(form)
    if form.validate_on_submit():
        # send email
        print(form.email.data)
        msg = Message(form.subject.data, sender='phoenixpegasusgrid@gmail.com', recipients=[form.email.data])
        msg.body = form.message.data
        mail.send(msg)
        flash('Email sent!', 'success')
        return redirect(url_for('main.homepage'))
    else:
        print(form.errors)
        flash('error', 'danger')
        return redirect(url_for('main.error', msg='Contact form unavailable at this time'))

@main.route('/clear-session')
def clear_session():
    session.clear()
    return redirect(url_for('main.homepage'))

''' ————————————ERROR HANDLING FOR HTML ERRORS———————————— '''
@main.route('/error/<msg>')
def error(msg):
    session['modal_show'] = False
    return render_template('error.html', error_msg=msg)

@main.app_errorhandler(500)
def internal_error(e):
    print(e)
    session['modal_show'] = False
    return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (500)'), 500

@main.app_errorhandler(503)
def internal_error(e):
    print(e)
    session['modal_show'] = False
    return render_template('error.html', error_msg='Something went wrong. Please try again later or contact us. (503)'), 503

@main.app_errorhandler(404)
def page_not_found(e):
    print(e)
    session['modal_show'] = False
    return render_template('error.html', error_msg='Page not found!'), 404
