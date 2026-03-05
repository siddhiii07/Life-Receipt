import pandas as pd
import random

rows = []

moods = ["Happy", "Neutral", "Tired", "Sad", "Energetic"]

for i in range(10000):

    study = random.randint(0,180)
    workout = random.randint(0,90)
    entertainment = random.randint(0,240)
    scrolling = random.randint(0,180)
    sleep = random.randint(300,480)

    mood = random.choice(moods)

    productive_score = study + workout
    leisure_score = entertainment + scrolling

    if productive_score > leisure_score:
        label = "Productive"
    else:
        label = "Leisure"

    rows.append({
        "study_minutes": study,
        "workout_minutes": workout,
        "entertainment_minutes": entertainment,
        "scrolling_minutes": scrolling,
        "sleep_minutes": sleep,
        "mood": mood,
        "label": label
    })

df = pd.DataFrame(rows)

df.to_csv("productivity_dataset.csv", index=False)

print("Dataset with 10,000 rows created successfully")