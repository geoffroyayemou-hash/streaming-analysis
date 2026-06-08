# Streaming Incident Analysis
# Goal: clean 6 months of production incident logs and identify failure patterns
# that correlate with longer triage times. Summary tables feed a Power BI dashboard.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# --- Load ---

df = pd.read_csv("incident_logs.csv", parse_dates=["timestamp"])
print(f"Loaded {len(df)} records")
print(df.dtypes)
print(df.head())

# --- Clean ---

# Check for nulls before any groupby operations
print("\nNull counts:\n", df.isnull().sum())

df = df.drop_duplicates(subset=["incident_id"])

# Normalize text fields so groupby doesn't split on casing or whitespace
df["event_type"]        = df["event_type"].str.strip().str.lower()
df["severity"]          = df["severity"].str.strip().str.lower()
df["region"]            = df["region"].str.strip()
df["resolution_method"] = df["resolution_method"].str.strip().str.lower()

# Flag outliers beyond 3 standard deviations
mean_rt = df["resolution_time_min"].mean()
std_rt  = df["resolution_time_min"].std()
df["is_outlier"] = df["resolution_time_min"] > (mean_rt + 3 * std_rt)
print(f"\nOutliers flagged: {df['is_outlier'].sum()}")

# Time features for Power BI slicing
df["date"]        = df["timestamp"].dt.date
df["hour"]        = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.day_name()
df["month"]       = df["timestamp"].dt.to_period("M").astype(str)

# --- Analysis ---

print("\n--- Failure Types ---")
failure_counts = df.groupby("event_type").agg(
    count=("incident_id", "count"),
    avg_res_min=("resolution_time_min", "mean"),
    n_critical=("severity", lambda x: (x == "critical").sum())
).sort_values("count", ascending=False)
print(failure_counts.round(1))

print("\n--- Severity Split ---")
print(df["severity"].value_counts())

print("\n--- By Region ---")
region_summary = df.groupby("region").agg(
    count=("incident_id", "count"),
    avg_res_min=("resolution_time_min", "mean")
).sort_values("count", ascending=False)
print(region_summary.round(1))

# Peak hours — want to cross-reference with broadcast schedule eventually
# TODO: overlay against actual event calendar once I get access to the schedule data
# would also be interesting to split by sport vs music vs esports to see if patterns differ
print("\n--- Peak Hours (top 5) ---")
print(df.groupby("hour")["incident_id"].count().sort_values(ascending=False).head(5))

# Triage time estimate
# Assumption: operators who recognize a top-3 pattern resolve ~30% faster
# because they skip diagnostic steps they've already learned to rule out
baseline  = df["resolution_time_min"].mean()
top3      = failure_counts.index[:3].tolist()
df["known_pattern"] = df["event_type"].isin(top3)
post_avg  = df.loc[df["known_pattern"], "resolution_time_min"].mean() * 0.70

print(f"\nBaseline avg resolution:   {baseline:.1f} min")
print(f"Estimated w/ pattern awareness: {post_avg:.1f} min")
print(f"Reduction:                 {((baseline - post_avg) / baseline) * 100:.1f}%")

# --- Export for Power BI ---

os.makedirs("exports", exist_ok=True)

monthly = df.groupby("month").agg(
    incidents=("incident_id", "count"),
    avg_res=("resolution_time_min", "mean"),
    critical=("severity", lambda x: (x == "critical").sum())
).reset_index()
monthly.to_csv("exports/monthly_trend.csv", index=False)

failure_counts.reset_index().to_csv("exports/failure_summary.csv", index=False)
region_summary.reset_index().to_csv("exports/region_summary.csv", index=False)
df.to_csv("exports/incidents_clean.csv", index=False)

print("\nExports saved to /exports/")

# --- Quick Charts ---
# Sanity check before building the full Power BI dashboard

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

fc = failure_counts.reset_index()
ax1.barh(fc["event_type"], fc["count"], color="#4472C4")
ax1.set_xlabel("Count")
ax1.set_title("Incident Count by Failure Type")
ax1.invert_yaxis()

sev    = df.groupby("severity")["resolution_time_min"].mean().sort_values()
colors = {"low": "#70AD47", "medium": "#FFC000", "high": "#FF0000", "critical": "#7030A0"}
ax2.bar(sev.index, sev.values, color=[colors.get(s, "#aaa") for s in sev.index])
ax2.set_ylabel("Avg Resolution (min)")
ax2.set_title("Avg Resolution Time by Severity")

plt.tight_layout()
plt.savefig("exports/charts.png", dpi=150)
print("Chart saved to exports/charts.png")
plt.show()
