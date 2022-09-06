

# function to read in fits files and upload to DB
def read_fits(file):
    '''
    step 1: read in csv file with pandas
    step 2: iterate over each row to assign variables and input info accordingly:
        FROM FILENAME (use regex)
            - get model (ex: M0)
            - get teff
            - get logg
            - get TRgrad
            - get cmtop 
            - get cmmin
        FROM FLUXES
            - EUV
            - FUV
            - NUV
            - J
    step 3: append each new row & matching info to DB
    '''
    