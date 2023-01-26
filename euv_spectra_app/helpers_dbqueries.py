from euv_spectra_app.extensions import *

def find_matching_subtype(session):
    """Matches to a subtype in the PEGASUS grid.

    Searches the PEGASUS grid for stellar subtype match using stellar effective 
    temperature, surface gravity and mass. Temperature is weighted higher than the 
    other variables.

    Args:
        session: A Flask session instance that needs to include the variables teff, 
        logg, and mass.

    Returns:
        One MongoDB document from the model_parameter_grid collection corresponding to 
        the stellar subtype that best matches the user's target based on temperature, 
        surface gravity, and mass.
    """
    matching_subtype = model_parameter_grid.aggregate([
        {'$facet': {
            'matchedTeff': [
                # Project a diff field that's the absolute difference along with the original doc.
                {'$project': {'diff': {'$abs': {'$subtract': [
                    float(session['teff']), '$teff']}}, 'doc': '$$ROOT'}},
                # Order the docs by diff, Take the first one, Add new weighted field
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 10}}],
            'matchedLogg': [
                {'$project': {'diff': {'$abs': {'$subtract': [
                    float(session['logg']), '$logg']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 5}}],
            'matchedMass': [
                {'$project': {'diff': {'$abs': {'$subtract': [
                    float(session['mass']), '$mass']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 2}}]
        }},
        # get them together. Should list all rules from above
        {'$project': {'doc': {'$concatArrays': [
            "$matchedTeff", "$matchedLogg", "$matchedMass"]}}},
        # split them apart, order by weight & desc, return top document
        {'$unwind': "$doc"}, {'$sort': {"doc.weight": -1}}, {'$limit': 1},
        # reshape to retrieve documents in its original format
        {'$project': {'_id': "$doc._id", 'model': "$doc.doc.model",
                      'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass"}}
    ])
    subtype_doc = ''
    for doc in matching_subtype:
        subtype_doc = model_parameter_grid.find_one(doc['_id'])
    return subtype_doc


def find_matching_photosphere(session):
    """Matches to a PHOENIX photosphere model.

    Searches a grid of custom PHOENIX calculated photosphere models for best match
    on stellar effective temperature and surface gravity. This will be used in later
    functions to subtract photospheric contributions in the GALEX FUV and NUV flux 
    densities.

    Args:
        session: A Flask session instance that needs to include the variables teff 
        and logg.

    Returns:
        One MongoDB document from the photosphere_models collection corresponding to 
        the photosphere that best matches the user's target based on temperature 
        and surface gravity.
    """
    # TODO: iterate list and create pointer for lowest diff value ** reduce On^2 to On
    matching_temp = photosphere_models.aggregate([
        {'$project': {'diff': {'$abs': {'$subtract': [
            session['teff'], '$teff']}}, 'doc': '$$ROOT'}},
        {'$sort': {'diff': 1}},
        {'$limit': 1}
    ])
    teff = ''
    for doc in matching_temp:
        teff = doc['doc']['teff']
    matching_photospheric_flux = photosphere_models.aggregate([
        {'$match': {'teff': teff}},
        {'$facet': {
            'matchedLogg': [
                {'$project': {'diff': {'$abs': {'$subtract': [
                    session['logg'], '$logg']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}],
        }},
        # get them together. Should list all rules from above
        {'$project': {'doc': {'$concatArrays': ["$matchedLogg"]}}},
        # split them apart, order by weight & desc, return top document
        {'$unwind': "$doc"}, {'$sort': {"doc.diff": -1}}, {'$limit': 1},
        # reshape to retrieve documents in its original format
        {'$project': {'_id': "$doc._id", 'fits_filename': "$doc.doc.fits_filename", 'teff': "$doc.doc.teff",
                      'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass", 'euv': "$doc.doc.euv", 'nuv': "$doc.doc.nuv", 'fuv': "$doc.doc.fuv"}}
    ])
    matching_photosphere_doc = ''
    for doc in matching_photospheric_flux:
        matching_photosphere_doc = doc
    return matching_photosphere_doc


def get_models_with_chi_squared(session, model_collection):
    """Calculates chi square (χ2) values.
    
    Calculates the chi square values of FUV and NUV flux densities of each model in
    the stellar subgrid compared to the FUV and NUV flux densities of the user's 
    inputted stellar object.

    Args:
        session: A Flask session variable that must include corrected_nuv and 
         corrected_fuv key value pairs, which are converted and photosphere subtracted 
         GALEX flux density values calculated from the convert_and_scale_fluxes function 
         in the helpers_flux module.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.
    
    Returns:
        The matching MongoDB model collection with all documents containing an 
        additional field, 'chi_squared', that has the calculated chi sqaure value using
        the equation:

        ((model_nuv - galex_nuv) ** 2 / galex_nuv) + ((model_fuv - galex_fuv) ** 2 / galex_fuv)

        The returned collection is sorted from lowest to highest chi squared value.
    """
    models_with_chi_squared = db.get_collection(model_collection).aggregate([
        {"$addFields": {"chi_squared": {"$round": [{"$add":
            # FOR NUV { "$divide": [ { "$pow": [ { "$subtract": [ "$NUV", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }
            [{"$divide": [{"$pow": [{"$subtract": ["$nuv", session['corrected_nuv']]}, 2]}, session['corrected_nuv']]},
            # FOR FUV { "$divide": [ { "$pow": [ { "$subtract": [ "$FUV", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }
            {"$divide": [{"$pow": [{"$subtract": ["$fuv", session['corrected_fuv']]}, 2]}, session['corrected_fuv']]}]
        }, 2]}}},
        {"$sort": {"chi_squared": 1}}
    ])
    return models_with_chi_squared


def get_models_with_weighted_fuv(session, model_collection):
    """Calculates chi square value with weighted preference on FUV flux.

    Calculates the chi square values of FUV and NUV flux densities of each model in
    the stellar subgrid compared to the FUV and NUV flux densities of the user's 
    inputted stellar object. Preference is given to FUV by only returning documents
    in the collection that have a chi square value of FUV greater than the chi
    square value of NUV.

    Args:
        session: A Flask session variable that must include corrected_nuv and 
         corrected_fuv key value pairs, which are converted and photosphere subtracted 
         GALEX flux density values calculated from the convert_and_scale_fluxes function 
         in the helpers_flux module.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.

    Returns:
        The matching MongoDB model collection with all documents having a FUV chi 
        square value less than the NUV chi square value. All documents contain an 
        additional field, 'chi_squared', that has the calculated chi square value and 
        FUV and NUV combined using the equation:

        ((model_nuv - galex_nuv) ** 2 / galex_nuv) + ((model_fuv - galex_fuv) ** 2 / galex_fuv)

        The returned collection is sorted from lowest to highest chi squared value.
    """
    models_with_fuv_less_than_nuv = db.get_collection(model_collection).aggregate([
        {"$addFields": {
            "chi_squared_fuv": {"$round": [{"$divide": [{"$pow": [{"$subtract": ["$fuv", session['corrected_fuv']]}, 2]}, session['corrected_fuv']]}, 2]},
            "chi_squared_nuv": {"$round": [{"$divide": [{"$pow": [{"$subtract": ["$nuv", session['corrected_nuv']]}, 2]}, session['corrected_nuv']]}, 2]},
            "chi_squared": {"$round": [{"$add": [
                {"$divide": [{"$pow": [{"$subtract": [
                    "$nuv", session['corrected_nuv']]}, 2]}, session['corrected_nuv']]},
                {"$divide": [{"$pow": [{"$subtract": ["$fuv", session['corrected_fuv']]}, 2]}, session['corrected_fuv']]}]
            }, 2]}
        }},
        {"$sort": {"chi_squared": 1}}
    ])
    final_models = []
    for model in list(models_with_fuv_less_than_nuv):
        if model['chi_squared_fuv'] < model['chi_squared_nuv']:
            final_models.append(model)
    return final_models


def get_models_within_limits(session, model_collection):
    """Searches for models within limits of GALEX FUV and NUV flux densities.

    Args:
        session: A Flask session variable that must include corrected_nuv, 
         corrected_nuv_err, corrected_fuv, and corrected_fuv_err key value pairs, which 
         are converted and photosphere subtracted GALEX flux density values calculated
         from the convert_and_scale_fluxes function in the helpers_flux module.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.

    Returns:
        MongoDB documents in the collection that have an FUV flux density value within 
        the upper and lower limits of the GALEX FUV flux density and an NUV flux 
        density value within the upper and lower limits of the GALEX NUV flux density.
    """
    fuv_lower_lim = session['corrected_fuv'] - session['corrected_fuv_err']
    fuv_upper_lim = session['corrected_fuv'] + session['corrected_fuv_err']
    nuv_lower_lim = session['corrected_nuv'] - session['corrected_nuv_err']
    nuv_upper_lim = session['corrected_nuv'] + session['corrected_nuv_err']
    models_within_limits = db.get_collection(model_collection).find(
        {'nuv': {"$gte": nuv_lower_lim, "$lte": nuv_upper_lim}, 
         'fuv': {"$gte": fuv_lower_lim, "$lte": fuv_upper_lim}}
    )
    return models_within_limits


def get_flux_ratios(session, model_collection):
    """TESTING: Computes the chi square value of flux ratios.
    
    Computes the chi square value of the model NUV to FUV flux ratio compared to
    the GALEX NUV to FUV flux ratio.

    Args:
        session: A Flask session variable that must include corrected_nuv and 
         corrected_fuv key value pairs, which are converted and photosphere subtracted 
         GALEX flux density values calculated from the convert_and_scale_fluxes function 
         in the helpers_flux module.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.

    Returns:
        The matching MongoDB collection with an additional field, 'flux_ratio_chi_squared',
        that is calculated with the equation:

        ((((model_nuv / model_fuv) - (galex_nuv / galex_fuv)) ** 2) / (galex_nuv / galex_fuv))

        The collection is returned from lowest value of flux_ratio_chi_squared to highest.
    """
    models_with_ratio = db.get_collection(model_collection).aggregate([
        {"$addFields": {
            "galex_flux_ratio": {"$divide": [session['corrected_nuv'], session['corrected_fuv']]},
            "model_flux_ratio": {"$divide": [session['nuv'], session['fuv']]}
            # "flux_ratio_chi_squared" : { "$round" : [{ "$divide" : [{"$pow" : [{"$subtract" : ["model_flux_ratio", "galex_flux_ratio"]},2]}, "galex_flux_ratio"]},2]}
        }},
        {"$addFields": {"ratio_chi_squared": {"$round": [{"$divide": [
            {"$pow": [{"$subtract": ["model_flux_ratio", "galex_flux_ratio"]}, 2]}]}, 2]}}},
        {"$sort": {"ratio_chi_squared": 1}}
    ])
    return models_with_ratio
