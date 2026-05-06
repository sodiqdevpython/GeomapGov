import joblib

model = joblib.load("ml/model.pkl")
vectorizer = joblib.load("ml/vectorizer.pkl")

def classify(text):
    X = vectorizer.transform([text])
    return model.predict(X)[0]