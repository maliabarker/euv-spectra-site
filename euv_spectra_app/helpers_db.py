from euv_spectra_app.extensions import *
import pandas as pd
import re
import os

'''———————MONGO DATABASE STUFF———————'''
def upload_fits_file(filepath):
    with open(filepath, "rb") as fits_file:
        filename = os.path.basename(filepath)
        print(filename)
        new_file = {
            'name' : filename,
            'file' : fits_file.read()
        }
        print(new_file)
        fits_files.insert_one(new_file)
        print('DONE!')
        return 'Completed'


def read_model_parameter_table(file_path):
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

def read_model_table(file_path, collection, model):
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
        file_str = row['Filename']

        # step 3: append each new row & matching info to DB
        new_model = {
            'fits_filename' : file_str,
            'subtype' : model,
            'teff' : row['Teff'],
            'logg' : row['Logg'],
            'mass' : row['Mass'],
            'trgrad' : float(re.search("(?<=TRgrad=)[^aA-zZ=][.]{0,1}\d*", file_str).group()),
            'cmtop' : float(re.search("(?<=cmtop=)[^aA-zZ=][.]{0,1}\d*", file_str).group()),
            'cmin' : float(re.search("(?<=cmin=)[^aA-zZ=][.]{0,1}\d*", file_str).group()),
            'euv' : row['EUV'],
            'fuv' : row['FUV'],
            'nuv' : row['NUV'],
        }

        collection.insert_one(new_model)

        print(new_model)
    return 'Completed!'



def read_photosphere_table(file_path):
    DATAPATH = file_path
    dataset = pd.read_csv(DATAPATH)
    print(f'Adding files')
    for index, row in dataset.iterrows():
        model_str = row['Filename']
        new_model = {
            'fits_filename' : model_str,
            'teff' : float(re.search("(?<=Teff=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'logg' : float(re.search("(?<=logg=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'mass' : float(re.search("(?<=mass=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'euv' : row['EUV'],
            'fuv' : row['FUV'],
            'nuv' : row['NUV']
        }
        photosphere_models.insert_one(new_model)
        print(new_model)
    return 'Completed!'



#read_photosphere_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/photosphere_fluxes.csv')
#read_model_parameter_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/model_parameter_grid.csv')
# read_model_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M0_photospheresubtractedfluxes.csv', m0_grid, 'M0')
# read_model_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M4_photospheresubtractedfluxes.csv', m4_grid, 'M4')
# read_model_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M6_photospheresubtractedfluxes.csv', m6_grid, 'M6')


# upload_fits_file('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=9.cmtop=6.cmin=3.7.gz.fits')
#all_fits_files = os.listdir('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files')
#for file in all_fits_files:
    #upload_fits_file(f'/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/{file}')
'''——————END MONGO DATABASE STUFF——————'''