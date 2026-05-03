from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from signtext.fingerspelling_svc import CLASS_LABELS, extract_features_from_landmarks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train fingerspelling SVC from landmarks CSV")
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to CSV file with columns: label, handedness, x0,y0,z0 ... x20,y20,z20",
    )
    parser.add_argument(
        "--out",
        default="models/fingerspelling_svc.joblib",
        help="Output model path",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio",
    )
    return parser.parse_args()


def row_to_landmarks(row: Dict[str, str]) -> List[Dict[str, float]]:
    landmarks: List[Dict[str, float]] = []
    for i in range(21):
        landmarks.append(
            {
                "x": float(row[f"x{i}"]),
                "y": float(row[f"y{i}"]),
                "z": float(row[f"z{i}"]),
            }
        )
    return landmarks


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    out_path = Path(args.out)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    features: List[np.ndarray] = []
    labels: List[str] = []

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row.get("label", "").strip().upper()
            if label not in CLASS_LABELS:
                continue

            handedness = row.get("handedness", "Right").strip() or "Right"
            landmarks = row_to_landmarks(row)
            feat = extract_features_from_landmarks(landmarks, handedness)
            features.append(feat[0])
            labels.append(label)

    if len(labels) < 40:
        raise ValueError("Not enough samples. Collect at least 40 valid rows.")

    x = np.asarray(features, dtype=np.float32)
    y = np.asarray(labels)

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=args.test_size,
        random_state=42,
        stratify=y,
    )

    model = make_pipeline(
        StandardScaler(),
        SVC(kernel="rbf", C=8.0, gamma="scale", probability=True),
    )
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    report = classification_report(y_test, y_pred, labels=CLASS_LABELS, zero_division=0)
    print("Classification report:\n")
    print(report)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_path)
    print(f"Saved model to: {out_path}")


if __name__ == "__main__":
    main()
