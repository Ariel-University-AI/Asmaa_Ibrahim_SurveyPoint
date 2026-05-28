import pandas as pd
import glob
import os
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

models = {}

for folder in ["1", "2", "3", "4"]:
    files = glob.glob(f"DATA/{folder}/*.csv") + glob.glob(f"DATA/{folder}/*.CSV")
    
    if not files:
        print(f"תיקייה {folder}: לא נמצאו קבצים")
        continue
    
    df = None
    for enc in ["utf-8-sig", "cp1255", "utf-8", "latin-1"]:
        try:
            df = pd.read_csv(files[0], encoding=enc)
            df.columns = ["שם נקודה", "Y", "X"]
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df = df.dropna(subset=["Y", "X"])
            break
        except:
            continue
    
    if df is None or len(df) < 5:
        print(f"תיקייה {folder}: אין מספיק נתונים")
        continue

    # train_test_split
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
    
    # אימון על train בלבד
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(train_df[["Y", "X"]])
    
    # בדיקה על test
    test_df = test_df.copy()
    test_df["תקין"] = model.predict(test_df[["Y", "X"]])
    חריגים = len(test_df[test_df["תקין"] == -1])
    
    print(f"תיקייה {folder}: train={len(train_df)}, test={len(test_df)}, חריגים בtest={חריגים} ✅")
    models[folder] = model

# שמירה
os.makedirs("Model", exist_ok=True)
joblib.dump(models, "Model/model.pkl")
print(f"\nנשמרו {len(models)} מודלים ✅")