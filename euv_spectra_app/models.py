# FOR ASTROQUERY/GALEX DATA
import numpy.ma as ma
import math
import requests
from astropy.time import Time
import astropy.units as u
from astroquery.exceptions import ResolverError
from astropy.coordinates import SkyCoord, Distance
from astroquery.mast import Catalogs
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.simbad import Simbad
from euv_spectra_app.extensions import db
from euv_spectra_app.helpers_dbqueries import find_matching_subtype, find_matching_photosphere, get_models_with_chi_squared, get_models_within_limits, get_models_with_weighted_fuv, get_flux_ratios, get_models_within_limits_saturated_fuv, get_models_within_limits_saturated_nuv, get_models_within_limits_upper_limit_fuv, get_models_within_limits_upper_limit_nuv

customSimbad = Simbad()
customSimbad.remove_votable_fields('coordinates')
customSimbad.add_votable_fields(
    'ra', 'dec', 'pmra', 'pmdec', 'plx', 'rv_value', 'typed_id')


class ProperMotionData():
    """Represents proper motion data of a stellar object."""

    def __init__(self, pm_ra=None, pm_dec=None, plx=None, rad_vel=None):
        self.pm_ra = pm_ra
        self.pm_dec = pm_dec
        self.plx = plx
        self.rad_vel = rad_vel

    def correct_pm(self, star_name, coords):
        """Corrects the given coordinates for proper motion using the GALEX observation time.

        Args:
            star_name (str): The name of the star to be queried on PEGASUS API.
            coords (tuple): A tuple containing two strings representing right ascension and declination.

        Returns:
            tuple: A tuple containing two floats representing the corrected right ascension and declination coordinates.

        Raises:
            TypeError: If the target star name is not found in the GALEX obs time collection (cannot get t_min)
            KeyError: If the target star name is not found in the GALEX obs time collection
            ValueError: If the star name is not a valid string to search with
            Exception: If an error occurs during coordinate correction or any other error occurs during galex search.
        """
        try:
            # STEP 1: Find a GALEX observation time from custom compiled dataset
            galex_time = db.mast_galex_times.find_one(
                {'target': star_name})['t_min']
        except TypeError as te:
            print(f'Galex obs time in depth error: {te}')
            return(f'Did not find matches in GALEX observations for {star_name if star_name else coords}. Unable to correct for proper motion. Look under question 3 on the FAQ page for more information.')
        except KeyError as ke:
            print(f'Galex obs time in depth error: {ke}')
            return(f'Did not find matches in GALEX observations for {star_name if star_name else coords}. Unable to correct for proper motion. Look under question 3 on the FAQ page for more information.')
        except ValueError as ve:
            print(f'Galex obs time in depth error: {ve}')
            return(f'Unable to search GALEX observations for {star_name if star_name else coords}. Unable to correct for proper motion. Please check your inputs or look under question 3 on the FAQ page for more information.')
        except Exception as e:
            print(f'Galex obs time in depth error: {e}')
            return(f'No GALEX observations found for {star_name if star_name else coords}. Unable to correct for proper motion. Look under question 3 on the FAQ page for more information.')
        else:
            try:
                # STEP 2: If observation time is found, start coordinate correction by initializing variables
                coordinates = coords[0] + ' ' + coords[1]
                skycoord_obj = ''
                # STEP 3: Calculate time difference between observation time and Jan 1st, 2000 (J2000)
                t3 = Time(galex_time, format='mjd') - \
                    Time(51544.0, format='mjd')
                # STEP 4: Convert time (which will return in seconds) into years
                td_year = t3.sec / 60 / 60 / 24 / 365.25
                # STEP 5: Check to see if radial velocity is given then create SkyCoord object with all data
                if self.rad_vel:
                    skycoord_obj = SkyCoord(coordinates, unit=(u.hourangle, u.deg), distance=Distance(parallax=self.plx*u.mas, allow_negative=True),
                                            pm_ra_cosdec=self.pm_ra*u.mas/u.yr, pm_dec=self.pm_dec*u.mas/u.yr, radial_velocity=self.rad_vel*u.km/u.s)
                else:
                    skycoord_obj = SkyCoord(coordinates, unit=(u.hourangle, u.deg), distance=Distance(
                        parallax=self.plx*u.mas, allow_negative=True), pm_ra_cosdec=self.pm_ra*u.mas/u.yr, pm_dec=self.pm_dec*u.mas/u.yr)
                # STEP 6: Use apply_space_motion function to calculate new coordinates
                skycoord_obj = skycoord_obj.apply_space_motion(
                    dt=td_year * u.yr)
                # STEP 7: Add new coordinates to return data dict
                return (skycoord_obj.ra.degree, skycoord_obj.dec.degree)
            except Exception as e:
                return (f'Unknown error during proper motion correction: {e}')


class GalexFlux():
    """Represents one GALEX flux and error (FUV or NUV)."""

    def __init__(self, flux, flux_err, photospheric_flux, dist, rad, wv):
        self.flux = flux
        self.upper_lim = flux + flux_err
        self.lower_lim = flux - flux_err
        self.photo_flux = photospheric_flux
        self.dist = dist * 3.08567758e18
        self.rad = rad * 6.9e10
        self.wv = wv
        self.scale = ((self.dist**2) / (self.rad**2))

    def convert_ujy_to_flux(self, chosen_flux):
        """Converts microjanskies to ergs/s/cm2/A."""
        return (((3e-5) * (chosen_flux * 10**-6)) / pow(self.wv, 2))

    def scale_flux(self, chosen_flux):
        """Scales flux to stellar surface."""
        return chosen_flux * self.scale

    def subtract_photosphere_flux(self, chosen_flux):
        """Subtracts the photospheric contributed flux from GALEX flux."""
        return chosen_flux - self.photo_flux

    def run_calculations(self, chosen_flux):
        """Runs calculations in correct order to return converted, scaled flux."""
        converted_flux = self.convert_ujy_to_flux(chosen_flux)
        scaled_flux = self.scale_flux(converted_flux)
        photo_subtracted_flux = self.subtract_photosphere_flux(scaled_flux)
        return photo_subtracted_flux

    def return_new_flux(self):
        """Returns newly calculated flux density."""
        return self.run_calculations(self.flux)

    def return_new_err(self):
        """Calculates the new flux error."""
        new_flux = self.return_new_flux()
        new_upper_lim = self.run_calculations(self.upper_lim)
        new_lower_lim = self.run_calculations(self.lower_lim)
        new_upper_err = new_upper_lim - new_flux
        new_lower_err = new_flux - new_lower_lim
        new_err = (new_upper_err + new_lower_err) / 2
        return new_err
    

class GalexFluxes():
    """Represents GALEX flux values."""

    def __init__(self, fuv=None, nuv=None, fuv_saturated=None, nuv_saturated=None, fuv_upper_limit=None, nuv_upper_limit=None, fuv_err=None, nuv_err=None, fuv_is_saturated=None, nuv_is_saturated=None, fuv_is_upper_limit=None, nuv_is_upper_limit=None, stellar_obj=None):
        self.fuv = fuv
        self.nuv = nuv
        self.fuv_saturated = fuv_saturated
        self.nuv_saturated = nuv_saturated
        self.fuv_upper_limit = fuv_upper_limit
        self.nuv_upper_limit = nuv_upper_limit
        self.fuv_err = fuv_err
        self.nuv_err = nuv_err
        self.fuv_is_saturated = fuv_is_saturated
        self.nuv_is_saturated = nuv_is_saturated
        self.fuv_is_upper_limit = fuv_is_upper_limit
        self.nuv_is_upper_limit = nuv_is_upper_limit
        self.stellar_obj = stellar_obj

    def has_attr_val(self, attr):
        if hasattr(self, attr) and getattr(self, attr) is not None:
            return True
        else:
            return False

    def check_null_fluxes(self):
        print('CHECKING NULL FLUXES')
        if (self.fuv is None or ma.is_masked(self.fuv)) and (self.nuv is None or ma.is_masked(self.nuv)):
            # all fluxes are null/ no galex data
            self.fuv, self.fuv_err = 'No Detection', 'No Detection'
            self.nuv, self.nuv_err = 'No Detection', 'No Detection'
            return ('No GALEX detections found.')
        elif self.fuv is None or ma.is_masked(self.fuv):
            # only FUV is null, predict FUV and add error message
            print('FUV NULL, predicting flux')
            self.predict_fluxes(self.nuv, self.nuv_err, 'nuv')
            return ('GALEX FUV not detected. Predicting for FUV and FUV error.')
        elif self.nuv is None or ma.is_masked(self.nuv):
            # only NUV is null, predict NUV and add error message
            print('NUV NULL, predicting flux')
            self.predict_fluxes(self.fuv, self.fuv_err, 'fuv')
            return ('GALEX NUV not detected. Predicting for NUV and NUV error.')

    def check_saturated_fluxes(self):
        """Checks if the FUV or NUV fluxes are saturated and corrects them if possible.

        If both the FUV and NUV fluxes are saturated, raises an exception and sets both
        fluxes to 'No Detection' and their errors to 'No Detection'. If only the FUV
        flux is saturated, predicts the corrected flux using the non-saturated NUV flux,
        updates the FUV flux and error, and returns the maximum flux and error between
        the predicted and original values. If only the NUV flux is saturated, predicts
        the corrected flux using the non-saturated FUV flux, updates the NUV flux and
        error, and returns the maximum flux and error between the predicted and original
        values. If none of the fluxes are saturated, prints a message and does nothing.

        Side effects: 
            If both fuv and nuv are saturated, sets values of fuv, fuv_err, nuv, and nuv_err of GalexFluxes object to 'No Detection'.
            If only fuv is saturated, may set values of fuv and fuv_err of GalexFluxes object.
            If only nuv is saturated, may set values of nuv and nuv_err of GalexFluxes object.

        Raises:
            ValueError if fuv_aper or nuv_aper is invalid.
            Exception if both fluxes are saturated.
        """
        try:
            if self.fuv_is_saturated and self.nuv_is_saturated:
                self.fuv, self.fuv_err = 'No Detection', 'No Detection'
                self.nuv, self.nuv_err = 'No Detection', 'No Detection'
                return ('Both GALEX detections cannot be saturated, cannot correct fluxes.')
            elif self.fuv_is_saturated:
                # Option A: Predict
                self.predict_fluxes(self.nuv, self.nuv_err, 'nuv')
                # print('Testing resulting saturated fluxes to compare:', self.fuv, self.fuv_saturated)
                if self.fuv < self.fuv_saturated:
                    # if predicted flux is not greater than saturated flux, change flux and err to None
                    self.fuv = None
                    self.fuv_err = None
            elif self.nuv_is_saturated:
                self.predict_fluxes(self.fuv, self.fuv_err, 'fuv')
                # print('Testing resulting saturated fluxes to compare:', self.nuv, self.nuv_saturated)
                if self.nuv < self.nuv_saturated:
                    self.nuv = None
                    self.nuv_err = None
        except ValueError as e:
            return ('Invalid `fuv_saturated`, `fuv_is_saturated` and/or `nuv_saturated`, `nuv_is_saturated` attributes:' + str(e))

    def check_upper_limit_fluxes(self):
        try:
            if self.fuv_is_upper_limit and self.nuv_is_upper_limit:
                self.fuv, self.fuv_err = 'No Detection', 'No Detection'
                self.nuv, self.nuv_err = 'No Detection', 'No Detection'
                return ('Both GALEX detections cannot be upper limits, cannot correct fluxes.')
            elif self.fuv_is_upper_limit:
                # Option A: Predict
                self.predict_fluxes(self.nuv, self.nuv_err, 'nuv')
                # print('Testing resulting upper limit fluxes to compare:', self.fuv, self.fuv_upper_limit)
                if self.fuv > self.fuv_upper_limit:
                    # if predicted flux is not less than saturated flux, change flux and err to None
                    self.fuv = None
                    self.fuv_err = None
            elif self.nuv_is_upper_limit:
                self.predict_fluxes(self.fuv, self.fuv_err, 'fuv')
                # print('Testing resulting upper limit fluxes to compare:', self.nuv, self.nuv_upper_limit)
                if self.nuv > self.nuv_upper_limit:
                    self.nuv = None
                    self.nuv_err = None
        except ValueError as e:
            return ('Invalid `fuv_upper_limit`, `fuv_is_upper_limit` and/or `nuv_upper_limit`, `nuv_is_upper_limit` attributes:' + str(e))

    def predict_early_ms(self, flux_val, flux_err, flux_type):
        """
        STEP 1: Scale GALEX flux densities to be at 10 parsecs with following equation
            stellar_dist^2 / 100 
            * NOTE: the stellar distance needs to be in parsecs
        STEP 2: Solve for the missing flux, for example if the given flux_type is 'nuv', 
        solve for 'fuv', use the following equations
            FUV = 10 ^ ( 1.17 * log10(NUV) - 1.26 )
            NUV = 10 ^ ( ( log10(FUV) + 1.26 ) / 1.17 )
            * NOTE: the fluxes in these equations are the scaled values obtained from 
                    the last step
        STEP 3: Unscale the flux from 10 psc back to earth surface using equation
            100 / stellar_dist^2
        """
        pred_flux = None
        pred_err = None
        scale = ((pow(self.stellar_obj['dist'], 2)) / 100)
        unscale = (100 / (pow(self.stellar_obj['dist'], 2)))
        scaled_flux = flux_val * scale
        upper_lim_scaled = (flux_val + flux_err) * scale
        lower_lim_scaled = (flux_val - flux_err) * scale
        which_flux = None
        which_err = None
        if flux_type == 'fuv':
            # predicting for NUV
            which_flux = 'nuv'
            which_err = 'nuv_err'
            pred_flux = (pow(10, (( math.log10(scaled_flux) + 1.26 ) / 1.17 ))) * unscale
            pred_upper_lim = (pow(10, (( math.log10(upper_lim_scaled) + 1.26 ) / 1.17 ))) * unscale
            pred_lower_lim = (pow(10, (( math.log10(lower_lim_scaled) + 1.26 ) / 1.17 ))) * unscale
        elif flux_type == 'nuv':
            # predicting for FUV
            which_flux = 'fuv'
            which_err = 'fuv_err'
            pred_flux = (pow(10, ( 1.17 * math.log10(scaled_flux) - 1.26 ))) * unscale
            pred_upper_lim = (pow(10, ( 1.17 * math.log10(upper_lim_scaled) - 1.26 ))) * unscale
            pred_lower_lim = (pow(10, ( 1.17 * math.log10(lower_lim_scaled) - 1.26 ))) * unscale
        else:
            return 'Can only correct GALEX FUV and NUV fluxes.'
        setattr(self, which_flux, pred_flux)
        new_upper_flux = pred_upper_lim - pred_flux
        new_lower_flux = pred_flux - pred_lower_lim
        pred_err = (new_upper_flux + new_lower_flux) / 2
        setattr(self, which_err, pred_err)

    def predict_late_ms(self, flux_val, flux_err, flux_type):
        """
        STEP 1: Scale GALEX flux densities to be at 10 parsecs with following equation
            stellar_dist^2 / 100 
            * NOTE: the stellar distance needs to be in parsecs
        STEP 2: Solve for the missing flux, for example if the given flux_type is 'nuv', 
        solve for 'fuv', use the following equations
            FUV = 10 ^ ( 0.98 * log10(NUV) - 0.47 )
            NUV = 10 ^ ( ( log10(FUV) + 0.47 ) / 0.98 )
            * NOTE: the fluxes used in these equations are the scaled values obtained 
                    from the last step
        """
        pred_flux = None
        pred_err = None
        scale = ((pow(self.stellar_obj['dist'], 2)) / 100)
        unscale = (100 / (pow(self.stellar_obj['dist'], 2)))
        scaled_flux = flux_val * scale
        upper_lim_scaled = (flux_val + flux_err) * scale
        lower_lim_scaled = (flux_val - flux_err) * scale
        which_flux = None
        which_err = None
        if flux_type == 'fuv':
            # predicting for NUV
            which_flux = 'nuv'
            which_err = 'nuv_err'
            pred_flux = (pow(10, (( math.log10(scaled_flux) + 0.47 ) / 0.98 ))) * unscale
            pred_upper_lim = (pow(10, (( math.log10(upper_lim_scaled) + 0.47 ) / 0.98 ))) * unscale
            pred_lower_lim = (pow(10, (( math.log10(lower_lim_scaled) + 0.47 ) / 0.98 ))) * unscale
        elif flux_type == 'nuv':
            # predicting for FUV
            which_flux = 'fuv'
            which_err = 'fuv_err'
            pred_flux = (pow(10, ( 0.98 * math.log10(scaled_flux) - 0.47 ))) * unscale
            pred_upper_lim = (pow(10, ( 0.98 * math.log10(upper_lim_scaled) - 0.47 ))) * unscale
            pred_lower_lim = (pow(10, ( 0.98 * math.log10(lower_lim_scaled) - 0.47 ))) * unscale
        setattr(self, which_flux, pred_flux)
        new_upper_flux = pred_upper_lim - pred_flux
        new_lower_flux = pred_flux - pred_lower_lim
        pred_err = (new_upper_flux + new_lower_flux) / 2
        setattr(self, which_err, pred_err)

    def predict_fluxes(self, flux_val, flux_err, flux_type):
        """Predicts the specified flux based on the remaining GALEX flux values.

        Args:
            flux_to_predict: Either fuv or nuv, specifies which flux to predict for.

        Side Effects:
            If flux_to_predict is 'fuv', sets fuv and fuv_err of GalexFluxes object.
            If flux_to_predict is 'nuv', sets nuv and nuv_err of GalexFluxes object.
        """
        early_m = ['M0', 'M1', 'M2', 'M3', 'M4', 'M5']
        late_m = ['M6', 'M7', 'M8', 'M9', 'M5']
        print('checking stellar subtype from inside predict fluxes:', self.stellar_obj['stellar_subtype'])
        # STEP 1: Check that stellar_subtype value exists
        if 'stellar_subtype' not in self.stellar_obj:
            print('DOES NOT HAVE A STELLAR SUBTYPE')
            return ('Cannot predict flux without stellar subtype. Please try again or contact us with more information on your search.')
        elif self.stellar_obj['stellar_subtype'] in early_m:
            print('STAR IS EARLY M:', self.stellar_obj['stellar_subtype'])
            self.predict_early_ms(flux_val, flux_err, flux_type)
        elif self.stellar_obj['stellar_subtype'] in late_m:
            print('STAR IS LATE M:', self.stellar_obj['stellar_subtype'])
            self.predict_late_ms(flux_val, flux_err, flux_type)
        else:
            print('Not an m star?')
            return ('Can only run predictions on M stars at the moment.')

    def get_limits(self, flux, err):
        """Returns the upper and lower limits of a specified flux."""
        upper_lim = flux + err
        lower_lim = flux - err
        return {"upper_lim": upper_lim, "lower_lim": lower_lim}

    def convert_ujy_to_flux_density(self, num, wv):
        """Converts microjanskies to ergs/s/cm2/A."""
        return (((3e-5) * (num * 10**-6)) / pow(wv, 2))

    def scale_flux(self, num):
        """Scales flux to stellar surface."""
        scale = (((self.stellar_obj['dist'] * 3.08567758e18)
                 ** 2) / ((self.stellar_obj['rad'] * 6.9e10)**2))
        return num * scale

    def get_photosphere_model(self):
        try:
            matching_photosphere_model = find_matching_photosphere(
                self.stellar_obj['teff'], self.stellar_obj['logg'], self.stellar_obj['mass'])
            # print('PHOTOSPHERE MODEL', matching_photosphere_model)
            return matching_photosphere_model
        except Exception:
            return ('Cannot find a photosphere model. Please try again.')

    def subtract_photosphere_flux(self, chosen_flux, photo_flux):
        """Subtracts the photospheric contributed flux from GALEX flux."""
        return chosen_flux - photo_flux
    
    def convert_scale_photosphere_subtract_single_flux(self, flux, flux_type):
        wv = None
        photo_flux = None
        photosphere_data = self.get_photosphere_model()
        if flux_type == 'fuv':
            wv = 1542.3
            photo_flux = photosphere_data['fuv']
        elif flux_type == 'nuv':
            wv = 2274.4
            photo_flux = photosphere_data['nuv']
        else:
            return ('Can only run calculations on fuv or nuv flux types. Please input one of these and try again.')
        converted_flux = self.convert_ujy_to_flux_density(flux, wv)
        scaled_flux = self.scale_flux(converted_flux)
        photosub_flux = self.subtract_photosphere_flux(scaled_flux, photo_flux)
        return photosub_flux
    
    def convert_scale_photosphere_subtract_fuv(self):
        self.processed_fuv = self.convert_scale_photosphere_subtract_single_flux(self.fuv, 'fuv')
        fuv_lims = self.get_limits(self.fuv, self.fuv_err)
        photosub_fuv_upper_lim = self.convert_scale_photosphere_subtract_single_flux(fuv_lims['upper_lim'], 'fuv')
        photosub_fuv_lower_lim = self.convert_scale_photosphere_subtract_single_flux(fuv_lims['lower_lim'], 'fuv')
        new_fuv_upper_err = photosub_fuv_upper_lim - self.processed_fuv
        new_fuv_lower_err = self.processed_fuv - photosub_fuv_lower_lim
        self.processed_fuv_err = (new_fuv_upper_err + new_fuv_lower_err) / 2

    def convert_scale_photosphere_subtract_nuv(self):
        self.processed_nuv = self.convert_scale_photosphere_subtract_single_flux(self.nuv, 'nuv')
        nuv_lims = self.get_limits(self.nuv, self.nuv_err)
        photosub_nuv_upper_lim = self.convert_scale_photosphere_subtract_single_flux(nuv_lims['upper_lim'], 'nuv')
        photosub_nuv_lower_lim = self.convert_scale_photosphere_subtract_single_flux(nuv_lims['lower_lim'], 'nuv')
        new_nuv_upper_err = photosub_nuv_upper_lim - self.processed_nuv
        new_nuv_lower_err = self.processed_nuv - photosub_nuv_lower_lim
        self.processed_nuv_err = (new_nuv_upper_err + new_nuv_lower_err) / 2

    def convert_scale_photosphere_subtract_fluxes(self):
        if self.fuv is None and self.nuv is None:
            return ValueError('The values of FUV and NUV cannot both be None. Please check values of the GalexFluxes object and try again.')
        elif self.nuv_is_saturated and self.nuv is None:
            # means that prediction test of saturation did not work, only do fuv and nuv_saturated values
            self.convert_scale_photosphere_subtract_fuv()
            self.processed_nuv_saturated = self.convert_scale_photosphere_subtract_single_flux(self.nuv_saturated, 'nuv')
        elif self.fuv_is_saturated and self.fuv is None:
            # means that prediction test of saturation did not work, only do nuv and fuv_saturated values
            self.convert_scale_photosphere_subtract_nuv()
            self.processed_fuv_saturated = self.convert_scale_photosphere_subtract_single_flux(self.fuv_saturated, 'fuv')
        elif self.nuv_is_upper_limit and self.nuv is None:
            # means that prediction test of upper limit did not work, only do fuv and nuv_upper_limit values
            self.convert_scale_photosphere_subtract_fuv()
            self.processed_nuv_upper_limit = self.convert_scale_photosphere_subtract_single_flux(self.nuv_upper_limit, 'nuv')
        elif self.fuv_is_upper_limit and self.fuv is None:
            # means that prediction test of saturation did not work, only do nuv and fuv_upper_limit values
            self.convert_scale_photosphere_subtract_nuv()
            self.processed_fuv_upper_limit = self.convert_scale_photosphere_subtract_single_flux(self.fuv_upper_limit, 'fuv')
        else:
            # means either:
            #   all fluxes are available, may have predicted flux but no saturated/upper limit flux OR
            #   a flux is saturated/upper limit, prediction test worked, treat all flux values as is and 
            #   do calculations on saturated/upper limit value as well
            if self.nuv_is_saturated:
                self.processed_nuv_saturated = self.convert_scale_photosphere_subtract_single_flux(self.nuv_saturated, 'nuv')
            if self.fuv_is_saturated:
                self.processed_fuv_saturated = self.convert_scale_photosphere_subtract_single_flux(self.fuv_saturated, 'fuv')
            if self.nuv_is_upper_limit:
                self.processed_nuv_upper_limit = self.convert_scale_photosphere_subtract_single_flux(self.nuv_upper_limit, 'nuv')
            if self.fuv_is_upper_limit:
                self.processed_fuv_upper_limit = self.convert_scale_photosphere_subtract_single_flux(self.fuv_upper_limit, 'fuv')
            # This means both are fine to process
            self.convert_scale_photosphere_subtract_nuv()
            self.convert_scale_photosphere_subtract_fuv()


class StellarObject():
    """Represents a stellar object."""

    def __init__(self, star_name=None, position=None, coords=None, teff=None, logg=None, mass=None, dist=None, rad=None, pm_data=None, pm_corrected_coords=None, fluxes=None, stellar_subtype=None):
        self.star_name = star_name
        self.position = position
        self.coords = coords
        self.teff = teff
        self.logg = logg
        self.mass = mass
        self.dist = dist
        self.rad = rad
        self.pm_data = pm_data
        self.pm_corrected_coords = pm_corrected_coords
        self.fluxes = fluxes
        self.stellar_subtype = stellar_subtype
        self.modal_error_msgs = []
        if self.fluxes is None:
            self.fluxes = GalexFluxes()

    def has_all_stellar_parameters(self):
        # Checks to see that all stellar intrinstic parameters exist.
        if self.teff is not None and self.logg is not None and self.mass is not None and self.dist is not None and self.rad is not None:
            return True
        else:
            return False
        
    def has_null_fluxes(self):
        # Checks for any null fluxes.
        if self.fluxes.has_attr_val('processed_fuv') is False or self.fluxes.has_attr_val('processed_nuv') is False:
            return True
        else:
            return False
        
    def has_saturated_fluxes(self):
        # Checks for any fluxes flagged as saturated.
        if hasattr(self.fluxes, 'fuv_saturated') and self.fluxes.fuv_saturated or hasattr(self.fluxes, 'nuv_saturated') and self.fluxes.nuv_saturated:
            return True
        else:
            return False
        
    def has_upper_limit_fluxes(self):
        # Checks for any fluxes flagged as upper limit.
        if hasattr(self.fluxes, 'fuv_upper_limit') and self.fluxes.fuv_upper_limit or hasattr(self.fluxes, 'nuv_upper_limit') and self.fluxes.nuv_upper_limit:
            return True
        else:
            return False

    def has_all_processed_fluxes(self):
        # Checks to see that all GALEX fluxes have been converted, scaled, and photosphere subtracted.
        if self.fluxes.has_attr_val('processed_fuv') and self.fluxes.has_attr_val('processed_fuv_err') and self.fluxes.has_attr_val('processed_nuv') and self.fluxes.has_attr_val('processed_nuv_err'):
            return True
        else:
            return False

    def get_stellar_parameters(self):
        """Searches Astroquery databases for stellar data.

        Searches SIMBAD, the NASA Exoplanet Archive, and MAST GALEX databases for 
        stellar data. Right ascension, declination, proper motion data, radial 
        velocity, and parallax are pulled from SIMBAD. Effective temperature, 
        surface gravity, mass, distance, and radius are pulled from the NASA 
        Exoplanet Archive. GALEX FUV and NUV flux density and the respective errors 
        are pulled from the MAST GALEX database. The data is used to populate the 
        resulting modal form.

        We check if each catalog/dataset search was successful by checking if the returned 
        data is None or not. If the search goes well, the searched catalog will assign 
        parameters in place and will return None. However, if the search does not run for 
        any reason, an error will be returned as a string error message. So, we check each 
        catalog search by checking if result of function call is None (search went well) or 
        not (error message is returned and we add that to modal error messages to return 
        on the user's front end.)

        Args:
            star_name OR position: The search term the user submitted in the search bar input.
            search_format: The format the search input is in, either name or position.

        Side Effects:
            If every function runs without errors, will assign teff, logg, mass, dist, rad, 
            fluxes, and stellar subtype.
            If the search is by star name, will assign proper motion data and proper motion 
            corrected coordinates.
            If the search is by position, will assign coordinates converted to RA and DEC.
            If an error occurs, will append to the modal galex error messages list.

        Raises:
            No errors are raised but if an error is detected from within a catalog search, the 
            function returns the error as a string and is sent to the front end error page to be displayed.
        """
        # STEP 1: Check for search type (position or name)
        if self.position:
            # STEP Pos1: Change coordinates to ra and dec
            converted_coords = self.convert_coords(self.position)
            if converted_coords is not None:
                # will stop function if coords were not converted into usable format
                self.modal_page_error_msg = converted_coords
                return
        elif self.star_name:
            # STEP Name1: Check if name is in the mast target database 
            # (used to check for case & spacing errors in user input)
            data = NasaExoplanetArchive.query_criteria(
                table="pscomppars", select="DISTINCT hostname")
            host_stars = data['hostname']
            for name in host_stars:
                # take away all spaces and make every letter upper case
                if self.star_name.upper().replace(' ', '') == name.upper().replace(' ', ''):
                    # if there is a match, assign the input star name to the correct format from NEA
                    self.star_name = name
                    break
            # STEP Name2: Get coordinate and proper motion info from Simbad
            simbad_data = self.query_simbad(self.star_name)
            if simbad_data is not None:
                # will stop function if no coords found in SIMBAD
                self.modal_error_msgs.append(simbad_data)
            # STEP Name3: Put PM and Coord info into proper motion correction function
            pm_corrected_coords = None
            if self.pm_data is not None:
                pm_corrected_coords = self.pm_data.correct_pm(
                    self.star_name, self.coords)
            # if the returned data is a tuple, this means it returned an RA and DEC, assign values as coords
            if isinstance(pm_corrected_coords, tuple):
                self.pm_corrected_coords = pm_corrected_coords
            # else, if the return data is not tuple and is string this means exception/error was thrown 
            # and error message is returned. Append the error message as either a regular or galex modal 
            # error message.
            elif isinstance(pm_corrected_coords, str):
                if 'GALEX' not in pm_corrected_coords:
                    # if it is a regular error message, this means something went wrong with the coordinates/object 
                    # and the search needs to break because the same coords/object will not search on the NEA dataset
                    self.modal_page_error_msg = pm_corrected_coords
                    return
                else:
                    # else if it is just a GALEX error, we can continue onto searching the NASA Exoplanet Archive 
                    # for stellar intrinsic parameters
                    self.modal_error_msgs.append(pm_corrected_coords)
        # STEP 2: Search NASA Exoplanet Archive with the search term & type
        nea_data = self.query_nasa_exoplanet_archive(self.star_name, self.coords)
        if nea_data is not None:
            # if the NEA search didn't return anything, then the object either doesn't exist or isn't an exoplanet 
            # host star. Functionality is not built in yet for non-exoplanet host stars, so we break the function 
            # and tell user to input parameters manually.

            # self.modal_page_error_msg = nea_data
            self.modal_error_msgs.append(nea_data)
            # return
        # STEP 3: Get the stellar subtype. Needed for GALEX flux predictions if a flux is null
        self.get_stellar_subtype(self.teff, self.logg, self.mass)
        # STEP 4: Check if coordinate correction happened then search GALEX with corrected/converted coords
        galex_data = self.query_galex(self.star_name, self.position, self.pm_corrected_coords, self.coords)
        if galex_data is not None:
            self.modal_error_msgs.append(galex_data)
            return

    def convert_coords(self, position):
        """Converts the position attribute to equatorial coordinates (coords attribute) using the SkyCoord class from the astropy.coordinates module.
        Args:
            position: The user's inputted position from search form.

        Side effects:
            Sets the coordinates of the stellar object.

        Raises:
            ValueError: If the position attribute is not in the expected format.
            TypeError: If the position attribute is not a string or a tuple of two strings.
            Exception: If an unknown error occurs during the coordinate conversion process.
        """
        try:
            c = SkyCoord(position, unit=(u.hourangle, u.deg))
            self.coords = (c.ra.degree, c.dec.degree)
            return
        except ValueError as ve:
            return (f'Invalid position attribute: {ve}')
        except TypeError as te:
            return (f'Invalid position attribute: {te}')
        except Exception as e:
            return (f'Unknown error during coordinate conversion: {e}')

    def query_simbad(self, star_name):
        """Searches the SIMBAD astronomical database to retrieve data on a specified star.
        Args:
            star_name: The user's inputted star name from the search form.

        Side effects:
            Sets the coordinates and proper motion data of the stellar object.

        Raises:
            Request Exception: If SIMBAD is down, will throw flash error on modal telling user SIMBAD is down.
            Exception: If an error occurs during the SIMBAD search, or if no data is found for the specified star.
        """
        try:
            # Check if SIMBAD is accessible
            simbad_response = requests.get("http://simbad.cds.unistra.fr/simbad/")
            if simbad_response.status_code != 200:
                return "SIMBAD is currently down. Cannot get data to correct for proper motion. Please enter GALEX flux values manually or try again later."
            
            result_table = customSimbad.query_object(star_name)
            if result_table and len(result_table) > 0:
                data = result_table[0]
                self.coords = (data['RA'], data['DEC'])
                self.pm_data = ProperMotionData(
                    data['PMRA'], data['PMDEC'], data['PLX_VALUE'])
                # check if radial velocity exists
                if not ma.is_masked(data['RV_VALUE']):
                    self.pm_data.rad_vel = data['RV_VALUE']
                return
            else:
                return (f'No results found in SIMBAD for {star_name}. Please check spelling, spacing, and or capitalization and try again.')
        except requests.exceptions.RequestException as rqe:
            print(f'In depth SIMBAD error: {rqe}')
            return f"Error connecting to SIMBAD. Cannot get data to correct for proper motion. Please enter GALEX flux values manually or try again later."
        except Exception as e:
            print(f'In depth SIMBAD error: {e}')
            return (f'Unknown error during SIMBAD search: {e}')

    def query_nasa_exoplanet_archive(self, star_name, coords):
        """Searches the NASA Exoplanet Archive for stellar parameters.

        Queries the NASA Exoplanet Archive (NExSci) for data on a given star_name or position and sets the attributes
        of the object to the retrieved data. Raises an exception if no results are found in the NExSci database
        for the given input parameters or if the spectral type of the star is not M or K.

        Args:
            star_name: The user's inputted star name from the search form.
            coords: The user's inputted coordinates from the search from, converted to RA and DEC.

        Side effects:
            Sets effective temperature (teff), surface gravity (logg), mass, distance (dist), and radius (rad)
            of the stellar object.

        Raises:
            Sends a string error message to the front end custom error page if no results
            are found or if the target is not a M or K type star.
            Request Exception: If the NASA Exoplanet Archive homepage is down.
            Exception: If any unknown error occurs during search.
        """
        try:
            nea_response = requests.get("https://exoplanetarchive.ipac.caltech.edu/")
            if nea_response.status_code != 200:
                return "The NASA Exoplanet Archive is currently down. Please enter stellar parameters manually or try again later."
            
            if star_name:
                corrected_star_name = star_name.replace("'", "''")
                nea_data = NasaExoplanetArchive.query_criteria(
                    table="pscomppars", 
                    select="top 5 disc_refname, st_spectype, st_teff, st_logg, st_mass, st_rad, sy_dist, sy_jmag", 
                    where=f"hostname like '%{corrected_star_name}%'", 
                    order="hostname")
            elif coords:
                nea_data = NasaExoplanetArchive.query_region(table="pscomppars", coordinates=SkyCoord(
                    ra=coords[0] * u.deg, dec=coords[1] * u.deg), radius=1.0 * u.deg)
            if len(nea_data) > 0:
                data = nea_data[0]
                if 2400 < data['st_teff'].unmasked.value < 5500:
                    self.teff = data['st_teff'].unmasked.value
                    self.logg = data['st_logg']
                    self.mass = data['st_mass'].unmasked.value
                    self.rad = data['st_rad'].unmasked.value
                    self.dist = data['sy_dist'].unmasked.value
                    return
                else:
                    return (f'{star_name if star_name else coords} is not an M or K type star. Data is currently only available for these spectral sybtypes.')
            else:
                return (f'Nothing found for {star_name if star_name else coords} in the NExSci database.')
        except requests.exceptions.RequestException as rqe:
            print(f'In depth NEA error: {rqe}')
            return "Error connecting to the NASA Exoplanet Archive. Please enter stellar parameters manually or try again later."
        except Exception as e:
            return f"Unknown error occured when searching the NASA Exoplanet Archive: {e}"

    def query_galex(self, star_name, position, pm_corrected_coords, coords):
        """Searches the MAST GALEX database by coordinates for flux densities.

        Queries the MAST GALEX database for FUV and NUV flux densities and respective
        errors. If one flux density is missing, the other will be estimated with the
        predict_fluxes() method below.

        Args:
            star_name: The original star name user input from the search bar. Used to see if we should 
                query GALEX with pm_corrected_coords.
            position: The original position user input from the search bar. Used to see if we should 
                query GALEX with coords
            pm_corrected_coords: The proper motion corrected coordinates (RA and DEC) for a given star name.
            coords: RA and Dec to query the database.

        Side Effects:
            Sets GALEX FUV flux density, NUV flux density, FUV flux density error, and NUV flux
            density error for the stellar object's GalexFlux object.
            Will also set saturated and/or upper limits flags and fluxes for the stellar object's 
            GalexFlux object if they exist.

        Raises:
            Sends a string error message if no results are found to be displayed on the
            modal form so users can still enter fluxes manually and get other stellar
            information back.
        """
        # STEP 1: Query the MAST catalogs object by GALEX catalog & given ra and dec
        try:
            # https://galex.stsci.edu/GR6/?page=mastform
            # Check if SIMBAD is accessible
            mast_response = requests.get("https://galex.stsci.edu/GR6/?page=mastform")
            if mast_response.status_code != 200:
                return "MAST is currently down. Please enter GALEX flux values manually or try again later."
            
            galex_data = None
            if star_name and pm_corrected_coords:
                # if the original query was by star name and the proper motion corrected coords exist
                galex_data = Catalogs.query_object(
                    f'{pm_corrected_coords[0]} {pm_corrected_coords[1]}', catalog="GALEX")
            elif position and coords:
                # elif the original query was by position and the coords exist
                galex_data = Catalogs.query_object(
                    f'{coords[0]} {coords[1]}', catalog="GALEX")
            # STEP 2: If there are results returned and results within 0.167 arcmins, then start processing the data.
            if galex_data is not None:
                if len(galex_data) > 0:
                    # Set minimum distance between target coordinates and actual coordinates of object.
                    MIN_DIST = galex_data['distance_arcmin'] < 0.167
                    if len(galex_data[MIN_DIST]) > 0:
                        filtered_data = galex_data[MIN_DIST][0]
                        # create new fluxes object to store data in if there isn't one yet
                        if self.fluxes is None:
                            self.fluxes = GalexFluxes()
                        # STEP 3: Assign the edited stellar object to the flux object
                        # delete any objects within stellar object and assign this to the flux object's stellar object
                        # this is done so the flux object can access attributes from the stellar object such as teff, logg, and mass
                        fluxes_stell_obj = self.__dict__.copy()
                        del fluxes_stell_obj['fluxes']
                        del fluxes_stell_obj['pm_data']
                        self.fluxes.stellar_obj = fluxes_stell_obj
                        # STEP 4: Assign fuv, nuv, and error to flux object
                        self.fluxes.fuv = filtered_data['fuv_flux']
                        self.fluxes.nuv = filtered_data['nuv_flux']
                        self.fluxes.fuv_err = filtered_data['fuv_fluxerr']
                        self.fluxes.nuv_err = filtered_data['nuv_fluxerr']
                        # STEP 5: Check for saturated fluxes
                        if not ma.is_masked(filtered_data['fuv_flux_aper_7']) and filtered_data['fuv_flux_aper_7'] > 34:
                            self.fluxes.fuv_is_saturated = True
                            self.fluxes.fuv_saturated = filtered_data['fuv_flux']
                        else:
                            self.fluxes.fuv_is_saturated = False
                        if not ma.is_masked(filtered_data['nuv_flux_aper_7']) and filtered_data['nuv_flux_aper_7'] > 108:
                            self.fluxes.nuv_is_saturated = True
                            self.fluxes.nuv_saturated = filtered_data['nuv_flux']
                        else:
                            self.fluxes.nuv_is_saturated = False
                        # STEP 6: Check if there are any masked values (these will be null values)
                        null_fluxes = self.fluxes.check_null_fluxes()
                        if null_fluxes is not None:
                            self.modal_error_msgs.append(null_fluxes)
                        saturated_fluxes = self.fluxes.check_saturated_fluxes()
                        if saturated_fluxes is not None:
                            self.modal_error_msgs.append(saturated_fluxes)
                        return
                    else:
                        # No results within 0.167 arc minutes
                        return 'No detection in GALEX FUV and NUV. Look under question 3 on the FAQ page for more information.'
                else:
                    # No results found for the GALEX catalog query
                    return (f'No GALEX observations found. Please enter flux values manually or approximate flux values using the proxy table under question 3 on the FAQ page.')
            else:
                # No results found because proper info was not given for example, will happen if 
                # proper motion correction did not occur and is therefore not given
                return (f'Missing data to query GALEX {"because coordinates were not corrected for proper motion" if star_name else f"for {coords}"}. Please enter flux values manually or approximate flux values using the proxy table under question 3 on the FAQ page.')
        except requests.exceptions.RequestException as rqe:
            print(f'Galex search in depth error: {rqe}')
            return f"Error connecting to MAST. Please enter GALEX flux values manually or try again later."
        except ResolverError as re:
            print(f'Galex search in depth error: {re}')
            return (f'Could not search GALEX catalog with object {coords if position else pm_corrected_coords}. Please enter flux values manually or approximate flux values using the proxy table under question 3 on the FAQ page.')
        except ValueError as ve:
            print(f'Galex search in depth error: {ve}')
            return (f'Could not search GALEX catalog with object {coords if position else pm_corrected_coords}. Please enter flux values manually or approximate flux values using the proxy table under question 3 on the FAQ page.')
        except Exception as e:
            print(f'Galex search in depth error: {e}')
            return (f'Unknown error during GALEX search: {e}')
    
    def get_stellar_subtype(self, teff, logg, mass):
        """Assigns the matching PEGASUS grid stellar subtype to object.

        Args:
            teff: The stellar effective temp (K) of the current stellar object.
            logg: The surface gravity of the current stellar object.
            mass: The mass (in solar masses) of the current stellar object.
        
        Side Effects:
            Sets the object's stellar_subtype attribute.

        Raises:
            TypeError if no subtype was returned from query.
            Exception if any unknown error occurs.
        """
        try:
            matching_subtype = find_matching_subtype(teff, logg, mass)
            try:
                self.stellar_subtype = matching_subtype['model']
            except TypeError as te:
                print(f'In depth stellar subtype search error:', te)
                return(f'No PEGASUS subtype found with inputs: teff={teff}, logg={logg}, and mass={mass}. Please check your input(s) and try again, or manually input your values on the home page manual form.')
        except Exception as e:
            print(f'In depth stellar subtype search error:', e)
            return(f'Unable to find stellar subtype with inputs: teff={teff}, logg={logg}, and mass={mass}. Please check your input and try again, or manually input your values on the home page manual form.')


class PegasusGrid():
    """Represents the PEGASUS grid"""

    def __init__(self, stellar_obj=None):
        self.stellar_obj = stellar_obj

    def query_pegasus_subtype(self):
        """Queries pegasus for stellar subtype based on stellar parameters.
        """
        try:
            matching_subtype = find_matching_subtype(
                self.stellar_obj.teff, self.stellar_obj.logg, self.stellar_obj.mass)

            self.stellar_obj.model_collection = f"{matching_subtype['model'].lower()}_grid"
            return matching_subtype
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)

    def query_pegasus_models_in_limits(self):
        """Queries pegasus models within limits of GALEX fuv and nuv flux densities.
        """
        try:
            models_in_limits = get_models_within_limits(
                self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_fuv,
                self.stellar_obj.fluxes.processed_nuv_err, self.stellar_obj.fluxes.processed_fuv_err,
                self.stellar_obj.model_collection)
            return list(models_in_limits)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)

    def query_pegasus_chi_square(self):
        """Queries pegasus models based on chi square of fuv and nuv flux densities.
        """
        try:
            model_with_chi_squared = get_models_with_chi_squared(
                self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_fuv, self.stellar_obj.model_collection)
            return list(model_with_chi_squared)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)

    def query_pegasus_weighted_fuv(self):
        """Queries pegasus models based on weighted FUV and chi square.
        """
        try:
            models_weighted = get_models_with_weighted_fuv(
                self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_fuv, self.stellar_obj.model_collection)
            return models_weighted
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)

    def query_pegasus_flux_ratio(self):
        """Queries pegasus models based on chi square of flux ratio.
        """
        try:
            models_with_ratios = get_flux_ratios(
                self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_fuv, self.stellar_obj.model_collection)
            return list(models_with_ratios)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)
    
    def query_pegasus_saturated_nuv(self):
        try:
            models_in_limits = get_models_within_limits_saturated_nuv(self.stellar_obj.fluxes.processed_nuv_saturated, self.stellar_obj.fluxes.processed_fuv, self.stellar_obj.fluxes.processed_fuv_err, self.stellar_obj.model_collection)
            return list(models_in_limits)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)
        
    def query_pegasus_saturated_fuv(self):
        try:
            models_in_limits = get_models_within_limits_saturated_fuv(self.stellar_obj.fluxes.processed_fuv_saturated, self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_nuv_err, self.stellar_obj.model_collection)
            return list(models_in_limits)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)
        
    def query_pegasus_upper_limit_nuv(self):
        try:
            models_in_limits = get_models_within_limits_upper_limit_nuv(self.stellar_obj.fluxes.processed_nuv_upper_limit, self.stellar_obj.fluxes.processed_fuv, self.stellar_obj.fluxes.processed_fuv_err, self.stellar_obj.model_collection)
            return list(models_in_limits)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)
        
    def query_pegasus_upper_limit_fuv(self):
        try:
            models_in_limits = get_models_within_limits_upper_limit_fuv(self.stellar_obj.fluxes.processed_fuv_upper_limit, self.stellar_obj.fluxes.processed_nuv, self.stellar_obj.fluxes.processed_nuv_err, self.stellar_obj.model_collection)
            return list(models_in_limits)
        except Exception as e:
            return ('Error fetching PEGASUS models:', e)

class PhoenixModel():
    def __init__(self, fits_filename, teff, logg, mass, euv, fuv, nuv, chi_squared):
        self.fits_filename = fits_filename
        self.teff = teff
        self.logg = logg
        self.mass = mass
        self.euv = euv
        self.fuv = fuv
        self.nuv = nuv
        self.chi_squared = chi_squared

    # def get_fits_data(self):
    #     try:
    #         # STEP 1: Find a GALEX observation time from PEGASUS API
    #         url = 'http://phoenixpegasusgrid.com/api/get_model_data'
    #         params = {'fits_filename': self.fits_filename}
    #         response = requests.get(url, params=params)
    #         response.raise_for_status()  # raise an exception if the status code is not 200 OK
    #         fits_data = dict(response.json())  # parse the response as JSON
    #         self.wv_data = fits_data['wavelength_data']
    #         self.flux_data = fits_data['flux_data']
    #         return fits_data
    #     except requests.exceptions.RequestException as e:
    #         return ('Error fetching FITS file data:', e)
    #     except ValueError as e:
    #         return ('Error fetching FITS file data:', response.json(), e)
