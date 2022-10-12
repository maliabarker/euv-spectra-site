# FOR ASTROQUERY/GALEX DATA
from astroquery.mast import Catalogs, Observations
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.vizier import Vizier
from astroquery.gaia import Gaia
from astroquery.simbad import Simbad
customSimbad = Simbad()
customSimbad.add_votable_fields('pm')

Gaia.MAIN_GAIA_TABLE = "gaiaedr3.gaia_source"
Gaia.ROW_LIMIT = 1

from astropy.coordinates import SkyCoord, Distance
import astropy.units as u
from astropy.time import Time
import numpy as np

def search_tic(search_input):
    tic_data = Catalogs.query_object(search_input, radius=.02, catalog="TIC")
    return_info = {
        'name' : 'TESS Input Catalog',
        'valid_info' : 0,
        'data' : {},
        'error_msg' : None
    }
    if len(tic_data) > 0:
        data = tic_data[0]
        # print('TIC')
        # print(data)
        star_info = {
            'teff' : float(data['Teff']),
            'logg' : float(data['logg']),
            'mass' : float(data['mass']),
            'rad' : float(data['rad']),
            'dist' : float(data['d'])
        }
        return_info['data'] = star_info
        for value in star_info.values():
            if str(value) != 'nan':
                return_info['valid_info'] += 1
        # print('———————————————————————————')
        # print('TIC')
        # print(data)
        # print(star_info)
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return(return_info)

def search_nea(search_input):
    nea_data = NasaExoplanetArchive.query_criteria(table="pscomppars", where=f"hostname like '%{search_input}%'", order="hostname")
    return_info = {
        'name' : 'NASA Exoplanet Archive',
        'valid_info' : 0,
        'data' : {},
        'error_msg' : None
    }
    if len(nea_data) > 0:
        data = nea_data[0]
        # print('NEA')
        # print(data)
        # print('———————————————————————————')
        # print('Exoplanet Archive')
        # print(data)
        star_info = {
            'teff' : data['st_teff'].unmasked.value,
            'logg' : data['st_logg'],
            'mass' : data['st_mass'].unmasked.value,
            'rad' : data['st_rad'].unmasked.value,
            'dist' : data['sy_dist'].unmasked.value
        }
        return_info['data'] = star_info
        for value in star_info.values():
            if str(value) != 'nan':
                return_info['valid_info'] += 1
        # print(star_info)
        # print(f'VALID INFO: {valid_info}')
    else:
        return_info['error_msg'] = 'Nothing found for this target'

    return(return_info)

def search_vizier(search_input):
    tables = []
    keywords = ['teff', 'logg', 'mass', 'rad', 'dist']

    return_info = {
        'name' : 'Vizier',
        'data' : [],
        'error_msg' : None
    }

    vizier_catalogs = Vizier.query_object(search_input)

    for table_name in vizier_catalogs.keys():
        table = vizier_catalogs[table_name]
        cols = list(col.lower() for col in table.columns)

        if all(elem in cols for elem in keywords):
            if table_name not in tables:
                tables.append(table_name)

    # print(f'VIZIER TABLES: {tables}')
    if tables:
        for table_name in tables:
            table = vizier_catalogs[table_name][0]
            # print('————————————————————————')
            # print(f'TABLE NAME: {table_name}')
            # print(table)
            valid_info = 0
            star_info = {
                'teff' : float(table['Teff']),
                'logg' : float(table['logg']),
                'mass' : float(table['Mass']),
                'rad' : float(table['Rad']),
                'dist' : float(table['Dist'])
            }

            for value in star_info.values():
                if str(value) != 'nan':
                    valid_info += 1

            # print(star_info)
            # print(f'VALID INFO: {valid_info}')
            table_dict = {
                'name' : f'Vizier catalog: {table_name}',
                'data' : star_info,
                'valid_info' : valid_info,
                'error_msg' : None
            }

            if valid_info == 0:
                table_dict['error_msg'] = 'No data found'

            return_info['data'].append(table_dict)
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return(return_info)

def search_simbad(search_input):
    return_info = {
        'name' : 'Simbad',
        'data' : {},
        'error_msg' : None
    }
    result_table = customSimbad.query_object(search_input)
    if result_table and len(result_table) > 0:
        data = result_table[0]
        print(data)
        return_info['data'] = {
            'ra': data['RA'], 
            'dec': data['DEC'], 
            'pmra': data['PMRA'], 
            'pmdec': data['PMDEC']
        }
    else:
        return_info['error_msg'] = 'No target found for that star name. Please try again.'
    return return_info

def search_gaia(search_input):
    return_info = {
        'name' : 'Gaia',
        'data' : {},
        'error_msg' : None
    }
    
    # try:
    #     c = SkyCoord.from_name(search_input)
    #     print(c.ra.degree)
    #     print(c.dec.degree)
    # except:
    #     return_info['error_msg'] = 'No coordinates found for this target.'
    
    # if c:
    #     coord = SkyCoord(ra=c.ra.degree, dec=c.dec.degree, unit=(u.degree, u.degree), frame='icrs')
    #     width, height = u.Quantity(0.02, u.deg), u.Quantity(0.02, u.deg)
    #     gaia_data = Gaia.query_object_async(coordinate=coord, width=width, height=height)
    #     #gaia_data.pprint()

    gaia_data = Catalogs.query_object(search_input, radius=.02, catalog="Gaia")
    if len(gaia_data) > 0:
        data = gaia_data[0]
        #print(data)
        return_info['data'] = {
            'ra': data['ra'], 
            'dec': data['dec'], 
            'pmra': data['pmra'], 
            'pmdec': data['pmdec'],
            'ref_epoch' : data['ref_epoch'],
            'parallax' : data['parallax']
        }
        print(return_info['data'])
    else:
        return_info['error_msg'] = 'No data found for this target, please try again'
    return return_info

def search_galex(ra, dec):
    galex_data = Catalogs.query_object(f'{ra} {dec}', catalog="GALEX")
    return_info = {
        'name' : 'GALEX',
        'data' : {},
        'error_msg' : None
    }
    if len(galex_data) > 0:
        MIN_DIST = galex_data['distance_arcmin'] < 0.3 # can try 0.5 as well
        if len(galex_data[MIN_DIST]) > 0:
            filtered_data = galex_data[MIN_DIST][0]
            # add dist arcmin value
            fluxes = {
                'fuv' : filtered_data['fuv_flux'],
                'nuv' : filtered_data['nuv_flux']
            }
            return_info['data'] = fluxes
        else:
            return_info['error_msg'] = 'No data points with distance arcmin under 0.1'
    else:
        return_info['error_msg'] = 'Nothing found for this target'
    return return_info

def correct_pm(data, star_name):
    return_info = {
        'name' : 'Corrected Coords',
        'data' : {},
        'error_msg' : None
    }

    try:
        galex_time = Observations.query_criteria(objectname=star_name, obs_collection='GALEX')[0]['t_max']
        print(f'TIME {galex_time}')
    except:
        return_info['error_msg'] = 'No GALEX Observations Available'
    
    if galex_time:
        c = SkyCoord(ra=data['ra']*u.degree, dec=data['dec']*u.degree, distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr, obstime=Time(data['ref_epoch'], format='jyear', scale='tcb'))
        # c = SkyCoord(ra=data['ra']*u.degree, dec=data['dec']*u.degree, distance=Distance(parallax=data['parallax']*u.mas, allow_negative=True), pm_ra_cosdec=data['pmra']*u.mas/u.yr, pm_dec=data['pmdec']*u.mas/u.yr, radial_velocity=data['rad_vel']*u.km/u.s, obstime=Time(data['ref_epoch'], format='jyear', scale='tcb'))
        c = c.apply_space_motion(new_obstime=Time(galex_time, format='mjd'))
        print(c)
        return_info['data'] = {
            'ra' : c.ra.degree,
            'dec' : c.dec.degree
        }
        print(return_info['data'])
    else:
        return_info['error_msg'] = 'Could not correct coordinates'
    return return_info