# FOR ASTROQUERY/GALEX DATA
import numpy.ma as ma
from astropy.time import Time
import astropy.units as u
from astropy.coordinates import SkyCoord, Distance
from astroquery.mast import Catalogs
from astroquery.ipac.nexsci.nasa_exoplanet_archive import NasaExoplanetArchive
from astroquery.simbad import Simbad
from euv_spectra_app.extensions import db
from euv_spectra_app.helpers_dbqueries import find_matching_subtype, find_matching_photosphere, get_models_with_chi_squared, get_models_within_limits, get_models_with_weighted_fuv, get_flux_ratios

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
            Exception: If an error occurs during the API request or coordinate correction.
        """
        try:
            # STEP 1: Find a GALEX observation time from custom compiled dataset
            galex_time = db.mast_galex_times.find_one(
                {'target': star_name})['t_min']
        except:
            return 'No GALEX observations found, unable to correct coordinates. \nLook under question 3 on the FAQ page for more information.'
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
                return ("Unknown error during proper motion correction:" + str(e))


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

    def __init__(self, fuv=None, nuv=None, fuv_err=None, nuv_err=None, nuv_aper=None, fuv_aper=None, j_band=None, stellar_obj=None):
        self.fuv = fuv
        self.nuv = nuv
        self.fuv_err = fuv_err
        self.nuv_err = nuv_err
        self.nuv_aper = nuv_aper
        self.fuv_aper = fuv_aper
        self.j_band = j_band
        self.stellar_obj = stellar_obj

    def check_null_fluxes(self):
        if self.fuv is None and self.nuv is None:
            return ('Values of GALEX FUV and NUV cannot be None.')
        if ma.is_masked(self.fuv) and ma.is_masked(self.nuv):
            # all fluxes are null/ no galex data
            self.fuv, self.fuv_err = 'No Detection', 'No Detection'
            self.nuv, self.nuv_err = 'No Detection', 'No Detection'
            return ('No GALEX detections found.')
        elif ma.is_masked(self.fuv):
            # only FUV is null, predict FUV and add error message
            self.predict_fluxes('fuv')
            return ('GALEX FUV not detected. Predicting for FUV and FUV error.')
        elif ma.is_masked(self.nuv):
            # only NUV is null, predict NUV and add error message
            self.predict_fluxes('nuv')
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
            fuv_is_saturated = self.fuv_aper > 34
            nuv_is_saturated = self.nuv_aper > 108
            if fuv_is_saturated and nuv_is_saturated:
                self.fuv, self.fuv_err = 'No Detection', 'No Detection'
                self.nuv, self.nuv_err = 'No Detection', 'No Detection'
                return ('Both GALEX detection saturated, cannot correct.')
            elif fuv_is_saturated:
                fuv_fluxes, fuv_errors = [self.fuv], [self.fuv_err]
                self.predict_fluxes('fuv')
                fuv_fluxes.append(self.fuv)
                fuv_errors.append(self.fuv_err)
                self.fuv, self.fuv_err = max(fuv_fluxes), max(fuv_errors)
            elif nuv_is_saturated:
                nuv_fluxes, nuv_errors = [self.nuv], [self.nuv_err]
                self.predict_fluxes('nuv')
                nuv_fluxes.append(self.nuv)
                nuv_errors.append(self.nuv_err)
                self.nuv, self.nuv_err = max(nuv_fluxes), max(nuv_errors)
        except ValueError as e:
            return ('Invalid `fuv_aper` and/or `nuv_aper` attributes:' + str(e))

    def predict_fluxes(self, flux_to_predict):
        """Predicts the specified flux based on the remaining GALEX flux values.

        Args:
            flux_to_predict: Either fuv or nuv, specifies which flux to predict for.

        Side Effects:
            If flux_to_predict is 'fuv', sets fuv and fuv_err of GalexFluxes object.
            If flux_to_predict is 'nuv', sets nuv and nuv_err of GalexFluxes object.

        Raises:
            ValueError if j_band is None
        """
        # STEP 1: Check that j_band value exists, if not throw ValueError
        if self.j_band is None:
            return ('2MASS J band magnitude cannot be None. Please include this attribute and try again.')
        # STEP 2: Convert J band 2MASS magnitude to microjanskies
        ZEROPOINT = 1594
        j_band_ujy = 1000 * (ZEROPOINT * pow(10.0, -0.4 * self.j_band))
        # STEP 3: Use equation to predict missing flux & error
        if flux_to_predict == 'nuv':
            upper_lim = self.fuv + self.fuv_err
            lower_lim = self.fuv - self.fuv_err
            # Predict NUV flux using NUV = ((FUV/J)^(1/1.1)) * J
            # STEP N1: Use equation to find upper, lower limits and new flux values
            new_nuv_upper_lim = (
                pow((upper_lim / j_band_ujy), (1 / 1.1))) * j_band_ujy
            new_nuv = (pow((self.fuv / j_band_ujy), (1 / 1.1))) * j_band_ujy
            new_nuv_lower_lim = (
                pow((lower_lim / j_band_ujy), (1 / 1.1))) * j_band_ujy
            # STEP N2: Find the differences between the upper and lower limits and flux value (these will be error)
            #  Then calculate average of these values to get the average error
            upper_nuv = new_nuv_upper_lim - new_nuv
            lower_nuv = new_nuv - new_nuv_lower_lim
            avg_nuv_err = (upper_nuv + lower_nuv) / 2
            # STEP N3: Assign new values to return data dict using calculated flux & error
            self.nuv = new_nuv
            self.nuv_err = avg_nuv_err
        elif flux_to_predict == 'fuv':
            upper_lim = self.nuv + self.nuv_err
            lower_lim = self.nuv - self.nuv_err
            # Predict FUV flux using FUV = ((NUV/J)^1.11) * J
            # STEP F1: Use equation to find upper, lower limits and new flux values
            new_fuv_upper_lim = (
                pow((upper_lim / j_band_ujy), 1.1)) * j_band_ujy
            new_fuv = (pow((self.nuv / j_band_ujy), 1.1)) * j_band_ujy
            new_fuv_lower_lim = (
                pow((lower_lim / j_band_ujy), 1.1)) * j_band_ujy
            # STEP F2: Find the differences between the upper and lower limits and flux value (these will be error)
            #  Then calculate average of these values to get the average error
            upper_fuv = new_fuv_upper_lim - new_fuv
            lower_fuv = new_fuv - new_fuv_lower_lim
            avg_fuv_err = (upper_fuv + lower_fuv) / 2
            # STEP N3: Assign new values to return data dict using calculated flux & error
            self.fuv = new_fuv
            self.fuv_err = avg_fuv_err
        else:
            return ('Can only correct for GALEX fuv and nuv flux densities.')

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
            print('PHOTOSPHERE MODEL', matching_photosphere_model)
            return matching_photosphere_model
        except Exception:
            return ('Cannot find a photosphere model. Please try again.')

    def subtract_photosphere_flux(self, chosen_flux, photo_flux):
        """Subtracts the photospheric contributed flux from GALEX flux."""
        return chosen_flux - photo_flux

    def convert_scale_photosphere_subtract_fluxes(self):
        FUV_WV = 1542.3
        NUV_WV = 2274.4
        photosphere_data = self.get_photosphere_model()

        fuv_lims = self.get_limits(self.fuv, self.fuv_err)
        nuv_lims = self.get_limits(self.nuv, self.nuv_err)

        converted_fuv = self.convert_ujy_to_flux_density(self.fuv, FUV_WV)
        converted_nuv = self.convert_ujy_to_flux_density(self.nuv, NUV_WV)
        scaled_fuv = self.scale_flux(converted_fuv)
        scaled_nuv = self.scale_flux(converted_nuv)
        photosub_fuv = self.subtract_photosphere_flux(
            scaled_fuv, photosphere_data['fuv'])
        photosub_nuv = self.subtract_photosphere_flux(
            scaled_nuv, photosphere_data['nuv'])
        self.processed_fuv = photosub_fuv
        self.processed_nuv = photosub_nuv

        converted_fuv_upper_lim = self.convert_ujy_to_flux_density(
            fuv_lims['upper_lim'], FUV_WV)
        converted_nuv_upper_lim = self.convert_ujy_to_flux_density(
            nuv_lims['upper_lim'], NUV_WV)
        converted_fuv_lower_lim = self.convert_ujy_to_flux_density(
            fuv_lims['lower_lim'], FUV_WV)
        converted_nuv_lower_lim = self.convert_ujy_to_flux_density(
            nuv_lims['lower_lim'], NUV_WV)

        scaled_fuv_upper_lim = self.scale_flux(converted_fuv_upper_lim)
        scaled_nuv_upper_lim = self.scale_flux(converted_nuv_upper_lim)
        scaled_fuv_lower_lim = self.scale_flux(converted_fuv_lower_lim)
        scaled_nuv_lower_lim = self.scale_flux(converted_nuv_lower_lim)

        photosub_fuv_upper_lim = self.subtract_photosphere_flux(
            scaled_fuv_upper_lim, photosphere_data['fuv'])
        photosub_nuv_upper_lim = self.subtract_photosphere_flux(
            scaled_nuv_upper_lim, photosphere_data['nuv'])
        photosub_fuv_lower_lim = self.subtract_photosphere_flux(
            scaled_fuv_lower_lim, photosphere_data['fuv'])
        photosub_nuv_lower_lim = self.subtract_photosphere_flux(
            scaled_nuv_lower_lim, photosphere_data['nuv'])

        new_fuv_upper_err = photosub_fuv_upper_lim - self.processed_fuv
        new_fuv_lower_err = self.processed_fuv - photosub_fuv_lower_lim

        new_nuv_upper_err = photosub_nuv_upper_lim - self.processed_nuv
        new_nuv_lower_err = self.processed_nuv - photosub_nuv_lower_lim

        self.processed_fuv_err = (new_fuv_upper_err + new_fuv_lower_err) / 2
        self.processed_nuv_err = (new_nuv_upper_err + new_nuv_lower_err) / 2


class StellarObject():
    """Represents a stellar object."""

    def __init__(self, star_name=None, position=None, coords=None, teff=None, logg=None, mass=None, dist=None, rad=None, pm_data=None, fluxes=None):
        self.star_name = star_name
        self.position = position
        self.coords = coords
        self.teff = teff
        self.logg = logg
        self.mass = mass
        self.dist = dist
        self.rad = rad
        self.pm_data = pm_data
        self.fluxes = fluxes
        if self.fluxes is None:
            self.fluxes = GalexFluxes()

    def can_query_pegasus(self):
        if self.teff is not None and self.logg is not None and self.mass is not None and self.dist is not None and self.rad is not None and self.fluxes.fuv is not None and self.fluxes.nuv is not None:
            return True
        else:
            return False

    def get_stellar_parameters(self):
        """Searches Astroquery databases for stellar data.

        Searches SIMBAD, the NASA Exoplanet Archive, and MAST GALEX databases for 
        stellar data. Right ascension, declination, proper motion data, radial 
        velocity, parallax, and J band 2MASS magnitude are pulled from SIMBAD. 
        Effective temperature, surface gravity, mass, distance, and radius are pulled 
        from the NASA Exoplanet Archive. GALEX FUV and NUV flux density and the 
        respective errors are pulled from the MAST GALEX database. The data is used to 
        populate the resulting modal form.

        Args:
            star_name OR position: The search term the user submitted in the search bar input.
            search_format: The format the search input is in, either name or position.

        Returns:
            Stellar parameters with cooresponding values to be passed to the modal form

        Raises:
            No errors are raised but if an error is detected, the function returns None and
            an error message is sent to the front end error page to be displayed.
        """
        # STEP 1: Check for search type (position or name)
        if self.position:
            # STEP P1: Change coordinates to ra and dec
            converted_coords = self.convert_coords()
            if converted_coords is not None:
                # will stop function if coords were not converted into usable format
                self.modal_error_msg = converted_coords
                return
        elif self.star_name:
            # STEP N1: Check if name is in the mast target database (meant to check for case & spacing errors)
            data = NasaExoplanetArchive.query_criteria(
                table="pscomppars", select="DISTINCT hostname")
            host_stars = data['hostname']
            for name in host_stars:
                if self.star_name.upper().replace(' ', '') == name.upper().replace(' ', ''):
                    self.star_name = name
                    break
            # STEP N2: Get coordinate and motion info from Simbad
            simbad_data = self.query_simbad()
            if simbad_data is not None:
                # will stop function if no coords found in SIMBAD
                self.modal_error_msg = simbad_data
                return
            # STEP N3: Put PM and Coord info into correction function
            pm_corrected_coords = self.pm_data.correct_pm(
                self.star_name, self.coords)
            if isinstance(pm_corrected_coords, tuple):
                self.coords = pm_corrected_coords
            else:
                self.modal_error_msg = pm_corrected_coords
                if 'GALEX' not in pm_corrected_coords:
                    return
        # STEP 2: Search NASA Exoplanet Archive with the search term & type
        nea_data = self.query_nasa_exoplanet_archive()
        if nea_data is not None:
            self.modal_error_msg = nea_data
            return
        # TODO check that NEA search was successful, allow to continue to galex if not
        # STEP 3: Check if coordinate correction happened then search GALEX with
            # corrected/converted coords
        # if self.star_name is not None and self.pm_data is not None:
            # coordinate correction happened which means GALEX data exists, execute galex query
        galex_data = self.query_galex()
        if galex_data is not None:
            self.modal_error_msg = galex_data
            return
        # TODO check that flux object was successfully created

    def convert_coords(self):
        """Converts the `position` attribute to equatorial coordinates (`coordinates` attribute) using the `SkyCoord` class from the `astropy.coordinates` module.

        Side effects:
            Sets the coordinates of the stellar object.

        Raises:
            ValueError: If the `position` attribute is not in the expected format.
            TypeError: If the `position` attribute is not a string or a tuple of two strings.
            Exception: If an unknown error occurs during the coordinate conversion process.
        """
        try:
            c = SkyCoord(self.position, unit=(u.hourangle, u.deg))
            self.coords = (c.ra.degree, c.dec.degree)
            return
        except ValueError as e:
            return ("Invalid `position` attribute: " + str(e))
        except TypeError as e:
            return ("Invalid `position` attribute: " + str(e))
        except Exception as e:
            return ("Unknown error during coordinate conversion: " + str(e))

    def query_simbad(self):
        """Searches the SIMBAD astronomical database to retrieve data on a specified star.

        Side effects:
            Sets the coordinates and proper motion data of the stellar object.

        Raises:
            Exception: If an error occurs during the SIMBAD search, or if no data is found for the specified star.
        """
        try:
            result_table = customSimbad.query_object(self.star_name)
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
                return (f"No results found in SIMBAD for {self.star_name}. Please check spelling, spacing, and/or capitalization and try again.")
        except Exception as e:
            return ("Unknown error during SIMBAD search:" + str(e))

    def query_nasa_exoplanet_archive(self):
        """Searches the NASA Exoplanet Archive for stellar parameters.

        Queries the NASA Exoplanet Archive (NExSci) for data on a given star_name or position and sets the attributes
        of the object to the retrieved data. Raises an exception if no results are found in the NExSci database
        for the given input parameters or if the spectral type of the star is not M or K.

        Side effects:
            Sets effective temperature (teff), surface gravity (logg), mass, distance (dist), and radius (rad)
            of the stellar object.
            Sets 2MASS J band magitude of GalexFluxes object.

        Raises:
            Sends a string error message to the front end custom error page if no results
            are found or if the target is not a M or K type star.
        """
        error_var = ''
        if self.star_name:
            error_var = self.star_name
            nea_data = NasaExoplanetArchive.query_criteria(
                table="pscomppars", select="top 5 disc_refname, st_spectype, st_teff, st_logg, st_mass, st_rad, sy_dist, sy_jmag", where=f"hostname like '%{self.star_name}%'", order="hostname")
        elif self.position:
            error_var = self.position
            nea_data = NasaExoplanetArchive.query_region(table="pscomppars", coordinates=SkyCoord(
                ra=self.coords[0] * u.deg, dec=self.coords[1] * u.deg), radius=1.0 * u.deg)
        if len(nea_data) > 0:
            data = nea_data[0]
            if 2400 < data['st_teff'].unmasked.value < 5500:
                self.teff = data['st_teff'].unmasked.value
                self.logg = data['st_logg']
                self.mass = data['st_mass'].unmasked.value
                self.rad = data['st_rad'].unmasked.value
                self.dist = data['sy_dist'].unmasked.value
                j_band = data['sy_jmag'].unmasked.value
                if j_band is not None:
                    self.fluxes.j_band = j_band
                return
            else:
                return (f'{error_var} is not an M or K type star. Data is currently only available for these spectral sybtypes.')
        else:
            return (f'No results found in the NExSci database for {error_var}. \
                            At this time, retrieved input parameters are only available for known exoplanet host stars with 2500 K < Teff < 5044 K. \
                            If {error_var} is a known exoplanet host star, please check spelling, spacing, and/or capitalization and try again.')

    def query_galex(self):
        """Searches the MAST GALEX database by coordinates for flux densities.

        Queries the MAST GALEX database for FUV and NUV flux densities and respective
        errors. If one flux density is missing, the other will be estimated with the
        predict_fluxes() method below.

        Args:
            coordinates: RA and Dec to query the database.

        Returns:
            GALEX FUV flux density, NUV flux density, FUV flux density error, and NUV flux
            density error.

        Raises:
            Sends a string error message if no results are found to be displayed on the
            modal form so users can still enter fluxes manually and get other stellar
            information back.
        """
        # STEP 1: Query the MAST catalogs object by GALEX catalog & given ra and dec
        try:
            galex_data = Catalogs.query_object(
                f'{self.coords[0]} {self.coords[1]}', catalog="GALEX")
            # STEP 2: If there are results returned and results within 0.167 arcmins, then start processing the data.
            if len(galex_data) > 0:
                # Set minimum distance between target coordinates and actual coordinates of object.
                MIN_DIST = galex_data['distance_arcmin'] < 0.167
                if len(galex_data[MIN_DIST]) > 0:
                    filtered_data = galex_data[MIN_DIST][0]
                    if self.fluxes is None:
                        self.fluxes = GalexFluxes()
                    fluxes_stell_obj = self.__dict__.copy()
                    del fluxes_stell_obj['fluxes']
                    del fluxes_stell_obj['pm_data']
                    self.fluxes.stellar_obj = fluxes_stell_obj
                    self.fluxes.fuv = filtered_data['fuv_flux']
                    self.fluxes.nuv = filtered_data['nuv_flux']
                    self.fluxes.fuv_err = filtered_data['fuv_fluxerr']
                    self.fluxes.nuv_err = filtered_data['nuv_fluxerr']
                    self.fluxes.fuv_aper = filtered_data['fuv_flux_aper_7']
                    self.fluxes.nuv_aper = filtered_data['fuv_flux_aper_7']
                    # STEP 3: Check if there are any masked values (these will be null values) and change accordingly
                    null_fluxes = self.fluxes.check_null_fluxes()
                    if null_fluxes is not None:
                        self.modal_error_msg = null_fluxes
                    saturated_fluxes = self.fluxes.check_saturated_fluxes()
                    if saturated_fluxes is not None:
                        self.modal_error_msg = saturated_fluxes
                    return
                else:
                    return 'No detection in GALEX FUV and NUV. \nLook under question 3 on the FAQ page for more information.'
            else:
                return 'No GALEX observations found.'
        except Exception as e:
            return ('Unknown error during GALEX search:' + str(e))


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
