import numpy as np
import pandas as pd
import re
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from euv_spectra_app.models import ModelImport

# from ..models import ModelImport
# from ..extensions import db



# function to read in fits files and upload to DB
def read_table(file_path):

    # step 1: read in csv file with pandas
    DATAPATH = file_path
    dataset = pd.read_csv(DATAPATH)

    # step 2: iterate over each row to assign variables and input info accordingly:
    #     FROM FILENAME (use regex)
    #         - get model (ex: M0)
    #         - get teff
    #         - get logg
    #         - get TRgrad
    #         - get cmtop 
    #         - get cmmin
    #     FROM FLUXES
    #         - EUV
    #         - FUV
    #         - NUV
    #         - J
    for index, row in dataset.iterrows():
        model_str = row['Model']

        # step 3: append each new row & matching info to DB
        new_model = ModelImport(
            model = model_str[:2],
            teff = re.search("(?<=Teff=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            logg = re.search("(?<=logg=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            trgrad = re.search("(?<=TRgrad=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            cmtop = re.search("(?<=cmtop=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            cmin = re.search("(?<=cmin=)[^aA-zZ=][.]{0,1}\d*", model_str).group(),
            euv = row['F_EUV'],
            fuv = row['F_FUV'],
            nuv = row['F_NUV'],
            j = row['F_J']
        )

        print(new_model.model, new_model.teff, new_model.logg, new_model.trgrad, new_model.cmtop, new_model.cmin, new_model.euv, new_model.fuv, new_model.nuv, new_model.j)

read_table('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/tables/M0_models.csv')