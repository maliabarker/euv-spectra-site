from euv_spectra_app.extensions import *

def find_matching_subtype(session):
    '''
    For finding matching subtype 
    INPUT: Session data, we use effective temp (teff), surface gravity (logg), and mass (mass)
    OUTPUT: One matching mongoDB document from the database
    '''
    matching_subtype = model_parameter_grid.aggregate([
        {'$facet': {
            'matchedTeff': [
                # Project a diff field that's the absolute difference along with the original doc.
                {'$project': {'diff': {'$abs': {'$subtract': [float(session['teff']), '$teff']}}, 'doc': '$$ROOT'}},
                # Order the docs by diff, Take the first one, Add new weighted field
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 10}}],
            'matchedLogg': [
                {'$project': {'diff': {'$abs': {'$subtract': [float(session['logg']), '$logg']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 5}}],
            'matchedMass': [
                {'$project': {'diff': {'$abs': {'$subtract': [float(session['mass']), '$mass']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}, {'$addFields': {'weight': 2}}]
        }},
        # get them together. Should list all rules from above  
        {'$project': {'doc': {'$concatArrays': ["$matchedTeff", "$matchedLogg", "$matchedMass"]}}},
        # split them apart, order by weight & desc, return top document
        {'$unwind': "$doc"}, {'$sort': {"doc.weight": -1}}, {'$limit': 1},
        # reshape to retrieve documents in its original format 
        {'$project': {'_id': "$doc._id", 'model': "$doc.doc.model", 'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass"}}
    ])
    subtype_doc = ''
    for doc in matching_subtype:
        subtype_doc = model_parameter_grid.find_one(doc['_id'])
    # print(f"SUBTYPE: {subtype_doc['model']}")
    return subtype_doc
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def find_matching_photosphere(session):
    '''
    For finding matching photosphere model 
    INPUT: Session data, we use effective temp (teff), and surface gravity (logg)
    OUTPUT: One matching mongoDB document from the database
    '''
    # TODO: iterate list and create pointer for lowest diff value ** reduce On^2 to On
    matching_temp = photosphere_models.aggregate([
        {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}},
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
                {'$project': {'diff': {'$abs': {'$subtract': [session['logg'], '$logg']}}, 'doc': '$$ROOT'}},
                {'$sort': {'diff': 1}}, {'$limit': 1}],
        }},
        # get them together. Should list all rules from above  
        {'$project': {'doc': {'$concatArrays': ["$matchedLogg"]}}},
        # split them apart, order by weight & desc, return top document
        {'$unwind': "$doc"}, {'$sort': {"doc.diff": -1}}, {'$limit': 1},
        # reshape to retrieve documents in its original format 
        {'$project': {'_id': "$doc._id", 'fits_filename': "$doc.doc.fits_filename", 'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass", 'euv': "$doc.doc.euv", 'nuv': "$doc.doc.nuv", 'fuv': "$doc.doc.fuv"}}
    ])
    matching_photosphere_doc = ''
    for doc in matching_photospheric_flux:
        # print(f'MATCHING PHOTOSPHERE: {doc}')
        matching_photosphere_doc = doc
    return matching_photosphere_doc
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def get_models_with_chi_squared(session, model_collection):
    '''
    For calculating chi squared value of each model in subgrid 
    INPUT: Session data, we use the corrected GALEX flux values, and the name of the model collection (ex: M0, M3)
    OUTPUT: The model collection with a new field (chi-squared) and corresponding values
    '''
    # EQUATION: chisq2 = sum((modelflux[i]- GALEX[i])**2 / GALEX[i])
    models_with_chi_squared = db.get_collection(model_collection).aggregate([
        { "$addFields" : { "chi_squared" : { "$round" : [ { "$add" : 
            #FOR NUV { "$divide": [ { "$pow": [ { "$subtract": [ "$NUV", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }
            [{ "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
            #FOR FUV { "$divide": [ { "$pow": [ { "$subtract": [ "$FUV", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }
            { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }]
        }, 2 ] } } },
        { "$sort" : { "chi_squared" : 1 } }
    ])
    return models_with_chi_squared
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def get_models_with_weighted_fuv(session, model_collection):
    '''
    For finding chi squared value of JUST FUV 
    INPUT: Session data, we use effective temp (teff), surface gravity (logg), and mass (mass)
    OUTPUT: One matching mongoDB document from the database

    # if no models within limits, check for FUV and NUV chi squared values
    # if chi squared FUV < chi squared NUV, return minimum chi squared of both added
    # ONLY looking at models that have FUV x^2 < NUV x^2
    '''
    models_with_fuv_less_than_nuv = db.get_collection(model_collection).aggregate([
        { "$addFields": {
            "chi_squared_fuv": { "$round" : [ { "$divide" : [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ]}, 2 ] }, 
            "chi_squared_nuv": { "$round" : [ { "$divide" : [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ]}, 2 ] },
            "chi_squared" : { "$round" : [ { "$add" : [
                { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
                { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }]
            }, 2 ] }
        }},
        { "$sort": { "chi_squared" : 1 }}
    ])
    final_models = []
    for model in list(models_with_fuv_less_than_nuv):
        if model['chi_squared_fuv'] < model['chi_squared_nuv']:
            final_models.append(model)

    return final_models
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
'''————————————————————————————————————————————————————————————————————————————————————————————————————————————————'''
def get_models_within_limits(session, model_collection):
    # return all results within upper and lower limits of fluxes (w/ chi squared values)
    # print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
    # print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
    fuv_lower_lim = session['corrected_fuv'] - session['corrected_fuv_err']
    fuv_upper_lim = session['corrected_fuv'] + session['corrected_fuv_err']
    nuv_lower_lim = session['corrected_nuv'] - session['corrected_nuv_err']
    nuv_upper_lim = session['corrected_nuv'] + session['corrected_nuv_err']
    models_within_limits = db.get_collection(model_collection).find({'nuv': {"$gte": nuv_lower_lim, "$lte": nuv_upper_lim}, 'fuv': {"$gte": fuv_lower_lim, "$lte": fuv_upper_lim}})
    return models_within_limits
        


''' OLD STUFF '''
# FOR CHI SQUARED CALCS: catch if there's no fuv/nuv detection, chi squared JUST over one flux
# models_with_chi_squared = db.get_collection(model_collection).aggregate([
#     { "$addFields": 
#         {"chi_squared": 
#             { "$switch": 
#                 { "branches": 
#                 # no NUV
#                 [{ "case": {"$eq": [session.get("nuv"), 'null'] }, "then": { "$round" : [ { "$divide" : [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ]}, 2 ] } },
#                 # no FUV
#                 { "case": {"$eq": [session.get("fuv"), 'null'] }, "then": { "$round" : [ { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }, 2 ] } }],
#                 "default": 
#                     { "$round" : [ 
#                         {"$add" : 
#                             [{ "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
#                             { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }]
#                         }, 2 ] 
#                     }
#                 }
#             }
#         }
#     },
#     { "$sort" : { "chi_squared" : 1 } }
# ])

# IN FIND MATCHING PHOTOSPHERE: combining teff match and logg match
# want to add numbers to queries (diff value) then add the values and return query with lowest value?
# matching_photospheric_flux_test = starter_photosphere_models.aggregate([
#     {'$facet': {
#         'matchedTeff': [
#             {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],

#         'matchedLogg': [
#             {'$project': {'diff': {'$abs': {'$subtract': [session['logg'], '$logg']}}, 'doc': '$$ROOT'}}, {'$limit': 1}],
#     }},
#     # get them together. Should list all rules from above  
#     {'$project': {'doc': {'$concatArrays': ["$matchedTeff", "$matchedLogg"]}}},
#     # split them apart, order by weight & desc, return top document
#     # {'$unwind': "$doc"}, {}
#     # {'$unwind': "$doc"}, {'$sort': {"doc.diff": -1}}, 
#     {'$limit': 1},
#     # reshape to retrieve documents in its original format 
#     #{'$project': {'_id': "$doc._id", 'fits_filename': "$doc.doc.fits_filename", 'teff': "$doc.doc.teff", 'logg': "$doc.doc.logg", 'mass': "$doc.doc.mass", 'euv': "$doc.doc.euv", 'nuv': "$doc.doc.nuv", 'fuv': "$doc.doc.fuv"}}
# ])

# FOR GETTING MODELS WITHING LIMITS: If a flux is missing (not possible now with flux substitution)
# if session["nuv"] == 'null':
#     # print('NO NUV')
#     # print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
#     fuv_lower_lim = session['corrected_fuv'] - session['corrected_fuv_err']
#     fuv_upper_lim = session['corrected_fuv'] + session['corrected_fuv_err']
#     models_within_limits = db.get_collection(model_collection).find({'fuv': {"$gte": fuv_lower_lim, "$lte": fuv_upper_lim}})
#     return models_within_limits
# elif session["fuv"] == 'null':
#     # print('NO FUV')
#     # print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
#     nuv_lower_lim = session['corrected_nuv'] - session['corrected_nuv_err']
#     nuv_upper_lim = session['corrected_nuv'] + session['corrected_nuv_err']
#     models_within_limits = db.get_collection(model_collection).find({'nuv': {"$gte": nuv_lower_lim, "$lte": nuv_upper_lim}})
#     return models_within_limits