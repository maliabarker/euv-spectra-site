from astropy.io import fits
from euv_spectra_app.extensions import *
import io
import plotly.graph_objects as go

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
    # print(f'CONVERTED DIST RAD, {radius_cm} {distance_cm}')

    scale = (distance_cm**2) / (radius_cm**2)
    # print(f'SCALE {scale}')
    
    #STEP 2: Check if any fluxes are null (don't continue if true)
    if session['fuv'] != 'null':
        # print(f'CONVERTING FUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        upper_lim_fuv = session['fuv'] + session['fuv_err']
        lower_lim_fuv = session['fuv'] - session['fuv_err']
        fuv_arb_wv = 1542.3

        converted_fuv = ((3e-5) * (session['fuv']* 10**-6)) / pow(fuv_arb_wv, 2)
        converted_upper_lim_fuv = ((3e-5) * (upper_lim_fuv* 10**-6)) / pow(fuv_arb_wv, 2)
        converted_lower_lim_fuv = ((3e-5) * (lower_lim_fuv* 10**-6)) / pow(fuv_arb_wv, 2)
        # print(f'Converted fluxes: FUV {converted_fuv} ERR up {converted_upper_lim_fuv} low {converted_lower_lim_fuv}')
        
        #STEP 4: Multiply flux by scale
        scaled_fuv = converted_fuv * scale
        scaled_upper_lim_fuv = converted_upper_lim_fuv * scale
        scaled_lower_lim_fuv = converted_lower_lim_fuv * scale
        # print(f'Scaled fluxes: FUV {scaled_fuv} ERR up {scaled_upper_lim_fuv} low {scaled_lower_lim_fuv}')
        
        #STEP 5: Subtract photospheric flux
        photospheric_subtracted_fuv = scaled_fuv - (photo_fluxes['fuv'])
        photospheric_subtracted_upper_lim_fuv = scaled_upper_lim_fuv - (photo_fluxes['fuv'])
        photospheric_subtracted_lower_lim_fuv = scaled_lower_lim_fuv - (photo_fluxes['fuv'])

        up_fuv = photospheric_subtracted_upper_lim_fuv - photospheric_subtracted_fuv
        low_fuv = photospheric_subtracted_fuv - photospheric_subtracted_lower_lim_fuv

        avg_err_fuv = (up_fuv + low_fuv) / 2

        # print(f'Photospheric subtracted fluxes: FUV {photospheric_subtracted_fuv} ERR {avg_err_fuv}')
        
        #STEP 6: Add new fluxes to dict
        # print('———————————————————')
        # print(photospheric_subtracted_fuv)
        # print(avg_err_fuv)
        returned_fluxes['fuv'] = photospheric_subtracted_fuv
        returned_fluxes['fuv_err'] = avg_err_fuv
    
    if session['nuv'] != 'null':
        # print(f'CONVERTING NUV')
        
        #STEP 3: Convert GALEX mJy to erg/s/cm2/A
        upper_lim_nuv = session['nuv'] + session['nuv_err']
        lower_lim_nuv = session['nuv'] - session['nuv_err']

        nuv_arb_wv = 2274.4

        converted_nuv = ((3e-5) * (session['nuv']* 10**-6)) / pow(nuv_arb_wv, 2)
        converted_upper_lim_nuv = ((3e-5) * (upper_lim_nuv* 10**-6)) / pow(nuv_arb_wv, 2)
        converted_lower_lim_nuv = ((3e-5) * (lower_lim_nuv* 10**-6)) / pow(nuv_arb_wv, 2)

        # print(f'Converted fluxes: NUV {converted_nuv} ERR up {converted_upper_lim_nuv} low {converted_lower_lim_nuv}')
        
        #STEP 4: Multiply flux by scale
        scaled_nuv = converted_nuv * scale
        scaled_upper_lim_nuv = converted_upper_lim_nuv * scale
        scaled_lower_lim_nuv = converted_lower_lim_nuv * scale
        # print(f'Scaled fluxes: NUV {scaled_nuv} ERR up {scaled_upper_lim_nuv} low {scaled_lower_lim_nuv}')
        
        #STEP 5: Subtract photospheric flux
        #NOTE DO WE USE SAME PHOTOSPHERIC FLUX FOR ERROR VALUES???
        photospheric_subtracted_nuv = scaled_nuv - (photo_fluxes['nuv'])
        photospheric_subtracted_upper_lim_nuv = scaled_upper_lim_nuv - (photo_fluxes['nuv'])
        photospheric_subtracted_lower_lim_nuv = scaled_lower_lim_nuv - (photo_fluxes['nuv'])

        up_nuv = photospheric_subtracted_upper_lim_nuv - photospheric_subtracted_nuv
        low_nuv = photospheric_subtracted_nuv - photospheric_subtracted_lower_lim_nuv

        avg_err_nuv = (up_nuv + low_nuv) / 2

        # print(f'Photospheric subtracted fluxes: NUV {photospheric_subtracted_nuv} ERR {avg_err_nuv}')
        
        #STEP 6: Add new fluxes to dict
        returned_fluxes['nuv'] = photospheric_subtracted_nuv
        returned_fluxes['nuv_err'] = avg_err_nuv
    return returned_fluxes



def find_fits_file(filename):
    # Get file from file structure
    # EXAMPLE: file = full_filepath/fits_files/{subtype}/{filename}
    # filepath = f'/fits_files/{subtype}/{filename}'

    item = fits_files.find_one({'name': filename})
    if item:
        file = io.BytesIO(item['file'])
        return file



def create_plotly_graph(files, model_data):
    # STEP 1: initialize figure
    fig = go.Figure()
    colors = ['#2E42FC', "#7139F1", "#9A33EA", "#C32DE3", "#EE26DB", "#FE63A0", "#FE8F77", "#FDAE5A"]
    
    # STEP 2: for each file, add new trace with data
    i = 0
    while i <= len(files) - 1:
        print(f'FILE {files[i]}')
        hst = fits.open(files[i])
        data = hst[1].data
        w_obs = data['WAVELENGTH'][0]
        f_obs = data['FLUX'][0]

        print('FILE DATA')
        print(w_obs[:5])
        print(f_obs[:5])

        if i == 0:
            fig.add_trace(go.Scatter(x=w_obs, y=f_obs, name=f"<b>Spectrum {i+1} (Best Match)</b> <br> FUV={round(model_data[i]['fuv'], 2)} NUV={round(model_data[i]['nuv'], 2)}", line=dict(color=colors[i], width=1)))
        else:
            fig.add_trace(go.Scatter(x=w_obs, y=f_obs, name=f"<b>Spectrum {i+1}</b> <br> FUV={round(model_data[i]['fuv'], 2)} NUV={round(model_data[i]['nuv'], 2)}", line=dict(color=colors[i], width=1)))
        i += 1

    # STEP 3: Add additional styling
    fig.update_layout(xaxis=dict(title='Wavelength (Å)', range=[10, 3000]),
                      yaxis=dict(title='Flux Density (erg/cm2/s/Å)', type='log', range=[-4, 7], tickformat='e'),
                      showlegend=True)
    return fig