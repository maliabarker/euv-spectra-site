from flask import Blueprint, request, render_template, redirect, url_for

from euv_spectra_app.models import Star
from euv_spectra_app.main.forms import StarForm, StarNameForm

# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Catalogs
import astropy.units as u
from astroquery.vizier import Vizier
import pprint
pp = pprint.PrettyPrinter(indent=4)


main = Blueprint("main", __name__)


# ——————————— HELPER FUNCTIONS ————————————— #
def search_galex(search_input):
    flux_catalog_data = Catalogs.query_object(search_input, radius=.02, catalog="GALEX")
    MIN_DIST = flux_catalog_data['distance_arcmin'] < 0.1
    filtered_data = flux_catalog_data[MIN_DIST][0]
    fluxes = (filtered_data['fuv_flux'], filtered_data['nuv_flux'])
    return fluxes

    # print(filtered_data)
    # ra = filtered_data['ra']
    # dec = filtered_data['dec']
    # print(f'Position {ra}, {dec}')


'''
————TODO—————

1. style form errors
    if there is a form error, keep the fuv and nuv inputs visible
    add flashes if there are form errors
    outline incorrect form inputs in red? (stretch)

2. query GALEX db when not searching by name
'''

@main.route('/', methods=['GET', 'POST'])
def homepage():
    
    form = StarForm()
    name_form = StarNameForm()

    if request.method == 'POST':
        print('————————POSTING————————')

        if form.validate_on_submit():
            print('form validated!')
            print(form)

            for fieldname, value in form.data.items():
                print(fieldname, value)

            
            return redirect(url_for('main.ex_result', formname='main'))


        elif name_form.validate_on_submit():

            star_name = name_form.name.data
            print(f'name form validated with star: {star_name}')

            '''GETTING FLUX VALUES FROM GALEX'''
            fluxes = search_galex(star_name)
            fuv, nuv = fluxes[0], fluxes[1]
            print(f'FLUXES {fuv}, {nuv}')

            '''GETTING OTHER STELLAR VALUES'''
            result = Vizier.query_region(star_name, radius=0.1*u.deg)
            tic82_table = result['IV/39/tic82'][0]

            teff = tic82_table['Teff']
            logg = tic82_table['logg']
            mass = tic82_table['Mass']
            rad = tic82_table['Rad']
            dist = tic82_table['Dist']
            print(f'INFO Teff:{teff}, Logg:{logg}, Mass:{mass}, Rad:{rad}, Dist:{dist}')

            
            catalog_data = Catalogs.query_object(star_name, radius=.02, catalog="TIC")
            table2 = catalog_data[0]

            teff2 = table2['Teff']
            logg2 = table2['logg']
            mass2 = table2['mass']
            rad2 = table2['rad']
            dist2A = table2['d']
            dist2B = table2['dstArcSec']
            print(f'INFO2 Teff:{teff2}, Logg:{logg2}, Mass:{mass2}, Rad:{rad2}, DistA:{dist2A}, DistB:{dist2B}')
            
            return redirect(url_for('main.ex_result', formname='name'))

    return render_template('home.html', form=form, name_form=name_form)

@main.route('/ex-spectra', methods=['GET', 'POST'])
def ex_result():
    return render_template('result.html')




# TODO (stretch challenge) allow for file uploads to AWS bucket if adding new models/spectra, pagination
# from werkzeug.utils import secure_filename
# from data_app.util.helpers import upload_file_to_s3, read_csv_from_s3
# for uploading files
# ALLOWED_EXTENSIONS = {'png', 'csv'}
# FOR PAGINATION OF RESULTS OR SEARCH
# from flask_paginate import Pagination, get_page_parameter