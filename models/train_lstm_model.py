import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import joblib

# Load dataset
df = pd.read_csv("productivity_dataset.csv")

# Encode mood column
mood_encoder = LabelEncoder()
df["mood"] = mood_encoder.fit_transform(df["mood"])

# Encode label (Productive / Leisure)
label_encoder = LabelEncoder()
df["label"] = label_encoder.fit_transform(df["label"])

# Feature columns
X = df[
    [
        "study_minutes",
        "workout_minutes",
        "entertainment_minutes",
        "scrolling_minutes",
        "sleep_minutes",
        "mood"
    ]
].values

# Target column
y = df["label"].values

# Reshape for LSTM (samples, timesteps, features)
X = X.reshape((X.shape[0], X.shape[1], 1))

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Build LSTM model
model = Sequential()

model.add(LSTM(32, input_shape=(6,1)))
model.add(Dense(16, activation="relu"))
model.add(Dense(2, activation="softmax"))

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

# Train model
model.fit(X_train, y_train, epochs=10, batch_size=32)

# Evaluate model
loss, accuracy = model.evaluate(X_test, y_test)

print("LSTM Accuracy:", accuracy)

# Save model
model.save("models/productivity_lstm_model.h5")

# Save encoders
joblib.dump(mood_encoder, "models/mood_encoder.pkl")
joblib.dump(label_encoder, "models/label_encoder.pkl")

print("LSTM model saved successfully")