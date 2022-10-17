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
            'teff' : float(re.search("(?<=Teff=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'logg' : float(re.search("(?<=logg=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'mass' : row['Mass'],
            'trgrad' : float(re.search("(?<=TRgrad=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'cmtop' : float(re.search("(?<=cmtop=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'cmin' : float(re.search("(?<=cmin=)[^aA-zZ=][.]{0,1}\d*", model_str).group()),
            'euv' : row['F_EUV'],
            'fuv' : row['F_FUV'],
            'nuv' : row['F_NUV'],
            'j' : row['F_J']
        }

        collection.insert_one(new_model)

        print(new_model['fits_filename'], new_model['model'], new_model['teff'], new_model['logg'], new_model['mass'], new_model['trgrad'], new_model['cmtop'], new_model['cmin'], new_model['euv'], new_model['fuv'], new_model['nuv'], new_model['j'])
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
        starter_photosphere_models.insert_one(new_model)
        print(new_model)
    return 'Completed!'

read_photosphere_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/starterphotosphere_fluxes.csv')
#read_model_parameter_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/model_parameter_grid.csv')
#read_model_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M0_models.csv', m0_grid)

#upload_fits_file('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
#all_fits_files = os.listdir('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files')
#for file in all_fits_files:
    #upload_fits_file(f'/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/{file}')
'''——————END MONGO DATABASE STUFF——————'''