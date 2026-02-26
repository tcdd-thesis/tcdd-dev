uv venv backend/.venv --system-site-packages --seed
source backend/.venv/bin/activate
uv pip install -r backend/rpidev.requirements.txt
uv pip install --force-reinstall simplejpeg