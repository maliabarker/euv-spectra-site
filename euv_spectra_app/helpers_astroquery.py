# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Catalogs
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.simbad import Simbad
customSimbad = Simbad()
customSimbad.remove_votable_fields('coordinates')
customSimbad.add_votable_fields('ra', 'dec', 'pmra', 'pmdec', 'plx', 'rv_value')

from astropy.coordinates import SkyCoord, Distance
import astropy.units as u
from astropy.time import Time
import numpy as np
import numpy.ma as ma
from euv_spectra_app.extensions import *


def populate_modal(search_input, search_format):
    '''
    * HELPER FUNCTION FOR SEARCHING OBJECT/POSITION & RETURNING FOR MODAL POPULATION *
    Inputs: search input (string) and the search format (string, will be 'position' or 'name')
    Outputs: Dictionary of radio choices (dict object) or error message. 
        For radio choices dict:
        Keys are names of radio buttons (ex: teff, mass, logg)
        Values include corresponding data returned from Astroquery database queries
    '''
    # STEP 1: Assign terms used by function that will be declared in in 'if' statements
    galex_coords = None
    # STEP 2: Initialize the dictionary that will be returned to the route
    return_data = {
        'error_msg': None,
        'search_term': search_input,
        'radio_choices': None
    }
    # STEP 3: Check for search type (position or name)
    if search_format == 'position':
        # IF POSITION
        # STEP P1: Change coordinates to ra and dec
        converted_coords = convert_coords(search_input)
        if converted_coords['error_msg'] != None:
            return_data['error_msg'] = converted_coords['error_msg']
            return return_data
        # STEP P2: Return the coordinates that will be put into GALEX search and assign new search term
        galex_coords = converted_coords
        search_input = converted_coords['data']['skycoord_obj']

    elif search_format == 'name':
        # IF NAME
        # STEP N1: Check if name is in the mast target database (meant to check for case & spacing errors)
        for name in db.mast_galex_times.distinct('target'):
            if search_input.upper().replace(' ', '') == name.upper().replace(' ', ''):
                search_input = name
                break
        # STEP N2: Get coordinate and motion info from Simbad
        simbad_data = search_simbad(search_input)
        if simbad_data['error_msg'] != None:
            return_data['error_msg'] = simbad_data['error_msg']
            return return_data
        # STEP N3: Put PM and Coord info into correction function
        corrected_coords = correct_pm(simbad_data['data'], search_input)
        if corrected_coords['error_msg'] != None:
            return_data['error_msg'] = corrected_coords['error_msg']
            return return_data
        # STEP N4: Return the coordinates that will be put into GALEX search and assign new search term
        return_data['search_term'] = search_input
        galex_coords = corrected_coords
    # STEP 4: Search NASA Exoplanet Archive with the search term & type
    nea_data = search_nea(search_input, search_format)
    if nea_data['error_msg'] != None:
        return_data['error_msg'] = nea_data['error_msg']
        return return_data

    j_band = nea_data['data'].pop('j_band')
    # STEP 5: Search GALEX with corrected/converted coords
    galex_data = search_galex(galex_coords['data']['ra'], galex_coords['data']['dec'], j_band)
    if galex_data['error_msg'] != None:
        return_data['error_msg'] = galex_data['error_msg']
    # STEP 6: Append data to the final catalogs list if there are no errors
    catalog_data = [nea_data, galex_data]
    # STEP 7: Append each type of data (this will be the temp, mass, etc.) into its own key value pair
    data = {key: dict['data'][key] for dict in catalog_data for key in dict['data']}
    return_data['radio_choices'] = data
    # STEP 8: Return the return_data dict object
    return return_data
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def search_nea(search_input, search_format):
    '''
    * HELPER FUNCTION FOR SEARCHING THE NASA EXOPLANET ARCHIVE BY OBJECT/POSITION FOR STELLAR PARAMETERS *
    Inputs: search input (string) and the search format (string, will be 'position' or 'name')
    Outputs: Dictionary of data (dict object) or error message. 
        For data dict:
        Keys are data objects (ex: teff, mass, logg)
        Values are corresponding data values
    '''
    nea_data = []
    if search_format == 'name':
        nea_data = NasaExoplanetArchive.query_criteria(table="pscomppars", select="top 5 disc_refname, st_spectype, st_teff, st_logg, st_mass, st_rad, sy_dist, sy_jmag", where=f"hostname like '%{search_input}%'", order="hostname")
    elif search_format == 'position':
        nea_data = NasaExoplanetArchive.query_region(table="pscomppars", coordinates=SkyCoord(ra=search_input.ra.degree * u.deg, dec=search_input.dec.degree * u.deg), radius=1.0 * u.deg)

    return_info = {
        'data' : {},
        'error_msg' : None
    }
    if len(nea_data) > 0:
        data = nea_data[0]
        if 'M' in data['st_spectype'] or 'K' in data['st_spectype']:
            star_info = {
                'teff' : data['st_teff'].unmasked.value,
                'logg' : data['st_logg'],
                'mass' : data['st_mass'].unmasked.value,
                'stell_rad' : data['st_rad'].unmasked.value,
                'dist' : data['sy_dist'].unmasked.value,
                'j_band': data['sy_jmag'].unmasked.value
            }
            return_info['data'] = star_info
            # print('———————————————————————————')
            # print('Exoplanet Archive')
            # # print(data)
            # print(star_info)
        else:
            return_info['error_msg'] = 'Target is not an M or K type star. Data is currently only available for these spectral sybtypes. \nPlease contact us with your target and parameters if you think this is a mistake.'
    else:
        return_info['error_msg'] = f'Nothing found for {search_input} in the NASA exoplanet archive. \nPlease check spelling or coordinate format.'
    return(return_info)
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def search_simbad(search_input):
    '''
    * HELPER FUNCTION FOR SEARCHING SIMBAD BY OBJECT FOR COORD & PROPER MOTION DATA *
    Inputs: search input (string, has to be an object name not coords)
    Outputs: Dictionary of data (dict object) or error message. 
        For data dict:
        Keys are data objects (ex: ra, dec, pm)
        Values are corresponding data values
    '''
    return_info = {
        'data' : {},
        'error_msg' : None
    }
    result_table = customSimbad.query_object(search_input)
    if result_table and len(result_table) > 0:
        data = result_table[0]
        return_info['data'] = {
            'ra': data['RA'], 
            'dec': data['DEC'], 
            'pmra': data['PMRA'], 
            'pmdec': data['PMDEC'],
            'parallax': data['PLX_VALUE'],
            'rad_vel': data['RV_VALUE']
        }
    else:
        return_info['error_msg'] = f'No target found for {search_input} in Simbad. \nPlease check spelling or coordinate format.'
    return return_info
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def search_galex(ra, dec, j_band):
    '''
    * HELPER FUNCTION FOR SEARCHING MAST GALEX DATABASE BY COORDS FOR FLUX DENSITIES *
    Inputs: ra (float) and dec (float)
    Outputs: Dictionary of data (dict object) or error message. 
        For data dict:
        Keys are data objects (ex: fuv, nuv)
        Values are corresponding data values
    '''
    # STEP 1: Initialize the return info dict 
            # We will make data equal the null placeholder 'No Detection' so if there are any error catches, 
            # the front end will still be able to load in the null values on the modal form 
            # & give users option to input their own values
    return_info = {
        'data' : {
            'fuv' : 'No Detection',
            'fuv_err' : 'No Detection',
            'nuv' : 'No Detection',
            'nuv_err' : 'No Detection'
        },
        'error_msg' : None
    }
    # STEP 2: Query the MAST catalogs object by GALEX catalog & given ra and dec
    galex_data = Catalogs.query_object(f'{ra} {dec}', catalog="GALEX")
    # STEP 3: If there are results returned and results within 0.167 arcmins, then start processing the data
    if len(galex_data) > 0:
        MIN_DIST = galex_data['distance_arcmin'] < 0.167 # can try 0.5 as well
        if len(galex_data[MIN_DIST]) > 0:
            filtered_data = galex_data[MIN_DIST][0]
            # STEP 4: Initialize the data return dict w/ flux densities and errors
            fluxes = {
                'fuv' : filtered_data['fuv_flux'],
                'fuv_err' : filtered_data['fuv_fluxerr'],
                'nuv' : filtered_data['nuv_flux'],
                'nuv_err' : filtered_data['nuv_fluxerr']
            }
            # STEP 5: Check if there are any masked values (these will be null values) and change accordingly
            if ma.is_masked(fluxes['fuv']) and ma.is_masked(fluxes['nuv']):
                # both are null, point to null placeholders and add error message
                fluxes['fuv'], fluxes['nuv'], fluxes['fuv_err'], fluxes['nuv_err'] = 'No Detection', 'No Detection', 'No Detection', 'No Detection'
                return_info['error_msg'] = 'GALEX error: No detection in GALEX FUV and NUV. \nLook under question 3 on the FAQ page for more information.'
            elif ma.is_masked(fluxes['fuv']):
                # only FUV is null, predict FUV and add error message
                predicted_fluxes = predict_fluxes('fuv', fluxes['nuv'], fluxes['nuv_err'], j_band)
                fluxes['fuv'] = predicted_fluxes['new_flux']
                fluxes['fuv_err'] = predicted_fluxes['new_err']
                return_info['error_msg'] = 'GALEX error: No detection in GALEX FUV, substitution is calculated for you. \nLook under question 3 on the FAQ page for more information.'
            elif ma.is_masked(fluxes['nuv']):
                # only NUV is null, predict NUV and add error message
                predicted_fluxes = predict_fluxes('nuv', fluxes['fuv'], fluxes['fuv_err'], j_band)
                fluxes['nuv'] = predicted_fluxes['new_flux']
                fluxes['nuv_err'] = predicted_fluxes['new_err']
                return_info['error_msg'] = 'GALEX error: No detection in GALEX NUV, substitution is calculated for you. \nLook under question 3 on the FAQ page for more information.'
            # STEP 6: Add the new data dict to the data object in return info
            return_info['data'] = fluxes
        else:
            return_info['error_msg'] = 'GALEX error: No detection in GALEX FUV and NUV. \nLook under question 3 on the FAQ page for more information.'
    else:
        return_info['error_msg'] = 'GALEX error: No detection in GALEX FUV and NUV. \nLook under question 3 on the FAQ page for more information.'
    return return_info
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def correct_pm(data, star_name):
    '''
    * HELPER FUNCTION TO CORRECT FOR PROPER MOTION *
    Inputs: data (dict, includes all data collected from simbad search), star_name (string)
    Outputs: Dictionary of data (dict object) or error message. 
        For data dict:
        Keys are data objects (ra, dec corrected for proper motion)
        Values are corresponding data values
    '''
    # STEP 1: Initialize the return dict
    return_info = {
        'data' : {},
        'error_msg' : None
    }
    # STEP 2: Find a GALEX observation time from custom compiled dataset
    try:
        galex_time = mast_galex_times.find_one({'target': star_name})['t_min']
    except:
        return_info['error_msg'] = 'No detection in GALEX FUV and NUV. \nLook under question 3 on the FAQ page for more information.'
    else:
        try:
            # STEP 3: If observation time is found, start coordinate correction by initializing variables
            coords = data['ra'] + ' ' + data['dec']
            c = ''

            # STEP 4: Calculate time difference between observation time and Jan 1st, 2000 (J2000)
            t3 = Time(galex_time, format='mjd') - Time(51544.0, format='mjd')
            # STEP 5: Convert time (which will return in seconds) into years
            td_year = t3.sec / 60 / 60 / 24 / 365.25
            # STEP 6: Check to see if radial velocity is given then create SkyCoord object with all data
            if type(data['rad_vel']) == np.float64:
                c = SkyCoord(coords, unit=(u.hourangle, u.deg), distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr, radial_velocity=data['rad_vel']*u.km/u.s)
            else:
                c = SkyCoord(coords, unit=(u.hourangle, u.deg), distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr)

            # STEP 7: Use apply_space_motion function to calculate new coordinates
            c = c.apply_space_motion(dt=td_year * u.yr)
            # STEP 8: Add new coordinates to return data dict
            return_info['data'] = {
                'ra' : c.ra.degree,
                'dec' : c.dec.degree
            }
        except:
            return_info['error_msg'] = 'Could not correct coordinates.'
    return return_info
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def convert_coords(coords):
    '''
    * HELPER FUNCTION TO CONVERT COORDINATES FROM WHATEVER IS INPUTTED BY USER TO RA & DEC *
    Inputs: coords (string)
    Outputs: Dictionary of data (dict object) or error message. 
        For data dict:
        Keys are data objects (ra, dec)
        Values are corresponding data values
    '''
    return_info = {
        'data' : {},
        'error_msg' : None
    }
    try:
        c = SkyCoord(coords, unit=(u.hourangle, u.deg))
        return_info['data'] = {
            'ra' : c.ra.degree,
            'dec' : c.dec.degree,
            'skycoord_obj' : c
        }
    except:
        return_info['error_msg'] = f'Error converting your coordinates {coords}. \nPlease check your format and try again.'
    return return_info
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def predict_fluxes(flux_type, flux_value, flux_err, j_band):
    '''
    * HELPER FUNCTION TO CALCULATE A PREDICTED FLUX IF MISSING FROM GALEX *
    Inputs: flux type (string), flux_value (float, the non-missing value), flux_err (float, the non-missing value), j_band (float, obtained from NEA query)
    Outputs: Dictionary of data (newly calculated flux & error)
    '''
    return_data = {
        'new_flux': None,
        'new_err': None
    }
    # STEP 1: Convert J band 2MASS magnitude to microjanskies
    zeropoint = 1594
    j_band_ujy = 1000 * (zeropoint * pow( 10.0, -0.4 * j_band ))
    # STEP 2: Calculate upper and lower limits of the non missing flux (will be used to find error)
    upper_lim = flux_value + flux_err
    lower_lim = flux_value - flux_err
    # STEP 3: Use equation to predict missing flux & error
    if flux_type == 'nuv':
        # Predict NUV flux using NUV = ((FUV/J)^(1/1.1)) * J
        # STEP N1: Use equation to find upper, lower limits and new flux values
        new_nuv_upper_lim = (pow((upper_lim / j_band_ujy), (1 / 1.1))) * j_band_ujy
        new_nuv = (pow((flux_value / j_band_ujy), (1 / 1.1))) * j_band_ujy
        new_nuv_lower_lim = (pow((lower_lim / j_band_ujy), (1 / 1.1))) * j_band_ujy
        # STEP N2: Find the differences between the upper and lower limits and flux value (these will be error)
                #  Then calculate average of these values to get the average error
        upper_nuv = new_nuv_upper_lim - new_nuv
        lower_nuv = new_nuv - new_nuv_lower_lim
        avg_nuv_err = (upper_nuv + lower_nuv) / 2
        # STEP N3: Assign new values to return data dict using calculated flux & error
        return_data['new_flux'] = new_nuv
        return_data['new_err'] = avg_nuv_err
    elif flux_type == 'fuv':
        # Predict FUV flux using FUV = ((NUV/J)^1.11) * J
        # STEP F1: Use equation to find upper, lower limits and new flux values
        new_fuv_upper_lim = (pow((upper_lim / j_band_ujy), 1.1)) * j_band_ujy
        new_fuv = (pow((flux_value / j_band_ujy), 1.1)) * j_band_ujy
        new_fuv_lower_lim = (pow((lower_lim / j_band_ujy), 1.1)) * j_band_ujy
        # STEP F2: Find the differences between the upper and lower limits and flux value (these will be error)
                #  Then calculate average of these values to get the average error
        upper_fuv = new_fuv_upper_lim - new_fuv
        lower_fuv = new_fuv - new_fuv_lower_lim
        avg_fuv_err = (upper_fuv + lower_fuv) / 2
        # STEP N3: Assign new values to return data dict using calculated flux & error
        return_data['new_flux'] = new_fuv
        return_data['new_err'] = avg_fuv_err
    return return_data
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''——————————————————————————NO LONGER IN USE—————————————————————'''
# def test_space_motion():
#     print('TESTING SPACE MOTION')
#     c1 = SkyCoord(ra=269.44850252543836 * u.deg, dec=4.739420051112412 * u.deg, distance=Distance(parallax=546.975939730948 * u.mas), pm_ra_cosdec=-801.5509783684709 * u.mas/u.yr, pm_dec=10362.394206546573 * u.mas/u.yr, radial_velocity=-110.46822 * u.km/u.s, obstime=Time(2016, format='jyear', scale='tcb'))
#     print(c1)
#     print(c1.apply_space_motion(new_obstime=Time(2050, format='jyear', scale='tcb')))
