"""
Streaming Incident Dashboard — Analysis Script
Author: Geoffroy Ayemou
Description: Cleans and analyzes 6 months of production incident logs,
             identifies top failure patterns, and exports summary data
             for Power BI dashboard ingestion.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

# ─── 1. LOAD & INSPECT ────────────────────────────────────────────────────────
df = pd.read_csv("incident_logs.csv", parse_dates=["timestamp"])
print(f"Loaded {len(df)} records | Columns: {list(df.columns)}")
print(df.dtypes)
print(df.head())

# ─── 2. DATA CLEANING ─────────────────────────────────────────────────────────
# Check for nulls
print("\nNull counts:\n", df.isnull().sum())

# Remove any duplicate incident IDs
df = df.drop_duplicates(subset=["incident_id"])

# Normalize text columns
df["event_type"] = df["event_type"].str.strip().str.lower()
df["severity"] = df["severity"].str.strip().str.lower()
df["region"] = df["region"].str.strip()
df["resolution_method"] = df["resolution_method"].str.strip().str.lower()

# Cap extreme resolution times (flag outliers > 3 std devs)
mean_rt = df["resolution_time_min"].mean()
std_rt = df["resolution_time_min"].std()
df["is_outlier"] = df["resolution_time_min"] > (mean_rt + 3 * std_rt)
print(f"\nOutlier incidents (resolution > 3σ): {df['is_outlier'].sum()}")

# Extract time features
df["date"] = df["timestamp"].dt.date
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.day_name()
df["month"] = df["timestamp"].dt.to_period("M").astype(str)

# ─── 3. FAILURE PATTERN ANALYSIS ──────────────────────────────────────────────
print("\n=== TOP FAILURE TYPES ===")
failure_counts = df.groupby("event_type").agg(
    count=("incident_id", "count"),
    avg_resolution_min=("resolution_time_min", "mean"),
    critical_count=("severity", lambda x: (x == "critical").sum())
).sort_values("count", ascending=False)
print(failure_counts.round(1))

print("\n=== SEVERITY DISTRIBUTION ===")
print(df["severity"].value_counts())

print("\n=== INCIDENTS BY REGION ===")
region_summary = df.groupby("region").agg(
    count=("incident_id", "count"),
    avg_resolution_min=("resolution_time_min", "mean")
).sort_values("count", ascending=False)
print(region_summary.round(1))

print("\n=== PEAK INCIDENT HOURS ===")
hourly = df.groupby("hour")["incident_id"].count().sort_values(ascending=False)
print(hourly.head(5))

# ─── 4. TRIAGE TIME REDUCTION ESTIMATE ────────────────────────────────────────
# Baseline: avg resolution time without pattern awareness
baseline_avg = df["resolution_time_min"].mean()

# Post-analysis: incidents matching top-3 failure types resolve faster (simulated)
top_3_types = failure_counts.index[:3].tolist()
df["is_known_pattern"] = df["event_type"].isin(top_3_types)
post_avg = df.loc[df["is_known_pattern"], "resolution_time_min"].mean() * 0.70  # 30% improvement
print(f"\nBaseline avg resolution: {baseline_avg:.1f} min")
print(f"Post-dashboard avg (simulated): {post_avg:.1f} min")
print(f"Simulated triage time reduction: {((baseline_avg - post_avg)/baseline_avg)*100:.1f}%")

# ─── 5. EXPORT SUMMARY TABLES FOR POWER BI ────────────────────────────────────
os.makedirs("exports", exist_ok=True)

# Monthly trend
monthly_trend = df.groupby("month").agg(
    incidents=("incident_id", "count"),
    avg_resolution_min=("resolution_time_min", "mean"),
    critical_incidents=("severity", lambda x: (x == "critical").sum())
).reset_index()
monthly_trend.to_csv("exports/monthly_trend.csv", index=False)

# Failure type summary
failure_counts.reset_index().to_csv("exports/failure_type_summary.csv", index=False)

# Region summary
region_summary.reset_index().to_csv("exports/region_summary.csv", index=False)

# Full cleaned dataset
df.to_csv("exports/incidents_cleaned.csv", index=False)

print("\nExports written to /exports/")

# ─── 6. QUICK MATPLOTLIB PREVIEW CHARTS ───────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Streaming Incident Analysis — Summary", fontsize=14, fontweight="bold")

# Chart 1: Incident count by event type
ax1 = axes[0]
fc = failure_counts.reset_index()
ax1.barh(fc["event_type"], fc["count"], color="#00d4ff")
ax1.set_xlabel("Incident Count")
ax1.set_title("Incidents by Event Type")
ax1.invert_yaxis()

# Chart 2: Avg resolution time by severity
ax2 = axes[1]
sev_rt = df.groupby("severity")["resolution_time_min"].mean().sort_values()
colors = {"low": "#4caf50", "medium": "#ff9800", "high": "#f44336", "critical": "#9c27b0"}
ax2.bar(sev_rt.index, sev_rt.values, color=[colors.get(s, "#999") for s in sev_rt.index])
ax2.set_ylabel("Avg Resolution Time (min)")
ax2.set_title("Resolution Time by Severity")

plt.tight_layout()
plt.savefig("exports/summary_charts.png", dpi=150)
print("Chart saved to exports/summary_charts.png")
plt.show()
