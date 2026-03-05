import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
import joblib

# Load dataset
df = pd.read_csv("dataset.csv")

# Encode mood (categorical → numeric)
le = LabelEncoder()
df["mood"] = le.fit_transform(df["mood"])

# Features
X = df[[
    "study_minutes",
    "workout_minutes",
    "entertainment_minutes",
    "scrolling_minutes",
    "sleep_minutes",
    "mood"
]]

# Target
y = df["label"]

# Train / Test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train model
model = DecisionTreeClassifier()
model.fit(X_train, y_train)

# Test accuracy
predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

print("Model Accuracy:", accuracy)

# Save model
joblib.dump(model, "productivity_model.pkl")

# Save encoder
joblib.dump(le, "mood_encoder.pkl")

print("Model saved successfully")