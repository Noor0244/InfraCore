
# InfraCore

## Run (Windows)

1) Create/activate the virtual environment (once per terminal):

- `venv\Scripts\Activate.ps1`

2) Install dependencies:

- `pip install -r requirements.txt`

3) Start the server (use the venv interpreter):

- `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

If you run `uvicorn app.main:app` without activating the venv, Windows may pick a global `uvicorn.exe` (e.g. from `C:\Users\...\Python311\Scripts`) and you can hit missing-module errors like `ModuleNotFoundError: No module named 'itsdangerous'`.

