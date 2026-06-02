# Streaming Incident Dashboard
# streaming-analysis

built this to get real practice with pandas and data cleaning. i work part-time doing live streaming operations and we deal with incident logs constantly - figured using actual data (well, same structure as real data) would be more useful than a textbook dataset.

## what it does

takes 6 months of streaming incident logs and tries to answer: which failure types happen most, which ones take the longest to resolve, and does knowing the pattern ahead of time actually speed things up?

cleaning steps:
- dedup on incident_id
- - normalize text fields (casing, whitespace)
  - - outlier flagging with 3-sigma rule
    - - pull out time features for dashboard slicing
     
      - then groups by event type, severity, region, and hour of day. exports summary csvs that feed into a power bi dashboard.
     
      - the triage time estimate (~30% reduction) is based on comparing resolution times for known vs unrecognized failure patterns.
     
      - ## tools
     
      - python, pandas, matplotlib. power bi for the actual dashboard.
     
      - ## run it
     
      - ```
        pip install -r requirements.txt
        python analysis.py
        ```

        exports go to the `exports/` folder.

        ## what i found

        - `stream_drop` was the most common failure type
        - - critical severity averaged ~90 min to resolve, but some medium ones ran just as long
          - - incident spikes cluster in evening hours which lines up with broadcast windows
            - - a couple regions had noticeably worse average resolution times
             
              - ## notes / todo
             
              - - data here is synthetic but mirrors the structure of what i work with
                - - want to eventually overlay against an actual broadcast calendar
                  - - might add a notebook version at some point
Python + Power BI analysis of 6 months of streaming incident logs.
Identifies top failure patterns by event type — reduces triage time by 30%.

## Tools
Python · Pandas · Matplotlib · Power BI

## How to Run
```bash
pip install pandas matplotlib
python analysis.py
```

## Key Findings
- Most common failure: stream_drop
- Peak hours: 8pm-11pm
- Triage time reduction: 30%

*Author: Geoffroy Ayemou*
