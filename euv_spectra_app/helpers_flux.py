class GalexFluxes:
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
        print(self.wv)
        return (((3e-5) * (chosen_flux * 10**-6)) / pow(self.wv, 2))
    
    def scale_flux(self, chosen_flux):
        return chosen_flux * self.scale

    def subtract_photosphere_flux(self, chosen_flux):
        return chosen_flux - self.photo_flux

    def run_calculations(self, chosen_flux):
        converted_flux = self.convert_ujy_to_flux(chosen_flux)
        scaled_flux = self.scale_flux(converted_flux)
        photo_subtracted_flux = self.subtract_photosphere_flux(scaled_flux)
        return photo_subtracted_flux
    
    def return_new_flux(self):
        return self.run_calculations(self.flux)
    
    def return_new_err(self):
        new_flux = self.return_new_flux()
        new_upper_lim = self.run_calculations(self.upper_lim)
        new_lower_lim = self.run_calculations(self.lower_lim)
        new_upper_err = new_upper_lim - new_flux
        new_lower_err = new_flux - new_lower_lim
        new_err = (new_upper_err + new_lower_err) / 2
        return new_err
        