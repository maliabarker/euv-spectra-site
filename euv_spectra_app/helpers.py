import json
import math
from astropy.io import fits
import plotly.graph_objects as go
from euv_spectra_app.extensions import *
from euv_spectra_app.models import StellarObject, ProperMotionData, GalexFluxes


def remove_objs_from_obj_dict(obj_dict):
            del obj_dict['fluxes']
            del obj_dict['pm_data']
            return obj_dict


def insert_data_into_form(obj, form):
    attrs = vars(obj)
    for attr_name, attr_value in attrs.items():
        if attr_name is 'fluxes':
            # is an object, go again
            insert_data_into_form(attr_value, form)
        elif hasattr(form, attr_name):
            # is not an object, check if it exists in form and if True, add to form data
            radio_input = getattr(form, attr_name)
            radio_input.choices.insert(
                0, (attr_value, attr_value))
            

def to_json(obj):
    # Check if the object is a simple data type
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Check if the object is a dictionary
    if isinstance(obj, dict):
        # Recursively call to_json on each value in the dictionary
        return {key: to_json(value) for key, value in obj.items()}

    # Check if the object is a list or tuple
    if isinstance(obj, (list, tuple)):
        # Recursively call to_json on each element in the list or tuple
        return [to_json(element) for element in obj]

    # If the object has a __dict__ attribute, it's probably a custom object
    if hasattr(obj, '__dict__'):
        # Recursively call to_json on each attribute of the object
        return to_json(obj.__dict__)

    # If all else fails, raise a TypeError
    print('JSON not of any valid object', obj, type(obj))
    raise TypeError(f'Object of type {type(obj)} is not JSON serializable')


def from_json(json_str):
    # Deserialize the JSON formatted string back into an object
    data = json.loads(json_str)
    stellar_target_obj = StellarObject()
    proper_motion_obj = ProperMotionData()
    galex_fluxes_obj = GalexFluxes()
    for key, value in data.items():
        if key == 'pm_data' and value is not None:
            proper_motion_dict = value
            for pm_key, pm_value in proper_motion_dict.items():
                setattr(proper_motion_obj, pm_key, pm_value)
        elif key == 'fluxes' and value is not None:
            galex_fluxes_dict = value
            for flux_key, flux_value in galex_fluxes_dict.items():
                setattr(galex_fluxes_obj, flux_key, flux_value)
        setattr(stellar_target_obj, key, value)
    stellar_target_obj.pm_data = proper_motion_obj
    stellar_target_obj.fluxes = galex_fluxes_obj
    return stellar_target_obj


def create_plotly_graph(files):
    """Creates a plotly graph with data from FITS files.
    
    Args:
        files: A dictionary of dictionaries with FITS files to pull data from and a file tag to include in the legend.
    
    Returns:
        A plotly figure. Will then be json serialized and sent to the front end.
    """
    # STEP 1: initialize figure
    fig = go.Figure()
    # colors = ['#2E42FC', "#7139F1", "#9A33EA", "#C32DE3",
    #           "#EE26DB", "#FE63A0", "#FE8F77", "#FDAE5A"]
    colors = ['#2E42FC', '#EE26DB', '#FF79AE', '#FE6201', '#FFBC28', '#DB2681', '#BBBBBB', '#00E4B0', '#7FFF1D']
    galex_x = [value['wavelength'] for key, value in files.items() if 'galex' in key]
    galex_y = [value['flux_density'] for key, value in files.items() if 'galex' in key]
    galex_names = [value['name'] for key, value in files.items() if 'galex' in key]
    galex_symbols = []
    all_buttons = []
    model_buttons = []
    flux_buttons = []
    # STEP 2: for each file, add new trace with data
    for key, value in files.items():
        if 'model' in key:
            # get model data from fits file
            hst = fits.open(value['filepath'])
            data = hst[1].data
            w_obs = data['WAVELENGTH'][0]
            f_obs = data['FLUX'][0]
            # get final model name by checking for flags or index #
            model_name = f"<b>Model {value['index'] + 1} Spectrum</b>"
            if value['index'] == 0:
                if 'flag' in value:
                    value['flag'] = f'{value["flag"]}, Best Match'
                else:
                    value['flag'] = '(Best Match)'
            if 'flag' in value:
                model_name = f"<b>Model {value['index'] + 1} Spectrum ({value['flag']})</b>"
            # Plot model
            fig.add_trace(go.Scatter(
                x=w_obs, y=f_obs, name=model_name, line=dict(color=colors[value['index']], width=1)))
            all_buttons.append(True)
            model_buttons.append(True)
            flux_buttons.append(False)
            # Group NUV, FUV, and EUV data points
            fig.add_trace(go.Scatter(
                x=[2315, 1542, 500], 
                y=[value['nuv'], value['fuv'], value['euv']],
                name=f'Model {value["index"] + 1} Fluxes',
                mode='markers',
                marker=dict(color=colors[value['index']], line=dict(color="Black", width=2), size=12),
                hovertemplate='<b>%{text}</b>: %{y:.2f}<extra></extra>',
                text=['NUV', 'FUV', 'EUV'],
                legendgroup=f'Model {value["index"] + 1} Fluxes',
            ))
            all_buttons.append(True)
            model_buttons.append(False)
            flux_buttons.append(True)
            
        # get symbol of each galex flux and append to galex data
        elif 'galex' in key:
            if 'flag' in value and value['flag'] == 'saturated':
                galex_symbols.append('arrow-up')
            elif 'flag' in value and value['flag'] == 'upper_limit':
                galex_symbols.append('arrow-down')
            else:
                galex_symbols.append('circle')
    # plot the GALEX data points
    fig.add_trace(go.Scatter(
        x=galex_x, y=galex_y, name='GALEX Processed Fluxes',
        mode='markers', marker=dict(color='Black', symbol=galex_symbols, size=10),
        hovertemplate='<b>%{text}</b>: %{y:.2f}<extra></extra>',
        text=galex_names,
        legendgroup='GALEX Processed Fluxes'
    ))
    all_buttons.append(True)
    model_buttons.append(False)
    flux_buttons.append(True)

    # Generate the menu buttons dynamically
    buttons = list([
        dict(label="View All", method="update", args=[{"visible": all_buttons}, {"title": "All"}]),
        dict(label="View All Models", method="update", args=[{"visible": model_buttons}, {"title": "All Models"}]),
        dict(label="View All Fluxes", method="update", args=[{"visible": flux_buttons}, {"title": "All Fluxes"}])
    ])

    # STEP 3: Add additional styling
    fig.update_layout(
        xaxis=dict(title='Wavelength (Å)', range=[10, 3000]), # Set x axis constraints for first load
        yaxis=dict(title='Flux Density (erg/cm2/s/Å)', type='log', range=[-4, 7], tickformat='.0e'), # Set y axis constraints for first load and scale logarithmically
        showlegend=True, # Show the legend
        # hovermode="x unified",
        updatemenus=[
            go.layout.Updatemenu(
                buttons=buttons, # Add true false button dicts for each menu option
                direction="down", # Set to a dropdown menu
                pad={"r": 10, "t": 10},
                showactive=True, # Show the active menu option
                x=0.5,  # Set x value to 0.5 for center alignment
                xanchor="center",  # Set xanchor to "center" for center alignment
                y=1.1,
                yanchor="top"
            ),
        ]
    )
    return fig


def test_new_early_m_equation(flux_val, flux_err, flux_type):
    """
    FUV = 10 ^ ( 1.17 * log10(NUV) - 1.26 )
    NUV = 10 ^ ( ( log10(FUV) + 1.26 ) / 1.17 )
    """
    pred_flux = None
    if flux_type == 'fuv':
        # predicting for NUV
        pred_flux = pow(10, (( math.log10(flux_val) + 1.26 ) / 1.17 ))
    elif flux_type == 'nuv':
        # predicting for FUV
        pred_flux = pow(10, ( 1.17 * math.log10(flux_val) - 1.26 ))
    return pred_flux


def test_new_late_m_equation(flux_val, flux_err, flux_type):
    """
    FUV = 10 ^ ( 0.98 * log10(NUV) - 0.47 )
    NUV = 10 ^ ( ( log10(FUV) + 0.47 ) / 0.98 )
    """
    pred_flux = None
    if flux_type == 'fuv':
        # predicting for NUV
        pred_flux = pow(10, (( math.log10(flux_val) + 0.47 ) / 0.98 ))
    elif flux_type == 'nuv':
        # predicting for FUV
        pred_flux = pow(10, ( 0.98 * math.log10(flux_val) - 0.47 ))
    return pred_flux