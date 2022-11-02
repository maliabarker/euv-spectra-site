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

    print(f"SUBTYPE: {subtype_doc['model']}")
    return subtype_doc

def find_matching_photosphere(session):
    # iterate list and create pointer for lowest diff value ** reduce On^2 to On
    matching_temp = photosphere_models.aggregate([
        {'$project': {'diff': {'$abs': {'$subtract': [session['teff'], '$teff']}}, 'doc': '$$ROOT'}},
        {'$sort': {'diff': 1}},
        {'$limit': 1}
    ])
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
        print(f'MATCHING PHOTOSPHERE: {doc}')
        matching_photosphere_doc = doc
    return matching_photosphere_doc