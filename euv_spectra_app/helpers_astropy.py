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


'''—————————NEA START—————————'''
def search_nea(search_input, search_format):
    nea_data = []
    if search_format == 'name':
        nea_data = NasaExoplanetArchive.query_criteria(table="pscomppars", select="top 5 disc_refname, st_spectype, st_teff, st_logg, st_mass, st_rad, sy_dist", where=f"hostname like '%{search_input}%'", order="hostname")
    elif search_format == 'position':
        nea_data = NasaExoplanetArchive.query_region(table="pscomppars", coordinates=SkyCoord(ra=search_input.ra.degree * u.deg, dec=search_input.dec.degree * u.deg), radius=1.0 * u.deg)

    return_info = {
        'valid_info' : 0,
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
                'dist' : data['sy_dist'].unmasked.value
            }
            return_info['data'] = star_info
            for value in star_info.values():
                if str(value) != 'nan':
                    return_info['valid_info'] += 1
            # print('———————————————————————————')
            # print('Exoplanet Archive')
            # print(data)
            # print(star_info)
        else:
            return_info['error_msg'] = 'Target is not an M or K type star. Data is currently only available for these spectral sybtypes. Please contact us with your target and parameters if you think this is a mistake.'
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return(return_info)
'''—————————NEA END—————————'''


'''—————————SIMBAD START—————————'''
def search_simbad(search_input):
    return_info = {
        'catalog_name' : 'Simbad',
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
        return_info['error_msg'] = 'No target found for that star name. Please try again.'
    return return_info
'''—————————SIMBAD END—————————'''



'''—————————GALEX START—————————'''
def search_galex(ra, dec):
    galex_data = Catalogs.query_object(f'{ra} {dec}', catalog="GALEX")
    return_info = {
        'data' : {},
        'error_msg' : None
    }
    if len(galex_data) > 0:
        MIN_DIST = galex_data['distance_arcmin'] < 0.167 # can try 0.5 as well
        if len(galex_data[MIN_DIST]) > 0:
            filtered_data = galex_data[MIN_DIST][0]
            # print(filtered_data)
            fluxes = {
                'fuv' : filtered_data['fuv_flux'],
                'fuv_err' : filtered_data['fuv_fluxerr'],
                'nuv' : filtered_data['nuv_flux'],
                'nuv_err' : filtered_data['nuv_fluxerr']
            }
            for key, value in fluxes.items():
                if ma.is_masked(value):
                    fluxes[key] = 'No Detection'
            return_info['data'] = fluxes
        else:
            return_info['error_msg'] = 'No detection in GALEX FUV and NUV. Look under question 3 on the FAQ page for more information.'
    else:
        return_info['error_msg'] = 'No detection in GALEX FUV and NUV. Look under question 3 on the FAQ page for more information.'
    return return_info
'''—————————GALEX END—————————'''



'''———————COORD CORRECTION START———————'''
def correct_pm(data, star_name):
    return_info = {
        'catalog_name' : 'Corrected Coords',
        'data' : {},
        'error_msg' : None
    }
    try:
        galex_time = mast_galex_times.find_one({'target': star_name})['t_min']
    except:
        return_info['error_msg'] = 'No detection in GALEX FUV and NUV. Look under question 3 on the FAQ page for more information.'
    else:
        try:
            # print('Correcting coords...')
            coords = data['ra'] + ' ' + data['dec']
            c = ''

            t3 = Time(galex_time, format='mjd') - Time(51544.0, format='mjd')
            td_year = t3.sec / 60 / 60 / 24 / 365.25
            if type(data['rad_vel']) == np.float64:
                c = SkyCoord(coords, unit=(u.hourangle, u.deg), distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr, radial_velocity=data['rad_vel']*u.km/u.s)
                # print('ORIGINAL COORDS')
                # print(c)
            else:
                c = SkyCoord(coords, unit=(u.hourangle, u.deg), distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr)
                # print('ORIGINAL COORDS')
                # print(c)

            # print('CORRECTED COORDS')
            c = c.apply_space_motion(dt=td_year * u.yr)
            # print(c)
            return_info['data'] = {
                'ra' : c.ra.degree,
                'dec' : c.dec.degree
            }
        except:
            return_info['error_msg'] = 'Could not correct coordinates'
    return return_info


def convert_coords(coords):
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
        return_info['error_msg'] = 'Error converting coordinates, please check your format and try again.'
    return return_info
'''———————COORD CORRECTION END———————'''



'''——————————————————————————NO LONGER IN USE—————————————————————'''
# def test_space_motion():
#     print('TESTING SPACE MOTION')
#     c1 = SkyCoord(ra=269.44850252543836 * u.deg, dec=4.739420051112412 * u.deg, distance=Distance(parallax=546.975939730948 * u.mas), pm_ra_cosdec=-801.5509783684709 * u.mas/u.yr, pm_dec=10362.394206546573 * u.mas/u.yr, radial_velocity=-110.46822 * u.km/u.s, obstime=Time(2016, format='jyear', scale='tcb'))
#     print(c1)
#     print(c1.apply_space_motion(new_obstime=Time(2050, format='jyear', scale='tcb')))
