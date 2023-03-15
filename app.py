from euv_spectra_app.extensions import app
from euv_spectra_app.main.routes import main
from euv_spectra_app.api.routes import api

app.register_blueprint(main)
app.register_blueprint(api)

if __name__ == "__main__":
    app.run(port=5002, host='0.0.0.0')