Drop word/phrase sequence recordings exported from collect-phrases.html into
this folder (any filename, .jsonl extension). Then run:

    python backend/scripts/train_word_model.py

from the backend/ directory (with the virtualenv active) to train and
deploy the local phrase model. Each line in a .jsonl file is one recorded
gesture:

    {"label": "HELLO", "handedness": "Right", "frames": [[[x,y,z]*21], ...], "duration_ms": 2500}

which is exactly what the collector tool exports. Only phrases that have
real recorded sequences will be recognized by the trained model -- there is
no synthetic filler for words the way there is for letters, since a gesture
can't be reasonably hand-guessed.
