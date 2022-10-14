from euv_spectra_app.extensions import *
import pandas as pd
import re
import os
# import codecs
# from bson.binary import Binary
from astropy.io import fits
from astropy.table import Table

'''——————START FITS STUFF——————'''
def read_fits(filepath):
    # fits_image_filename = fits.util.get_testdata_filepath('test0.fits')
    # hdul = fits.open(filepath)
    with fits.open(filepath) as hdul:
        data = hdul[1].data
        hdul.info()
        data = hdul[0].data
        print(data)
    
    info = Table.read(filepath, hdu=1)
    print(info)
    print(info.columns)
    print(info['WAVELENGTH'])
    print(info['FLUX'])

'''——————END FITS STUFF——————'''

'''———————MONGO DATABASE STUFF———————'''
def upload_fits_file(filepath):
    with open(filepath, "rb") as fits_file:
        filename = os.path.basename(filepath)
        print(filename)
        # grid_id = grid_fs.put(fits_file, content_type = 'RFC 4047', filename = filename)
        # print(grid_id)

        new_file = {
            # 'grid_id' : grid_id,
            'name' : filename,
            'file' : fits_file.read()
        }
        print(new_file)

        fits_files.insert_one(new_file)
        return 'Completed'

def find_fits_file(filename):
    item = fits_files.find_one({'name': filename})
    #print(item)
    # fits_file = grid_fs.get(item['id'])
    # print(fits_file)
    # base64_data = codecs.encode(fits_file.read(), 'base64')
    # final_file = base64_data.decode('utf-8')
    # print(final_file)
    read_fits(item['file'])

    return 'done'

def read_model_parameter_table(file_path):
    # step 1: read in csv file with pandas
    DATAPATH = file_path
    dataset = pd.read_csv(DATAPATH)
    for index, row in dataset.iterrows():
        model = {
            'model' : row['Spectral_Type'],
            'teff' : row['Teff'],
            'logg' : row['logg'],
            'mass' : row['M']
        }
        print(model)
        model_parameter_grid.insert_one(model)
    return 'Completed!'

def read_model_table(file_path, collection):
    # step 1: read in csv file with pandas
    DATAPATH = file_path
    dataset = pd.read_csv(DATAPATH)

    # step 2: iterate over each row to assign variables and input info accordingly:
    #     FROM FILENAME (use regex)
    #         - full fits filename, model (ex: M0), teff, logg, TRgrad, cmtop, cmmin
    #     FROM FLUXES & MASS
    #         - Mass, EUV, FUV, NUV, J

    print(f'Adding files to {collection}')

    for index, row in dataset.iterrows():
        model_str = row['Model']

        # step 3: append each new row & matching info to DB
        new_model = {
            'fits_filename' : model_str,
            'model' : model_str[:2],
            'teff' : re.search("(?<=Teff=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            'logg' : re.search("(?<=logg=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            'mass' : row['Mass'],
            'trgrad' : re.search("(?<=TRgrad=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            'cmtop' : re.search("(?<=cmtop=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            'cmin' : re.search("(?<=cmin=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            'euv' : row['F_EUV'],
            'fuv' : row['F_FUV'],
            'nuv' : row['F_NUV'],
            'j' : row['F_J']
        }

        collection.insert_one(new_model)

        print(new_model['fits_filename'], new_model['model'], new_model['teff'], new_model['logg'], new_model['mass'], new_model['trgrad'], new_model['cmtop'], new_model['cmin'], new_model['euv'], new_model['fuv'], new_model['nuv'], new_model['j'])
    return 'Completed!'

#read_model_parameter_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/model_parameter_grid.csv')
#read_model_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M0_models.csv', m0_grid)

#upload_fits_file('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
all_fits_files = os.listdir('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files')
#for file in all_fits_files:
    #upload_fits_file(f'/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/{file}')
'''——————END MONGO DATABASE STUFF——————'''


'''——————START BASE64 STUFF——————'''
# def encode_file(filename):
#     with open(filename, "rb") as fits_file:
#         encoded_string = base64.b64encode(fits_file.read())
#         print(encoded_string)
#         return encoded_string

# def upload_fits_file(file_path):
#     print('Uploading fits file')
#     encoded_string = encode_file(file_path)
#     filename = os.path.basename(file_path)
#     new_file = {
#         'name' : filename,
#         'b64encoded_file' : encoded_string
#     }
#     print(new_file)
#     fits_files.insert_one(new_file)
#     return 'Completed!'

'''——————END BASE64 STUFF——————'''

#read_fits('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
#find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')