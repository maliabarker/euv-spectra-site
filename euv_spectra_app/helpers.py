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