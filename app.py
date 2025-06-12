import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

# Settings for plots
sns.set(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

# Replace with your repo details
owner = "ONDC-Official"
repo = "pramaan"
issues_url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=closed&per_page=100"
milestones_url = f"https://api.github.com/repos/{owner}/{repo}/milestones?state=all"
headers = {"Accept": "application/vnd.github.v3+json"}

# Fetch closed issues
issues_response = requests.get(issues_url, headers=headers)
issues = issues_response.json()

# Process closed issues
data = []
resolution_times = []
for issue in issues:
    if "pull_request" not in issue:
        created_at = pd.to_datetime(issue["created_at"])
        closed_at = pd.to_datetime(issue["closed_at"])
        resolution_time_days = (closed_at - created_at).total_seconds() / (3600 * 24)
        resolution_times.append(resolution_time_days)
        data.append([
            issue["number"],
            issue["title"],
            created_at,
            closed_at,
            resolution_time_days
        ])

df = pd.DataFrame(data, columns=["Issue #", "Title", "Created At", "Closed At", "Resolution Time (Days)"])

# Plot: Resolution times
fig1 = plt.figure()
sns.barplot(x="Issue #", y="Resolution Time (Days)", data=df, color="skyblue")
plt.axhline(y=sum(resolution_times)/len(resolution_times), color='red', linestyle='--', label='Average')
plt.xticks(rotation=90)
plt.title("Resolution Time (Days) per Closed Issue")
plt.legend()
plt.tight_layout()
plt.show()

# Fetch milestones
milestones_response = requests.get(milestones_url, headers=headers)
milestones = milestones_response.json()

# Process milestone data
milestone_data = []
for milestone in milestones:
    milestone_data.append({
        "Milestone": milestone["title"],
        "Open Issues": milestone["open_issues"],
        "URL": milestone["html_url"]
    })

milestone_df = pd.DataFrame(milestone_data)

# Plot: Open issues per milestone
fig2 = plt.figure()
sns.barplot(x="Milestone", y="Open Issues", data=milestone_df, palette="muted")
plt.title("Open Issues per Milestone")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Display milestone URLs
# from IPython.display import display, Markdown
# for _, row in milestone_df.iterrows():
#     display(Markdown(f"- *{row['Milestone']}*: [Link]({row['URL']}) — {row['Open Issues']} open issues"))


st.pyplot(fig1)
st.pyplot(fig2)
st.button('Refresh', on_click=st.rerun)
