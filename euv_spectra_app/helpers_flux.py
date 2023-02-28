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
    def __init__(self, fuv='No Detection', fuv_err='No Detection', nuv='No Detection', nuv_err='No Detection', scale=None):
        self.fuv = fuv
        self.fuv_err = fuv_err
        self.nuv = nuv
        self.nuv_err = nuv_err
        self.scale = scale

    def predict_fluxes(self, flux_type, j_band):
        """Calculates a predicted flux if the value is missing from GALEX.

        Args:
            flux_type: Either fuv or nuv, specified to know which equation to use.

        Returns:
            A predicted nuv or fuv flux value and corresponding error.
        """
        # STEP 1: Convert J band 2MASS magnitude to microjanskies
        ZEROPOINT = 1594
        j_band_ujy = 1000 * (ZEROPOINT * pow(10.0, -0.4 * j_band))
        # STEP 3: Use equation to predict missing flux & error
        if flux_type == 'nuv':
            print('OLD NUV', self.nuv, self.nuv_err)
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
            print('NEW NUV', self.nuv, self.nuv_err)
        elif flux_type == 'fuv':
            print('OLD FUV', self.fuv, self.fuv_err)
            upper_lim = self.nuv + self.nuv_err
            lower_lim = self.nuv - self.nuv_err
            print('J BAND', j_band_ujy)
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
            print('NEW FUV', self.fuv, self.fuv_err)
        else:
            print('Cannot correct for that flux type, can only do FUV and NUV.')

