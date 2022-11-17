from cProfile import label
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
    print(f'SCALE {scale}')
    
    #STEP 2: Check if any fluxes are null (don't continue if true)
    if session['fuv'] != 'null':
        print(f'CONVERTING FUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        upper_lim_fuv = session['fuv'] + session['fuv_err']
        lower_lim_fuv = session['fuv'] - session['fuv_err']
        fuv_arb_wv = 1542.3

        converted_fuv = ((3e-5) * (session['fuv']* 10**-6)) / pow(fuv_arb_wv, 2)
        converted_upper_lim_fuv = ((3e-5) * (upper_lim_fuv* 10**-6)) / pow(fuv_arb_wv, 2)
        converted_lower_lim_fuv = ((3e-5) * (lower_lim_fuv* 10**-6)) / pow(fuv_arb_wv, 2)
        print(f'Converted fluxes: FUV {converted_fuv} ERR up {converted_upper_lim_fuv} low {converted_lower_lim_fuv}')
        
        #STEP 4: Multiply flux by scale
        scaled_fuv = converted_fuv * scale
        scaled_upper_lim_fuv = converted_upper_lim_fuv * scale
        scaled_lower_lim_fuv = converted_lower_lim_fuv * scale
        print(f'Scaled fluxes: FUV {scaled_fuv} ERR up {scaled_upper_lim_fuv} low {scaled_lower_lim_fuv}')
        
        #STEP 5: Subtract photospheric flux
        photospheric_subtracted_fuv = scaled_fuv - (photo_fluxes['fuv'] / (10**8))
        photospheric_subtracted_upper_lim_fuv = scaled_upper_lim_fuv - (photo_fluxes['fuv'] / (10**8))
        photospheric_subtracted_lower_lim_fuv = scaled_lower_lim_fuv - (photo_fluxes['fuv'] / (10**8))

        up_fuv = photospheric_subtracted_upper_lim_fuv - photospheric_subtracted_fuv
        low_fuv = photospheric_subtracted_fuv - photospheric_subtracted_lower_lim_fuv

        avg_err_fuv = (up_fuv + low_fuv) / 2

        print(f'Photospheric subtracted fluxes: FUV {photospheric_subtracted_fuv} ERR {avg_err_fuv}')
        
        #STEP 6: Add new fluxes to dict
        returned_fluxes['fuv'] = photospheric_subtracted_fuv * (10**8)
        returned_fluxes['fuv_err'] = avg_err_fuv * (10**8)
    
    if session['nuv'] != 'null':
        print(f'CONVERTING NUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        upper_lim_nuv = session['nuv'] + session['nuv_err']
        lower_lim_nuv = session['nuv'] - session['nuv_err']

        nuv_arb_wv = 2274.4

        converted_nuv = ((3e-5) * (session['nuv']* 10**-6)) / pow(nuv_arb_wv, 2)
        converted_upper_lim_nuv = ((3e-5) * (upper_lim_nuv* 10**-6)) / pow(nuv_arb_wv, 2)
        converted_lower_lim_nuv = ((3e-5) * (lower_lim_nuv* 10**-6)) / pow(nuv_arb_wv, 2)

        print(f'Converted fluxes: NUV {converted_nuv} ERR up {converted_upper_lim_nuv} low {converted_lower_lim_nuv}')
        
        #STEP 4: Multiply flux by scale
        scaled_nuv = converted_nuv * scale
        scaled_upper_lim_nuv = converted_upper_lim_nuv * scale
        scaled_lower_lim_nuv = converted_lower_lim_nuv * scale
        print(f'Scaled fluxes: NUV {scaled_nuv} ERR up {scaled_upper_lim_nuv} low {scaled_lower_lim_nuv}')
        
        #STEP 5: Subtract photospheric flux
        #NOTE DO WE USE SAME PHOTOSPHERIC FLUX FOR ERROR VALUES???
        photospheric_subtracted_nuv = scaled_nuv - (photo_fluxes['nuv'] / (10**8))
        photospheric_subtracted_upper_lim_nuv = scaled_upper_lim_nuv - (photo_fluxes['nuv'] / (10**8))
        photospheric_subtracted_lower_lim_nuv = scaled_lower_lim_nuv - (photo_fluxes['nuv'] / (10**8))

        up_nuv = photospheric_subtracted_upper_lim_nuv - photospheric_subtracted_nuv
        low_nuv = photospheric_subtracted_nuv - photospheric_subtracted_lower_lim_nuv

        avg_err_nuv = (up_nuv + low_nuv) / 2

        print(f'Photospheric subtracted fluxes: NUV {photospheric_subtracted_nuv} ERR {avg_err_nuv}')
        
        #STEP 6: Add new fluxes to dict
        returned_fluxes['nuv'] = photospheric_subtracted_nuv * (10**8)
        returned_fluxes['nuv_err'] = avg_err_nuv * (10**8)
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
    # print(w_obs)
    # print(f_obs)
    
    fig = plt.figure()
    fig.set_size_inches(9, 4)
    '''FOR FUTURE WITH MULTIPLE LINES:
        colors=[list of colors]
        line1, = plt.plot(w_obs, f_obs, color=colors[0], label='Spectrum 1 (Best Match), χ2=<value>')
        line2, = plt.plot(w_obs, f_obs, color=colors[1], label='Spectrum 2, χ2=<value>')...
        plt.legend(handles=[line1, line2])
    '''
    plt.plot(w_obs, f_obs, color='#5240f7', label='Spectrum 1 (Best Match), χ2=?')
    plt.xlabel('Wavelength (Å)')
    plt.ylabel('Flux Density (erg/cm2/s/Å)')
    plt.yscale('log')
    # set x lim to 10-100
    plt.xlim(10,3000)
    # set y lim to min flux and max flux
    plt.ylim(1e+6,1e+18)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.175), ncol=3, fancybox=True, shadow=True)
    # plt.legend(loc='lower right')
    # PLOT ALL CHI SQUARED MATCHES AND ADD LEGEND
    # <!-- Add legend for lines (with intent of plotting all matching chi squared lines on single graph) -->
    return fig

def convert_fig_to_html(fig):
    html_string = mpld3.fig_to_html(fig, template_type='simple')
    return html_string


#read_fits('/Users/maliabarker/Desktop/NASA/EUV_Spectra_Site/euv_spectra_app/static/fits_files/M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')

#file = find_fits_file('M0.Teff=3850.logg=4.78.TRgrad=7.5.cmtop=5.5.cmin=3.5.7.gz.fits')
#html_str = create_graph(file, 'M0')