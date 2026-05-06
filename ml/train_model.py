import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATASET_PATH = os.path.join(BASE_DIR, "dataset.csv")
MODEL_PATH = os.path.join(BASE_DIR, "complaint_classifier_model.pkl")
REPORT_PATH = os.path.join(BASE_DIR, "classification_report.txt")
PREDICTIONS_PATH = os.path.join(BASE_DIR, "test_predictions.csv")


def main():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset topilmadi: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)

    required_columns = {"text", "category"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"Datasetda quyidagi ustunlar yo‘q: {missing_columns}")

    df = df.dropna(subset=["text", "category"])

    X = df["text"].astype(str)
    y = df["category"].astype(str)

    if len(df) < 10:
        raise ValueError("Dataset juda kichik. Kamida 10 ta yozuv bo‘lishi kerak.")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.30,
        random_state=42,
        stratify=y
    )

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ("classifier", RandomForestClassifier(
            n_estimators=200,
            random_state=42,
            class_weight="balanced"
        ))
    ])

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )

    report = classification_report(
        y_test,
        y_pred,
        zero_division=0
    )

    cm = confusion_matrix(y_test, y_pred)

    joblib.dump(model, MODEL_PATH)

    result_text = (
        "GeomapGov AI classification report\n"
        f"Accuracy: {accuracy:.4f}\n"
        f"Precision(weighted): {precision:.4f}\n"
        f"Recall(weighted): {recall:.4f}\n"
        f"F1-score(weighted): {f1:.4f}\n\n"
        f"{report}\n\n"
        f"Confusion matrix:\n{cm}\n"
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(result_text)

    predictions_df = pd.DataFrame({
        "text": X_test,
        "actual": y_test,
        "predicted": y_pred
    })

    predictions_df.to_csv(PREDICTIONS_PATH, index=False)

    print("✅ Model muvaffaqiyatli o‘rgatildi.")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-score: {f1:.4f}")
    print(f"Model saqlandi: {MODEL_PATH}")
    print(f"Hisobot saqlandi: {REPORT_PATH}")
    print(f"Predictions saqlandi: {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()