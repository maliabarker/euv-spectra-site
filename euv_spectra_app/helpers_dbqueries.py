from euv_spectra_app.extensions import *
from bson.objectid import ObjectId

def find_matching_subtype(teff, logg, mass):
    """Matches to a subtype in the PEGASUS grid.

    Searches the PEGASUS grid for stellar subtype match using stellar effective 
    temperature, surface gravity, and mass. Temperature is weighted higher than
    surface gravity, surface gravity is weighted higher than mass. The weights are
    10, 5, and 2, respectively.

    Args:
        teff: Stellar effective temperature of the user's stellar target.
        logg: Surface gravity of the user's stellar target.
        mass: Mass of the user's stellar target.

    Returns:
        One MongoDB document from the model_parameter_grid collection corresponding to 
        the stellar subtype that best matches the user's target based on temperature, 
        surface gravity, and mass.
    """
    matching_subtype = model_parameter_grid.aggregate([
        {
            "$addFields": {
                "diff_teff": { "$abs": { "$subtract": [ teff, "$teff" ] } },
                "diff_logg": { "$abs": { "$subtract": [ logg, "$logg" ] } },
                "diff_mass": { "$abs": { "$subtract": [ mass, "$mass" ] } },
            }
        },
        {
            "$addFields" : {
                "diff_sum": { 
                    "$add": [
                        { "$multiply": [ "$diff_teff", 10 ] },
                        { "$multiply": [ "$diff_logg", 2 ] },
                        { "$multiply": [ "$diff_mass", 5 ] }
                    ]
                }
            }
        },
        { "$sort": { "diff_sum": 1 } },
        { "$limit": 1 },
    ])
    return list(matching_subtype)[0]


def find_matching_photosphere(teff, logg, mass):
    """Matches to a PHOENIX photosphere model.

    Searches a grid of custom PHOENIX calculated photosphere models for best match
    on stellar effective temperature, surface gravity and mass. This will be used
    in later functions to subtract photospheric contributions in the GALEX FUV and
    NUV flux densities.

    Args:
        teff: Stellar effective temperature of the user's stellar target.
        logg: Surface gravity of the user's stellar target.
        mass: Mass of the user's stellar target.

    Returns:
        One MongoDB document from the photosphere_models collection corresponding to 
        the photosphere that best matches the user's target based on temperature,
        surface gravity, and mass.
    """
    matching_photosphere_model = photosphere_models.aggregate([
        {
            "$addFields": {
                "diff_teff": { "$abs": { "$subtract": [ teff, "$teff" ] } },
                "diff_logg": { "$abs": { "$subtract": [ logg, "$logg" ] } },
                "diff_mass": { "$abs": { "$subtract": [ mass, "$mass" ] } },
            }
        },
        { "$sort": { "diff_teff": 1, "diff_logg": 1, "diff_mass": 1 } },
        { "$limit": 1 },
    ])
    return list(matching_photosphere_model)[0]


def get_models_with_chi_squared(corrected_nuv, corrected_fuv, model_collection):
    """Calculates chi square (χ2) values.

    Calculates the chi square values of FUV and NUV flux densities of each model in
    the stellar subgrid compared to the FUV and NUV flux densities of the user's 
    inputted stellar object.

    Args:
        corrected_nuv: The GALEX NUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        corrected_fuv: The GALEX FUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
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
        {"$addFields": 
            {"chi_squared": 
                {"$round": 
                    [ 
                        { "$add": 
                            [ 
                                { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", corrected_nuv ] }, 2 ] }, corrected_nuv ] },
                                { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", corrected_fuv ] }, 2 ] }, corrected_fuv ] } 
                            ]
                        }, 
                        2 
                    ]
                } 
            } 
        },
        { "$sort": { "chi_squared": 1 } }
    ])
    return models_with_chi_squared


def get_models_with_weighted_fuv(corrected_nuv, corrected_fuv, model_collection):
    """Calculates chi square value with weighted preference on FUV flux.

    Calculates the chi square values of FUV and NUV flux densities of each model in
    the stellar subgrid compared to the FUV and NUV flux densities of the user's 
    inputted stellar object. Preference is given to FUV by only returning documents
    in the collection that have a chi square value of FUV greater than the chi
    square value of NUV.

    Args:
        corrected_nuv: The GALEX NUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        corrected_fuv: The GALEX FUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
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
            "chi_squared_fuv": {"$round": [{"$divide": [{"$pow": [{"$subtract": ["$fuv", corrected_fuv]}, 2]}, corrected_fuv]}, 2]},
            "chi_squared_nuv": {"$round": [{"$divide": [{"$pow": [{"$subtract": ["$nuv", corrected_nuv]}, 2]}, corrected_nuv]}, 2]},
            "chi_squared": {"$round": [{"$add": [
                {"$divide": [{"$pow": [{"$subtract": [
                    "$nuv", corrected_nuv]}, 2]}, corrected_nuv]},
                {"$divide": [{"$pow": [{"$subtract": ["$fuv", corrected_fuv]}, 2]}, corrected_fuv]}]
            }, 2]}
        }},
        {"$sort": {"chi_squared": 1}}
    ])
    final_models = []
    for model in list(models_with_fuv_less_than_nuv):
        if model['chi_squared_fuv'] < model['chi_squared_nuv']:
            final_models.append(model)
    return final_models


def get_models_within_limits(corrected_nuv, corrected_fuv, corrected_nuv_err, corrected_fuv_err, model_collection):
    """Searches for models within limits of GALEX FUV and NUV flux densities.

    Args:
        corrected_nuv: The GALEX NUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        corrected_nuv_err: The GALEX NUV flux density error (scaled, converted, and 
         photosphere subtracted) of the user's stellar target.
        corrected_fuv: The GALEX FUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        corrected_fuv_err: The GALEX FUV flux density error (scaled, converted, and 
         photosphere subtracted) of the user's stellar target.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.

    Returns:
        MongoDB documents in the collection that have an FUV flux density value within 
        the upper and lower limits of the GALEX FUV flux density and an NUV flux 
        density value within the upper and lower limits of the GALEX NUV flux density.
    """
    print(corrected_fuv, corrected_fuv_err, corrected_nuv, corrected_nuv_err)
    fuv_lower_lim = corrected_fuv - corrected_fuv_err
    fuv_upper_lim = corrected_fuv + corrected_fuv_err
    nuv_lower_lim = corrected_nuv - corrected_nuv_err
    nuv_upper_lim = corrected_nuv + corrected_nuv_err
    print(fuv_upper_lim, fuv_lower_lim, nuv_upper_lim, nuv_lower_lim)
    models_within_limits = db.get_collection(model_collection).aggregate([
        {
            '$match': {
                'fuv': { '$gte': fuv_lower_lim, '$lte': fuv_upper_lim },
                'nuv': { '$gte': nuv_lower_lim, '$lte': nuv_upper_lim },
            }
        },
        {
            "$addFields": {
                "chi_squared": {
                    "$round": [ 
                        { "$add": 
                            [ 
                                { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", corrected_nuv ] }, 2 ] }, corrected_nuv ] },
                                { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", corrected_fuv ] }, 2 ] }, corrected_fuv ] } 
                            ]
                        }, 
                        2 
                    ]
                } 
            } 
        },
        { "$sort": { "chi_squared": 1 } }
    ])
    return models_within_limits


def get_flux_ratios(corrected_nuv, corrected_fuv, model_collection):
    """TESTING: Computes the chi square value of flux ratios.

    Computes the chi square value of the model NUV to FUV flux ratio compared to
    the GALEX NUV to FUV flux ratio.

    Args:
        corrected_nuv: The GALEX NUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        corrected_fuv: The GALEX FUV flux density (scaled, converted, and photosphere
         subtracted) of the user's stellar target.
        model_collection: The name of the MongoDB collection representing the matched 
         stellar subtype.

    Returns:
        The matching MongoDB collection with an additional field, 'chi_squared',
        that is calculated with the equation:

        ((((model_nuv / model_fuv) - (galex_nuv / galex_fuv)) ** 2) / (galex_nuv / galex_fuv))

        The collection is returned from lowest value of chi_squared to highest.
    """
    models_with_ratio = db.get_collection(model_collection).aggregate([
        {  
            "$addFields": {
                "galex_flux_ratio": {"$divide": [corrected_nuv, corrected_fuv]},
                "model_flux_ratio": {"$divide": ["$nuv", "$fuv"]}
            }
        },
        {
            "$addFields": {
                "chi_squared": {
                    "$divide": [
                        { "$pow": [ { "$subtract": [ "$model_flux_ratio", "$galex_flux_ratio" ] }, 2 ] },
                        "$galex_flux_ratio"
                    ]
                }
            }
        },
        {"$sort": {"chi_squared": 1}}
    ])
    return models_with_ratio
