import os
import joblib
from django.conf import settings


MODEL_PATH = os.path.join(
    settings.BASE_DIR,
    "ml",
    "complaint_classifier_model.pkl"
)


_model = None


def load_model():
    global _model

    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"AI model topilmadi: {MODEL_PATH}. "
                "Avval python ml/train_model.py buyrug‘ini ishga tushiring."
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def classify_report_text(text: str) -> str:
    """
    Murojaat matnini AI model orqali kategoriya qiladi.
    Natija: road, waste, traffic, ecology yoki other.
    """
    if not text or not text.strip():
        return "other"

    model = load_model()
    prediction = model.predict([text.strip()])[0]

    return str(prediction)