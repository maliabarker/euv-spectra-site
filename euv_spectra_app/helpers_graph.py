from astropy.io import fits
from euv_spectra_app.extensions import *
import plotly.graph_objects as go


def create_plotly_graph(files, model_data):
    """Creates a plotly graph with data from FITS files.
    
    Args:
        files: A list of FITS files to pull data from.
        model_data: A list of lists that represents the data of the model corresponding
         to the FITS file.
    
    Returns:
        A plotly figure. Will then be json serialized and sent to the front end.
    """
    # STEP 1: initialize figure
    fig = go.Figure()
    colors = ['#2E42FC', "#7139F1", "#9A33EA", "#C32DE3",
              "#EE26DB", "#FE63A0", "#FE8F77", "#FDAE5A"]
    # STEP 2: for each file, add new trace with data
    i = 0
    while i <= len(files) - 1:
        hst = fits.open(files[i])
        data = hst[1].data
        w_obs = data['WAVELENGTH'][0]
        f_obs = data['FLUX'][0]
        if i == 0:
            fig.add_trace(go.Scatter(
                x=w_obs, y=f_obs, name=f"<b>Spectrum {i+1} (Best Match)</b> <br> FUV={round(model_data[i]['fuv'], 2)} NUV={round(model_data[i]['nuv'], 2)}", line=dict(color=colors[i], width=1)))
        else:
            fig.add_trace(go.Scatter(
                x=w_obs, y=f_obs, name=f"<b>Spectrum {i+1}</b> <br> FUV={round(model_data[i]['fuv'], 2)} NUV={round(model_data[i]['nuv'], 2)}", line=dict(color=colors[i], width=1)))
        i += 1
    # STEP 3: Add additional styling
    fig.update_layout(xaxis=dict(title='Wavelength (Å)', range=[10, 3000]),
                      yaxis=dict(title='Flux Density (erg/cm2/s/Å)',
                                 type='log', range=[-4, 7], tickformat='e'),
                      showlegend=True)
    return fig
