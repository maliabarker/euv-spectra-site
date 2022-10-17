from astropy.io import fits
import matplotlib.pyplot as plt
from euv_spectra_app.extensions import *
import io
import matplotlib
import mpld3

matplotlib.use('agg')

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