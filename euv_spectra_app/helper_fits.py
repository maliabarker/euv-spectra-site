from astropy.io import fits
import matplotlib.pyplot as plt
from euv_spectra_app.extensions import *
import io
import matplotlib
import mpld3

matplotlib.use('agg')

def convert_and_scale_fluxes(session, photo_fluxes):
    returned_fluxes = {
        'fuv': session['fuv'],
        'fuv_err': session['fuv_err'],
        'nuv': session['nuv'],
        'nuv_err': session['nuv_err']
    }

    #STEP 1: CONVERT & Compute scale value
    radius_cm = session['stell_rad'] * 6.9e10
    distance_cm = session['dist'] * 3.08567758e18
    print(f'CONVERTED DIST RAD, {radius_cm} {distance_cm}')

    scale = (distance_cm**2) / (radius_cm**2)

    #STEP 2: Check if any fluxes are null (don't continue if true)
    if session['fuv'] != 'null':
        print(f'CONVERTING FUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        fuv_arb_wv = 1542.3
        converted_fuv = ((3e-5) * (session['fuv']* 10**-6)) / pow(fuv_arb_wv, 2)
        converted_fuv_err = ((3e-5) * (session['fuv_err']* 10**-6)) / pow(fuv_arb_wv, 2)
        print(f'Converted fluxes: FUV {converted_fuv} ERR {converted_fuv_err}')
        
        #STEP 4: Multiply flux by scale
        print(f'SCALE {scale}')
        scaled_fuv = converted_fuv * scale
        scaled_fuv_err = converted_fuv_err * scale
        print(f'Scaled fluxes: FUV {scaled_fuv} ERR {scaled_fuv_err}')
        print(f"PHOTO FLUXES: FUV {photo_fluxes['fuv']}")
        
        #STEP 5: Subtract photospheric flux
        #NOTE DO WE USE SAME PHOTOSPHERIC FLUX FOR ERROR VALUES???
        photospheric_subtracted_fuv = scaled_fuv - photo_fluxes['fuv']
        photospheric_subtracted_fuv_err = scaled_fuv_err - photo_fluxes['fuv']
        print(f'Photospheric subtracted fluxes: FUV {photospheric_subtracted_fuv} ERR {photospheric_subtracted_fuv_err}')
        
        #STEP 6: Add new fluxes to dict
        returned_fluxes['fuv'] = photospheric_subtracted_fuv
        returned_fluxes['fuv_err'] = photospheric_subtracted_fuv_err
    
    if session['nuv'] != 'null':
        print(f'CONVERTING NUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        nuv_arb_wv = 2274.4
        converted_nuv = ((3e-5) * (session['nuv']* 10**-6)) / pow(nuv_arb_wv, 2)
        converted_nuv_err = ((3e-5) * (session['nuv_err']* 10**-6)) / pow(nuv_arb_wv, 2)
        print(f'Converted fluxes: NUV {converted_nuv} ERR {converted_nuv_err}')
        
        #STEP 4: Multiply flux by scale
        print(f'SCALE {scale}')
        scaled_nuv = converted_nuv * scale
        scaled_nuv_err = converted_nuv_err * scale
        print(f'Scaled fluxes: NUV {scaled_nuv} ERR {scaled_nuv_err}')
        
        #STEP 5: Subtract photospheric flux
        #NOTE DO WE USE SAME PHOTOSPHERIC FLUX FOR ERROR VALUES???
        photospheric_subtracted_nuv = scaled_nuv - photo_fluxes['nuv']
        photospheric_subtracted_nuv_err = scaled_nuv_err - photo_fluxes['nuv']
        print(f'Photospheric subtracted fluxes: NUV {photospheric_subtracted_nuv} ERR {photospheric_subtracted_nuv_err}')
        
        #STEP 6: Add new fluxes to dict
        returned_fluxes['nuv'] = photospheric_subtracted_nuv
        returned_fluxes['nuv_err'] = photospheric_subtracted_nuv_err
    return returned_fluxes

def find_fits_file(filename):
    print('finding fits')
    item = fits_files.find_one({'name': filename})
    file = io.BytesIO(item['file'])
    return file

def create_graph(file, session):
    hst = fits.open(file)
    data = hst[1].data
    w_obs = data['WAVELENGTH'][0]
    f_obs = data['FLUX'][0]
    print(w_obs)
    print(f_obs)

    fig = plt.figure()
    plt.plot(w_obs, f_obs, color='#5240f7')
    plt.xlabel('Wavelength (Å)')
    plt.ylabel('Flux Density (erg/cm2/s/Å)')
    plt.yscale('log')
    # set x lim to 10-100
    plt.xlim(1000,3000)
    # set y lim to min flux and max flux
    plt.ylim(1e-16,5e-11)
    # plt.legend(loc='lower right')
    plt.title(session['model_subtype'])
    # PLOT ALL CHI SQUARED MATCHES AND ADD LEGEND
    # 
    return fig

def convert_fig_to_html(fig):
    html_string = mpld3.fig_to_html(fig, template_type='simple')
    return html_string


#read_fits('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')

#file = find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
#html_str = create_graph(file, 'M0')