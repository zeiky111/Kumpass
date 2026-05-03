# Train SVC for Finger Spelling

## 1) CSV format

Required columns:
- label
- handedness
- x0,y0,z0 ... x20,y20,z20

Example header:

label,handedness,x0,y0,z0,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4,x5,y5,z5,x6,y6,z6,x7,y7,z7,x8,y8,z8,x9,y9,z9,x10,y10,z10,x11,y11,z11,x12,y12,z12,x13,y13,z13,x14,y14,z14,x15,y15,z15,x16,y16,z16,x17,y17,z17,x18,y18,z18,x19,y19,z19,x20,y20,z20

Labels currently supported by classifier pipeline:
A,B,D,F,I,L,W,Y

## 2) Train command

From backend folder:

python training/train_svc_from_csv.py --csv training/landmarks.csv --out models/fingerspelling_svc.joblib

## 3) Use trained model

Restart Django server after training. The app auto-loads:
models/fingerspelling_svc.joblib

If model file is missing, app falls back to synthetic bootstrap model.
