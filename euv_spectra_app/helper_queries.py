from euv_spectra_app.extensions import *

def find_matching_subtype(session):
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
        #print(doc)
        subtype_doc = model_parameter_grid.find_one(doc['_id'])

    # print(f"SUBTYPE: {subtype_doc['model']}")
    return subtype_doc


def find_matching_photosphere(session):
    # iterate list and create pointer for lowest diff value ** reduce On^2 to On
    matching_temp = photosphere_models.aggregate([
        {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}},
        {'$sort': {'diff': 1}},
        {'$limit': 1}
    ])

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
    # print('TESTING')
    # for doc in matching_photospheric_flux_test:
    #     print(doc)

    teff = ''
    for doc in matching_temp:
        # print(doc['doc']['teff'])
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


def get_models_with_chi_squared(session, model_collection):
    # chisq2= sum((modelflux[i]- GALEX[i])**2 / GALEX[i])
    #FOR NUV { "$divide": [ { "$pow": [ { "$subtract": [ "$NUV", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }
    #FOR FUV { "$divide": [ { "$pow": [ { "$subtract": [ "$FUV", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }
    
    # catch if there's no fuv/nuv detection, chi squared JUST over one flux
    models_with_chi_squared = db.get_collection(model_collection).aggregate([
        { "$addFields": 
            {"chi_squared": 
                { "$switch": 
                    { "branches": 
                    # no NUV
                    [{ "case": {"$eq": [session.get("nuv"), 'null'] }, "then": { "$divide" : [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ]}},
                    # no FUV
                    { "case": {"$eq": [session.get("fuv"), 'null'] }, "then": { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }}],
                    "default": 
                        {"$add" : 
                            [{ "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
                            { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }]}
                    }
                }
            }
        },
        { "$sort" : { "chi_squared" : 1 } }
    ])

    return models_with_chi_squared

    # if session["nuv"] == 'null':
    #     print('NO NUV')
    #     print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
    #     models_with_chi_squared = db.get_collection(model_collection).aggregate([
    #         { "$match": {
    #             "fuv": { "$elemMatch": {"$gte":{"$subtract": [session['corrected_fuv'], session['corrected_fuv_err']]}, "$lte":{"$add": [session['corrected_fuv'], session['corrected_fuv_err']]}}}
    #             }
    #         },
    #         { "$addFields": { "chi_squared": { "$divide" : [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ]} } }
    #         # { "$project": {  
    #         #         "fits_filename": 1, "mass": 1, "euv": 1, "fuv": 1, "nuv": 1, "chiSquared": { 
    #         #             "$divide" : [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ]
    #         #         }
    #         #     }
    #         # }
    #     ])
    #     return models_with_chi_squared

    # elif session["fuv"] == 'null':
    #     print('NO FUV')
    #     print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
    #     models_with_chi_squared = db.get_collection(model_collection).aggregate([
    #         { "$match": {
    #             "nuv": { "$elemMatch": {"$gte": {"$subtract": [session['corrected_nuv'], session['corrected_nuv_err']]}, "$lte":{"$add": [session['corrected_nuv'], session['corrected_nuv_err']]}}}
    #             }
    #         },
    #         { "$addFields": { "chi_squared": { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] } } }
    #         # { "$project": {  
    #         #         "fits_filename": 1, "mass": 1, "euv": 1, "fuv": 1, "nuv": 1, "chiSquared": { 
    #         #             { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] }
    #         #         }
    #         #     }
    #         # }
    #     ])
    #     return models_with_chi_squared

    # else:
    #     print('BOTH FLUXES AVAILABLE')
    #     print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
    #     print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
    #     models_with_chi_squared = db.get_collection(model_collection).aggregate([
    #         { "$match": {
    #             "nuv": { "$elemMatch": {"$gte": {"$subtract": [session['corrected_nuv'], session['corrected_nuv_err']]}, "$lte":{"$add": [session['corrected_nuv'], session['corrected_nuv_err']]}}},
    #             "fuv": { "$elemMatch": {"$gte":{"$subtract": [session['corrected_fuv'], session['corrected_fuv_err']]}, "$lte":{"$add": [session['corrected_fuv'], session['corrected_fuv_err']]}}}
    #             }
    #         },
    #         { "$addFields": { "chi_squared": { 
    #                     "$add" : [
    #                         { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
    #                         { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }
    #                     ]} } 
    #         }
    #         # { "$project": {  
    #         #         "fits_filename": 1, "mass": 1, "euv": 1, "fuv": 1, "nuv": 1, "chiSquared": { 
    #         #             "$add" : [
    #         #                 { "$divide": [ { "$pow": [ { "$subtract": [ "$nuv", session['corrected_nuv'] ]}, 2 ] }, session['corrected_nuv'] ] },
    #         #                 { "$divide": [ { "$pow": [ { "$subtract": [ "$fuv", session['corrected_fuv'] ]}, 2 ] }, session['corrected_fuv'] ] }
    #         #             ]
    #         #         }
    #         #     }
    #         # }
    #     ])
    #     return models_with_chi_squared
            # ATTEMPT TO SWITCH CASES IN MATCH 
                # { "$match" :
            #     { "$expr":
            #         {"$switch": { 
            #             "branches": [
            #             # no NUV
            #             { "case": {"$eq": [session.get("corrected_nuv"), False] }, "then": {"fuv": {"$gte": {"$subtract": [session['corrected_fuv'], session['corrected_fuv_err']]}, "$lte":{"$add": [session['corrected_fuv'], session['corrected_fuv_err']]}}}},
            #             # no FUV
            #             { "case": {"$eq": [session.get("corrected_fuv"), False] }, "then": {"nuv": {"$gte": {"$subtract": [session['corrected_nuv'], session['corrected_nuv_err']]}, "$lte":{"$add": [session['corrected_nuv'], session['corrected_nuv_err']]}}}}
            #             ],
            #             "default": 
            #                 {"$nuv": {"$gte": {"$subtract": [session['corrected_nuv'], session['corrected_nuv_err']]}, "$lte":{"$add": [session['corrected_nuv'], session['corrected_nuv_err']]}},
            #                 "$fuv": {"$gte":{"$subtract": [session['corrected_fuv'], session['corrected_fuv_err']]}, "$lte":{"$add": [session['corrected_fuv'], session['corrected_fuv_err']]}}}
            #         }}
            #     }
            # },

def get_models_within_limits(session, model_collection, models):
    # return all results within upper and lower limits of fluxes (w/ chi squared values)
        # db.get_collection(model_collection).find({'nuv': {"$gte":<lower_lim_nuv>, "$lte":<upper_lim_nuv>}, 'fuv': {$gte:<lower_lim_fuv>, $lte:<upper_lim_fuv>}})
        
        # lower_lim = {"$subtract": [session['corrected_nuv'], session['corrected_nuv_err']]}
        # session['corrected_nuv'] - session['corrected_nuv_err']
        # upper_lim = {"$add": [session['corrected_nuv'], session['corrected_nuv_err']]}
        # session['corrected_nuv'] + session['corrected_nuv_err']

        # compute upper lim and lower lim for each flux and find within those values

    if session["nuv"] == 'null':
        # print('NO NUV')
        # print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
        fuv_lower_lim = session['corrected_fuv'] - session['corrected_fuv_err']
        fuv_upper_lim = session['corrected_fuv'] + session['corrected_fuv_err']
        models_within_limits = db.get_collection(model_collection).find({'fuv': {"$gte": fuv_lower_lim, "$lte": fuv_upper_lim}})
        return models_within_limits

    elif session["fuv"] == 'null':
        # print('NO FUV')
        # print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
        nuv_lower_lim = session['corrected_nuv'] - session['corrected_nuv_err']
        nuv_upper_lim = session['corrected_nuv'] + session['corrected_nuv_err']
        models_within_limits = db.get_collection(model_collection).find({'nuv': {"$gte": nuv_lower_lim, "$lte": nuv_upper_lim}})
        return models_within_limits

    else:
        # print('BOTH FLUXES AVAILABLE')
        # print(f'NUV UPPER LIM {session["corrected_nuv"] + session["corrected_nuv_err"]} LOWER LIM {session["corrected_nuv"] - session["corrected_nuv_err"]}')
        # print(f'FUV UPPER LIM {session["corrected_fuv"] + session["corrected_fuv_err"]} LOWER LIM {session["corrected_fuv"] - session["corrected_fuv_err"]}')
        fuv_lower_lim = session['corrected_fuv'] - session['corrected_fuv_err']
        fuv_upper_lim = session['corrected_fuv'] + session['corrected_fuv_err']

        nuv_lower_lim = session['corrected_nuv'] - session['corrected_nuv_err']
        nuv_upper_lim = session['corrected_nuv'] + session['corrected_nuv_err']
        
        models_within_limits = db.get_collection(model_collection).find({'nuv': {"$gte": nuv_lower_lim, "$lte": nuv_upper_lim}, 'fuv': {"$gte": fuv_lower_lim, "$lte": fuv_upper_lim}})
        return models_within_limits