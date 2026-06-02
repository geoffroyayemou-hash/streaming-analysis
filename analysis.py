# streaming incident analysis
# using incident log data from my streaming ops work to practice cleaning + visualization
# goal: find the failure patterns that cause the longest triage times

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

df = pd.read_csv("incident_logs.csv", parse_dates=["timestamp"])
print(f"loaded {len(df)} rows")
print(df.head())
print(df.dtypes)

# --- cleaning ---

# always check nulls first - had a groupby silently break on me once because of this
print("\nnull counts:")
print(df.isnull().sum())

df = df.drop_duplicates(subset=["incident_id"])

# strip whitespace + lowercase so groupby doesn't split "Stream_Drop" and "stream_drop"
df["event_type"] = df["event_type"].str.strip().str.lower()
df["severity"]   = df["severity"].str.strip().str.lower()
df["region"]     = df["region"].str.strip()
df["resolution_method"] = df["resolution_method"].str.strip().str.lower()

# flag anything beyond 3 std devs as an outlier
# covered this in my stats courses - basically catches the really weird ones
mean_rt = df["resolution_time_min"].mean()
std_rt  = df["resolution_time_min"].std()
df["is_outlier"] = df["resolution_time_min"] > (mean_rt + 3 * std_rt)
print(f"\noutliers flagged: {df['is_outlier'].sum()}")

# time features - need these for slicing in power bi
df["date"]        = df["timestamp"].dt.date
df["hour"]        = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.day_name()
df["month"]       = df["timestamp"].dt.to_period("M").astype(str)

# --- analysis ---

print("\n--- failure types ---")
failure_counts = df.groupby("event_type").agg(
    count=("incident_id", "count"),
    avg_res_min=("resolution_time_min", "mean"),
    n_critical=("severity", lambda x: (x == "critical").sum())
).sort_values("count", ascending=False)
print(failure_counts.round(1))

print("\n--- severity split ---")
print(df["severity"].value_counts())

print("\n--- by region ---")
region_summary = df.groupby("region").agg(
    count=("incident_id", "count"),
    avg_res_min=("resolution_time_min", "mean")
).sort_values("count", ascending=False)
print(region_summary.round(1))

# peak hours - want to cross-reference this with broadcast schedule later
# TODO: overlay against actual event calendar once i get access
print("\n--- peak hours (top 5) ---")
print(df.groupby("hour")["incident_id"].count().sort_values(ascending=False).head(5))

# triage time estimate
# if operators already know the top patterns, they skip a lot of the guesswork
# rough assumption: 30% faster for recognized patterns - could refine this later
baseline = df["resolution_time_min"].mean()
top3 = failure_counts.index[:3].tolist()
df["known_pattern"] = df["event_type"].isin(top3)
post_avg = df.loc[df["known_pattern"], "resolution_time_min"].mean() * 0.70

print(f"\nbaseline avg resolution: {baseline:.1f} min")
print(f"estimated with pattern awareness: {post_avg:.1f} min")
print(f"reduction: {((baseline - post_avg) / baseline) * 100:.1f}%")

# --- exports for power bi ---

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

print("\nexports saved to /exports/")

# --- quick charts to sanity check before dashboard ---

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

fc = failure_counts.reset_index()
ax1.barh(fc["event_type"], fc["count"], color="#4472C4")
ax1.set_xlabel("count")
ax1.set_title("incidents by type")
ax1.invert_yaxis()

sev = df.groupby("severity")["resolution_time_min"].mean().sort_values()
colors = {"low": "#70AD47", "medium": "#FFC000", "high": "#FF0000", "critical": "#7030A0"}
ax2.bar(sev.index, sev.values, color=[colors.get(s, "#aaa") for s in sev.index])
ax2.set_ylabel("avg resolution (min)")
ax2.set_title("resolution time by severity")

plt.tight_layout()
plt.savefig("exports/charts.png", dpi=150)
print("chart saved")
plt.show()
