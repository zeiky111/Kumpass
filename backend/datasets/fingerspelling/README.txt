Drop fingerspelling landmark CSVs exported from collect-landmarks.html into this
folder (any filename, .csv extension). Then run:

    python backend/scripts/train_fingerspelling_model.py

from the backend/ directory (with the virtualenv active) to train and deploy
the model. Each CSV must have the header:

    label,handedness,x0,y0,z0,x1,y1,z1,...,x20,y20,z20

which is exactly what the collector tool exports.
