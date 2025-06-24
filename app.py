import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Settings for plots
sns.set(style="whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)

# Streamlit app configuration
st.set_page_config(page_title="GitHub Issues Analysis", layout="wide")
st.title("GitHub Issues Analysis Dashboard")

# Sidebar for configuration
st.sidebar.header("Configuration")

# Repository settings
owner = st.sidebar.text_input("Repository Owner", value="ONDC-Official")
repo = st.sidebar.text_input("Repository Name", value="pramaan")

# Date filtering options
st.sidebar.header("Filter Options")
filter_type = st.sidebar.selectbox(
    "Filter Type",
    ["All Time", "Specific Day", "Date Range", "Last N Days", "Last N Weeks", "Last N Months"]
)

# Date inputs based on filter type
if filter_type == "Specific Day":
    selected_date = st.sidebar.date_input("Select Date", datetime.now().date())
elif filter_type == "Date Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.sidebar.date_input("Start Date", datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.sidebar.date_input("End Date", datetime.now().date())
elif filter_type == "Last N Days":
    n_days = st.sidebar.number_input("Number of Days", min_value=1, max_value=365, value=30)
elif filter_type == "Last N Weeks":
    n_weeks = st.sidebar.number_input("Number of Weeks", min_value=1, max_value=52, value=4)
elif filter_type == "Last N Months":
    n_months = st.sidebar.number_input("Number of Months", min_value=1, max_value=12, value=3)

# Issue state selection
issue_state = st.sidebar.selectbox("Issue State", ["all", "open", "closed"])

# Function to fetch all issues with pagination
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_issues(owner, repo, state="all"):
    all_issues = []
    page = 1
    per_page = 100
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    with st.progress(0) as progress_bar:
        while True:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            params = {
                "state": state,
                "per_page": per_page,
                "page": page,
                "sort": "created",
                "direction": "desc"
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                st.error(f"Error fetching data: {response.status_code}")
                return []
            
            issues = response.json()
            
            if not issues:
                break
                
            # Filter out pull requests
            issues = [issue for issue in issues if "pull_request" not in issue]
            all_issues.extend(issues)
            
            progress_bar.progress(min(page * per_page / 1000, 1.0))  # Assume max 1000 issues for progress
            page += 1
            
            # Safety break to avoid infinite loop
            if page > 50:  # Max 5000 issues
                break
    
    return all_issues

# Function to filter issues based on date criteria
def filter_issues_by_date(issues, filter_type, **kwargs):
    if filter_type == "All Time":
        return issues
    
    filtered_issues = []
    now = datetime.now()
    
    for issue in issues:
        created_at = pd.to_datetime(issue["created_at"])
        
        if filter_type == "Specific Day":
            target_date = pd.to_datetime(kwargs['selected_date'])
            if created_at.date() == target_date.date():
                filtered_issues.append(issue)
                
        elif filter_type == "Date Range":
            start_date = pd.to_datetime(kwargs['start_date'])
            end_date = pd.to_datetime(kwargs['end_date'])
            if start_date <= created_at <= end_date:
                filtered_issues.append(issue)
                
        elif filter_type == "Last N Days":
            cutoff_date = now - timedelta(days=kwargs['n_days'])
            if created_at >= cutoff_date:
                filtered_issues.append(issue)
                
        elif filter_type == "Last N Weeks":
            cutoff_date = now - timedelta(weeks=kwargs['n_weeks'])
            if created_at >= cutoff_date:
                filtered_issues.append(issue)
                
        elif filter_type == "Last N Months":
            cutoff_date = now - timedelta(days=kwargs['n_months'] * 30)  # Approximate
            if created_at >= cutoff_date:
                filtered_issues.append(issue)
    
    return filtered_issues

# Main execution
if st.sidebar.button("Analyze Issues") or st.session_state.get('auto_run', False):
    st.session_state['auto_run'] = True
    
    with st.spinner("Fetching issues..."):
        all_issues = fetch_all_issues(owner, repo, issue_state)
    
    if not all_issues:
        st.error("No issues found or error fetching data.")
        st.stop()
    
    # Prepare filter parameters
    filter_params = {}
    if filter_type == "Specific Day":
        filter_params['selected_date'] = selected_date
    elif filter_type == "Date Range":
        filter_params['start_date'] = start_date
        filter_params['end_date'] = end_date
    elif filter_type == "Last N Days":
        filter_params['n_days'] = n_days
    elif filter_type == "Last N Weeks":
        filter_params['n_weeks'] = n_weeks
    elif filter_type == "Last N Months":
        filter_params['n_months'] = n_months
    
    # Filter issues
    filtered_issues = filter_issues_by_date(all_issues, filter_type, **filter_params)
    
    # Process issues data
    data = []
    resolution_times = []
    
    for issue in filtered_issues:
        created_at = pd.to_datetime(issue["created_at"])
        closed_at = pd.to_datetime(issue["closed_at"]) if issue["closed_at"] else None
        
        resolution_time_days = None
        if closed_at:
            resolution_time_days = (closed_at - created_at).total_seconds() / (3600 * 24)
            resolution_times.append(resolution_time_days)
        
        data.append({
            "Issue #": issue["number"],
            "Title": issue["title"],
            "Created At": created_at,
            "Closed At": closed_at,
            "Resolution Time (Days)": resolution_time_days,
            "State": issue["state"],
            "Author": issue["user"]["login"],
            "Labels": [label["name"] for label in issue["labels"]]
        })
    
    df = pd.DataFrame(data)
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Issues", len(filtered_issues))
    
    with col2:
        open_issues = len([i for i in filtered_issues if i["state"] == "open"])
        st.metric("Open Issues", open_issues)
    
    with col3:
        closed_issues = len([i for i in filtered_issues if i["state"] == "closed"])
        st.metric("Closed Issues", closed_issues)
    
    with col4:
        if resolution_times:
            avg_resolution = sum(resolution_times) / len(resolution_times)
            st.metric("Avg Resolution Time", f"{avg_resolution:.1f} days")
        else:
            st.metric("Avg Resolution Time", "N/A")
    
    # Issues created over time
    if len(df) > 0:
        st.subheader("Issues Created Over Time")
        
        # Group by date
        df['Created Date'] = df['Created At'].dt.date
        daily_counts = df.groupby('Created Date').size().reset_index(name='Count')
        
        fig_timeline = px.line(daily_counts, x='Created Date', y='Count',
                              title='Issues Created Daily',
                              labels={'Count': 'Number of Issues'})
        st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Issues by day of week
        df['Day of Week'] = df['Created At'].dt.day_name()
        dow_counts = df['Day of Week'].value_counts().reindex([
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Issues by Day of Week")
            fig_dow = px.bar(x=dow_counts.index, y=dow_counts.values,
                           title='Issues Created by Day of Week',
                           labels={'x': 'Day of Week', 'y': 'Number of Issues'})
            st.plotly_chart(fig_dow, use_container_width=True)
        
        with col2:
            if resolution_times:
                st.subheader("Resolution Time Distribution")
                fig_resolution = px.histogram(df[df['Resolution Time (Days)'].notna()], 
                                            x='Resolution Time (Days)',
                                            title='Resolution Time Distribution',
                                            nbins=20)
                st.plotly_chart(fig_resolution, use_container_width=True)
        
        # Issues table
        st.subheader("Issues Details")
        
        # Display options
        show_columns = st.multiselect(
            "Select columns to display:",
            df.columns.tolist(),
            default=["Issue #", "Title", "Created At", "State", "Author"]
        )
        
        if show_columns:
            display_df = df[show_columns].copy()
            if 'Created At' in display_df.columns:
                display_df['Created At'] = display_df['Created At'].dt.strftime('%Y-%m-%d %H:%M')
            if 'Closed At' in display_df.columns:
                display_df['Closed At'] = display_df['Closed At'].dt.strftime('%Y-%m-%d %H:%M')
            
            st.dataframe(display_df, use_container_width=True)
        
        # Export functionality
        if st.button("Export to CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"github_issues_{owner}_{repo}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    else:
        st.warning("No issues found for the selected criteria.")

# Instructions
st.sidebar.markdown("---")
st.sidebar.markdown("### Instructions")
st.sidebar.markdown("""
1. Enter the GitHub repository owner and name
2. Select your desired filter type
3. Configure the date parameters
4. Click 'Analyze Issues' to generate the report
5. Use the export button to download results as CSV
""")

# Auto-refresh option
if st.sidebar.checkbox("Auto-refresh every 5 minutes"):
    st.rerun()
