from euv_spectra_app.extensions import app
from euv_spectra_app.main.routes import main

app.register_blueprint(main)

if __name__ == "__main__":
    app.run(debug=True, port=5002, host='0.0.0.0')