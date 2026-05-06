import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib

df = pd.read_csv("data/dataset.csv")

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df['text'])
y = df['category']

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "ml/model.pkl")
joblib.dump(vectorizer, "ml/vectorizer.pkl")