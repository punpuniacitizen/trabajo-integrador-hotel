import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # El puerto se puede cambiar con la variable PORT (por defecto, 5000)
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
