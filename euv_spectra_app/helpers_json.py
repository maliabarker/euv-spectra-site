import json
from euv_spectra_app.helpers_astroquery import StellarTarget, ProperMotionDataOld, GalexFluxesOld
from euv_spectra_app.models import StellarObject, ProperMotionData, GalexFluxes, PegasusGrid, PhoenixModel

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
    stellar_target_obj = StellarTarget()
    proper_motion_obj = ProperMotionDataOld()
    galex_fluxes_obj = GalexFluxesOld()
    for key, value in data.items():
        print(key, value)
        if key == 'proper_motion_data' and value is not None:
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
    stellar_target_obj.proper_motion_data = proper_motion_obj
    stellar_target_obj.fluxes = galex_fluxes_obj
    return stellar_target_obj

def from_json_new(json_str):
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
