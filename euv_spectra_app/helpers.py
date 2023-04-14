import json
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
            print(f'{attr_name} is an object')
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
        print(key, value)
        if key == 'pm_data' and value is not None:
            proper_motion_dict = value
            for pm_key, pm_value in proper_motion_dict.items():
                print(pm_key, pm_value)
                setattr(proper_motion_obj, pm_key, pm_value)
        elif key == 'fluxes' and value is not None:
            galex_fluxes_dict = value
            for flux_key, flux_value in galex_fluxes_dict.items():
                print(flux_key, flux_value)
                setattr(galex_fluxes_obj, flux_key, flux_value)
        setattr(stellar_target_obj, key, value)
    stellar_target_obj.pm_data = proper_motion_obj
    stellar_target_obj.fluxes = galex_fluxes_obj
    return stellar_target_obj


def create_plotly_graph(files):
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
                x=w_obs, y=f_obs, name=f"<b>Model {i+1} Spectrum (Best Match)</b>", line=dict(color=colors[i], width=1)))
        else:
            fig.add_trace(go.Scatter(
                x=w_obs, y=f_obs, name=f"<b>Model {i+1} Spectrum</b>", line=dict(color=colors[i], width=1)))
        i += 1
    # STEP 3: Add additional styling
    fig.update_layout(xaxis=dict(title='Wavelength (Å)', range=[10, 3000]),
                      yaxis=dict(title='Flux Density (erg/cm2/s/Å)',
                                 type='log', range=[-4, 7], tickformat='.0e'),
                      showlegend=True)
    return fig
