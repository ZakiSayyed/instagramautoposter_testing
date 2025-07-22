#Testing
from datetime import datetime, timedelta, date
import time
import streamlit as st
import requests
import pandas as pd
from PIL import Image
import pillow_heif
import os
import base64
from supabase import create_client, Client
from pillow_heif import register_heif_opener
from dateutil import parser
import pytz
import re
from streamlit_calendar import calendar
import cloudinary
import cloudinary.uploader

register_heif_opener()

# Use secrets from Streamlit Cloud
ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
IG_USER_ID = st.secrets["IG_USER_ID"]
API_VERSION = st.secrets["API_VERSION"]
CLOUD_NAME = st.secrets["CLOUD_NAME"]
API_KEY = st.secrets["API_KEY"]
API_SECRET = st.secrets["API_SECRET"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{IG_USER_ID}/insights"
SUPABASE_URL = st.secrets["SUPABASE_URL"]
USERNAME = st.secrets["USER_NAME"]
PASSWORD = st.secrets["USER_PASSWORD"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]  # Add this to your secrets.toml
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
GRAPH_URL = "https://graph.facebook.com/v23.0"
CLOUD_NAME = st.secrets["CLOUD_NAME"]
API_KEY = st.secrets["API_KEY"]

#______________________________________________________________________________________________________#
# 🌐 Configure Cloudinary
cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=API_KEY,
    api_secret=API_SECRET
)
def upload_to_cloudinary(image_path):
    try:
        result = cloudinary.uploader.upload(image_path)
        url = result.get("secure_url")
        print(f"✅ Uploaded to Cloudinary: {url}")
        return url
    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        return None
    
#______________________________________________________________________________________________________#

def get_recent_media(limit=5):
    url = f"{GRAPH_URL}/{IG_USER_ID}/media"
    params = {
        "fields": "id,timestamp,caption,media_type,media_url",
        "limit": limit,
        "access_token": ACCESS_TOKEN
    }
    res = requests.get(url, params=params).json()
    return res.get('data', [])

def get_media_engagement(media_id):
    url = f"{GRAPH_URL}/{media_id}/insights"
    params = {
        "metric": "reach,likes,comments,shares,saved,total_interactions",
        "access_token": ACCESS_TOKEN
    }
    res = requests.get(url, params=params).json()
    insights = res.get("data", [])

    if not insights:
        return {}

    return {i['name']: i['values'][0]['value'] for i in insights}

def build_post_insight_json():
    posts = get_recent_media()
    bundle = []

    for post in posts:
        post_data = {
            "id": post["id"],
            "caption": post["caption"]
        }

        # Parse timestamps
        timestamp_utc = parser.isoparse(post["timestamp"])
        timestamp_est = timestamp_utc.astimezone(pytz.timezone("US/Eastern"))
        post_data["timestamp_est"] = timestamp_est.isoformat()
        # Add engagement
        metrics = get_media_engagement(post["id"])
        post_data["metrics"] = metrics

        bundle.append(post_data)

    return bundle

#______________________________________________________________________________________________________#
#Database codes

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def update_posting_configs(num_of_posts, frequency, dont_use_until):
    try:
        updates = [
            {"config_name": "num_of_posts", "config_value": str(num_of_posts)},
            {"config_name": "frequency", "config_value": frequency},
            {"config_name": "dontuseuntil", "config_value": str(dont_use_until)},
        ]

        for update in updates:
            response = supabase.table("config") \
                .update({"config_value": update["config_value"]}) \
                .eq("config_name", update["config_name"]) \
                .execute()

            if response.data:
                print(f"✅ Updated {update['config_name']} to {update['config_value']}")
            else:
                print(f"❌ Failed to update {update['config_name']} (no data returned)")

    except Exception as e:
        print(f"❌ Error updating configs: {e}")

def fetch_posting_configs():
    try:
        config_keys = ["num_of_posts", "frequency", "dontuseuntil"]

        response = supabase.table("config") \
            .select("config_name, config_value") \
            .in_("config_name", config_keys) \
            .execute()

        if not response.data:
            print("❌ No config values found.")
            return None

        # Create a dictionary from the results
        config_map = {item["config_name"]: item["config_value"] for item in response.data}

        # Extract and return values with defaults if not found
        num_of_posts = int(config_map.get("num_of_posts", 1))
        frequency = config_map.get("frequency", "Daily")
        dont_use_until = int(config_map.get("dontuseuntil", 0))

        return num_of_posts, frequency, dont_use_until

    except Exception as e:
        print(f"❌ Error fetching configs: {e}")
        return None


# def check_posts_with_dont_use_until_today():
#     today = date.today()
#     try:
#         response = supabase.table("postsdb") \
#             .select("*") \
#             .execute()
#         matching_posts = []
#         for post in response.data:
#             dont_use_until_str = post.get("dont_use_until")
#             if dont_use_until_str:
#                 try:
#                     # Parse the string into a datetime object
#                     dont_use_until_dt = datetime.strptime(dont_use_until_str.strip(), "%Y-%m-%d %H:%M:%S")

#                     # Compare only the date parts
#                     if dont_use_until_dt.date() == today:
#                         matching_posts.append(post)

#                 except ValueError as ve:
#                     print(f"⚠️ Skipping invalid datetime: {dont_use_until_str} ({ve})")
#         if matching_posts:
#             for post in matching_posts:
#                 print(f"📌 Match found: {post['image_path']} — {post['dont_use_until']}")
#                 reuse_post(post['id'])
#                 if response:
#                     print("Post ready to reuse")
#                     time.sleep(2)
#                 # schedule_post(post['id'])
#                 pass
#         else:
#             print("✅ No posts with today's dont_use_until date.")

#     except Exception as e:
#         print(f"❌ Error checking posts: {e}")

# def check_reusable_posts():
#     try:
#         response = supabase.table("postsdb") \
#             .select("id, caption, scheduled_time") \
#             .eq("caption", "") \
#             .eq("scheduled_time", "") \
#             .execute()

#         if response.data:
#             reusable_ids = [post["id"] for post in response.data]
#             print(f"✅ Reusable Post IDs: {reusable_ids}")
#             return reusable_ids
#         else:
#             print("✅ No reusable posts found.")
#             return []

#     except Exception as e:
#         print(f"❌ Error checking reusable posts: {e}")
#         return []

# def schedule_post(post_ids, dont_use_until=90):
#     for post_id in post_ids:
#         used_hours = set()
#         try:
#             response = supabase.table("postsdb") \
#                 .select("*") \
#                 .eq("id", post_id) \
#                 .single() \
#                 .execute()

#             if response.data:
#                 image_url = response.data.get("image_url")
#                 image_path = response.data.get("image_path")
                
#                 print(f"Image URL: {image_url}")
                
#                 engagement_data = build_post_insight_json() 
#                 generated_caption = generate_caption(
#                             None,
#                             None,
#                             engagement_data,
#                             used_hours,
#                             image_url
#                         )

#                 generated_output = generated_caption
#                 print(f"Generated caption: {generated_output}")
#                 caption = generated_output.split("Recommended Time:")[0].strip()

#                 hour = 12  # Default
#                 match = re.search(r"(\d{1,2})\s*(AM|PM)", generated_output, re.IGNORECASE)
#                 if match:
#                     hour = int(match.group(1))
#                     used_hours.add(hour)
#                     period = match.group(2).upper()
#                     if period == "PM" and hour != 12:
#                         hour += 12
#                     elif period == "AM" and hour == 12:
#                         hour = 0
#                     start_date = datetime.today().date()
#                     selected_time = datetime.combine(start_date, datetime.min.time()).replace(hour=hour, minute=0)
#                     dontuseuntill = datetime.combine(start_date + timedelta(days=dont_use_until), datetime.min.time()).replace(hour=hour, minute=0)
#                     print(dontuseuntill)
#                     update_resuseable_posts(post_id, caption, selected_time, dontuseuntill)                           
#                 else:
#                     print("⚠️ Recommended time not found, using 12:00 PM default")
#                     st.warning("⚠️ Recommended time not found, using 12:00 PM default")
#                     start_date = datetime.today().date()
#                     post_date = start_date + timedelta(days=batch_num * interval_days)
#                     selected_time = datetime.combine(post_date, datetime.min.time()).replace(hour=hour, minute=0)
#                     dontuseuntill = datetime.combine(post_date + timedelta(days=dont_use_until), datetime.min.time()).replace(hour=hour, minute=0)
#                     print(dontuseuntill)
#                     update_resuseable_posts(post_id, caption, selected_time, dontuseuntill)    

#             else:
#                 print(f"❌ No post found with id: {post_id}")
        
#         except Exception as e:
#             print(f"❌ Error fetching post: {e}")

# def reuse_post(post_id):
#     response = supabase.table("postsdb") \
#         .update({
#             "scheduled_time": "",       # Empty string
#             "caption": "",              # Empty string
#             "posted": "Pending",        # Set status to "Pending"
#             "dont_use_until": ""        # Empty string
#         }) \
#         .eq("id", post_id) \
#         .execute()

#     return response

# # Check if a post with the same image and scheduled time is already scheduled
# def post_already_scheduled(image_name, scheduled_time):
#     image_path = f"uploads/{image_name}"
#     scheduled_time = str(scheduled_time)
    
#     response = supabase.table("postsdb").select("*") \
#         .eq("image_path", image_path) \
#         .eq("scheduled_time", scheduled_time) \
#         .execute()
    
#     return bool(response.data)

# def post_already_scheduled_check(image_name):
#     image_path = image_name
#     response = supabase.table("postsdb").select("*") \
#         .eq("image_path", image_path) \
#         .execute()

#     return bool(response.data)

# Add a new post to the Supabase database
def add_post(image_path, caption, scheduled_time, url, dontuse):
    data = {
        "image_path": image_path,
        "caption": caption,
        "scheduled_time": str(scheduled_time),
        "posted": "Pending",
        "image_url": url,
        "dont_use_until": str(dontuse)
    }
    supabase.table("postsdb").insert(data).execute()

def update_resuseable_posts(post_id, caption, scheduled_time, dontuse):
    data = {
        "caption": caption,
        "scheduled_time": str(scheduled_time),
        "posted": "Pending",
        "dont_use_until": str(dontuse)
    }

    response = supabase.table("postsdb") \
        .update(data) \
        .eq("id", post_id) \
        .execute()

    return response

# Update a single column in a post by post ID
def update_post(post_id, colname, value):
    response = supabase.table("postsdb") \
        .update({colname: str(value)}) \
        .eq("id", post_id) \
        .execute()
    return response

# Retrieve all posts ordered by scheduled time (ascending)
def get_all_posts():
    response = supabase.table("postsdb").select("*") \
        .order("scheduled_time", desc=False) \
        .execute()
    return response.data if response.data else []

def delete_post(post_id):
    supabase.table("postsdb") \
        .delete() \
        .eq("id", post_id) \
        .execute()
#End of Database codes
#______________________________________________________________________________________________________#


METRICS = [
    "views", "reach", "likes", "comments", "shares",
    "saves", "replies", "accounts_engaged", "total_interactions"
]

# Metrics that support time_series
TIME_SERIES_SUPPORTED = ["reach"]

# Fetch total_value (default)
def fetch_total_value(metric):
    params = {
        "metric": metric,
        "period": "day",
        "metric_type": "total_value",
        "access_token": ACCESS_TOKEN
    }
    r = requests.get(BASE_URL, params=params)
    return r.json()

# Fetch time_series (only for reach)
def fetch_time_series(metric):
    params = {
        "metric": metric,
        "period": "day",
        "metric_type": "time_series",
        "access_token": ACCESS_TOKEN
    }
    r = requests.get(BASE_URL, params=params)
    return r.json()

# Process total or time-series data
def get_metric_data(metric):
    if metric in TIME_SERIES_SUPPORTED:
        res = fetch_time_series(metric)
        if "error" in res or not res.get("data"):
            return None, None, res.get("error", {}).get("message", "No data")
        values = res["data"][0].get("values", [])
        df = pd.DataFrame(values)
        df["end_time"] = pd.to_datetime(df["end_time"])
        df.rename(columns={"value": "Value", "end_time": "Date"}, inplace=True)
        return df, df["Value"].sum(), None
    else:
        res = fetch_total_value(metric)
        if "error" in res or not res.get("data"):
            return None, None, res.get("error", {}).get("message", "No data")
        val = res["data"][0]["total_value"].get("value", 0)
        today = pd.to_datetime("today").normalize()
        df = pd.DataFrame([{"Date": today, "Value": val}])
        return df, val, None
    
#Insights functions
def get_account_insights(IG_USER_ID, access_token):

    url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/insights"

    # Only metrics that actually work with period=day
    metrics = [
        "reach"  # only one reliably working as of API v18
    ]

    params = {
        "metric": ",".join(metrics),
        "period": "days_28",
        "access_token": access_token
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        print("❌ Error fetching account insights:", response.status_code, response.text)
        return []
 
def get_ig_business_account_id(page_id, access_token):
    url = f'https://graph.facebook.com/v19.0/{page_id}'
    params = {
        'fields': 'instagram_business_account',
        'access_token': access_token
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data.get('instagram_business_account', {}).get('id')

def get_profile_info(IG_USER_ID, access_token):
    url = f'https://graph.facebook.com/v19.0/{IG_USER_ID}'
    params = {
        'fields': 'username,name,biography,website,profile_picture_url,followers_count,media_count',
        'access_token': access_token
    }
    response = requests.get(url, params=params)
    return response.json()

def get_recent_posts(IG_USER_ID, access_token):
    url = f'https://graph.facebook.com/v19.0/{IG_USER_ID}/media'
    params = {
        'fields': 'id,caption,media_type,media_url,timestamp,like_count,comments_count',
        'access_token': access_token
    }
    response = requests.get(url, params=params)
    return response.json().get('data', [])

def get_post_insights(media_id, access_token):
    url = f'https://graph.facebook.com/v19.0/{media_id}/insights'
    params = {
        'metric': 'impressions,reach,engagement,saved',
        'access_token': access_token
    }
    response = requests.get(url, params=params)
    return response.json().get('data', [])

from PIL import Image

# Re-save uploaded image to ensure format compatibility
def convert_image(input_path, output_format='jpg'):
    if output_format.lower() not in ['jpg', 'png']:
        raise ValueError("Output format must be 'jpg' or 'png'")

    # Register HEIF plugin
    pillow_heif.register_heif_opener()

    image = Image.open(input_path)
    output_path = os.path.splitext(input_path)[0] + f".{output_format}"
    image_format = 'JPEG' if output_format.lower() == 'jpg' else 'PNG'
    image.save(output_path, format=image_format)
    # print(f"Converted: {input_path} → {output_path}")
    return output_path

st.set_page_config(page_title="Instagram Auto Poster")
posting_status = False

# Set up session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Only show Login menu if not logged in
if not st.session_state.logged_in:
    st.sidebar.title("Instagram Auto Poster")
    st.title("🔐 Login to Instagram")
    st.write("Please enter your Instagram credentials to continue.")

    entered_username = st.text_input("Username", type="default")
    entered_password = st.text_input("Password", type="password")

    if st.button("Login"):
        if entered_username and entered_password:
            if entered_username == USERNAME and entered_password == PASSWORD:
                st.success("Login successful! Redirecting to Home page...")
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid username or password.")
        else:
            st.error("Please enter both username and password.")
else:

    menu = st.sidebar.selectbox(
        "Select a page:",
        ["Home", "Configuration", "Analytics", "Detailed Insights", "Scheduled Posts", "Logout"]
    )
    # Display content based on menu selection
    if menu == "Home":
        st.title("📱 Instagram Auto Poster")
        st.write("Welcome to the Home page!")

        st.header("Select schedule criteria")
        num_of_posts = st.number_input("Number of posts per interval", min_value=1, step=1, format="%d")
        frequency = st.selectbox("Post frequency", ["Daily", "Weekly", "Monthly"])
        dont_use_until = st.number_input(f"Do not use for next - Days", min_value=0, step=1, format="%d")
        if st.button("Update Critera"):
            update_posting_configs(str(num_of_posts), str(frequency), str(dont_use_until))
            st.success("Configuration updated successfully!")
            time.sleep(2)
            st.rerun()
        st.header("Current Critera")
        configs = fetch_posting_configs()
        dont_use_until1 = configs[2]
        num_of_posts1 = configs[0]
        frequency1 = configs[1]
        st.write(f"Don't use for the next {dont_use_until1} days")
        st.write(f"Number of posts: {num_of_posts1}")
        st.write(f"Frequency: {frequency1}")      

    elif menu == "Analytics":
        st.title("📊 Analytics Dashboard")
        tab1, tab2 = st.tabs(["📄 Profile Info", "📸 Recent Posts"])

        with tab1:
            profile = get_profile_info(IG_USER_ID, ACCESS_TOKEN)

            st.subheader(f"Username: {profile.get('username')}")
            st.write(f"**Name:** {profile.get('name')}")
            st.write(f"**Biography:** {profile.get('biography')}")
            st.write(f"**Website:** {profile.get('website')}")
            st.image(profile.get('profile_picture_url'), width=150)
            st.write(f"**Followers Count:** {profile.get('followers_count')}")
            st.write(f"**Total Media Posts:** {profile.get('media_count')}")

        with tab2:
            posts = get_recent_posts(IG_USER_ID, ACCESS_TOKEN)

            for i in range(0, len(posts), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(posts):
                        post = posts[i + j]
                        with cols[j]:
                            st.markdown("---")
                            st.write(f"**Post ID:** {post['id']}")
                            # st.write(f"**Caption:** {post.get('caption', 'N/A')}")
                            st.write(f"**Media Type:** {post['media_type']}")
                            if post['media_type'] == "IMAGE":
                                st.image(post['media_url'], width=300)
                            elif post['media_type'] == "VIDEO":
                                st.video(post['media_url'])
                            elif post['media_type'] == "CAROUSEL_ALBUM":
                                st.write("Carousel post. [View Media]({})".format(post['media_url']))
                            else:
                                st.write(f"Media URL: {post['media_url']}")
                            # st.write(f"**Timestamp:** {post['timestamp']}")
                            ts = post['timestamp']
                            
                            try:
                                # Fix timezone format for fromisoformat
                                ts_fixed = ts.replace("+0000", "+00:00")
                                dt = datetime.fromisoformat(ts_fixed)
                                st.write(f"**Date:** {dt.date()} | **Time:** {dt.strftime('%H:%M:%S')}")
                            except Exception:
                                st.write(f"**Timestamp:** {ts}")                       
                            st.write(f"**Like Count:** {post.get('like_count', 'N/A')}")
                            st.write(f"**Comments Count:** {post.get('comments_count', 'N/A')}")

    elif menu == "Detailed Insights":
        #Prod
        import streamlit as st
        import requests
        import pandas as pd
        import plotly.express as px
        import json
        import os

        # Metrics we want to show
        METRICS = [
            "views", "reach", "likes", "comments", "shares",
            "saves", "replies", "accounts_engaged", "total_interactions"
        ]

        # Metrics that support time_series
        TIME_SERIES_SUPPORTED = ["reach"]

        # Fetch total_value (default)
        def fetch_total_value(metric):
            params = {
                "metric": metric,
                "period": "day",
                "metric_type": "total_value",
                "access_token": ACCESS_TOKEN
            }
            r = requests.get(BASE_URL, params=params)
            return r.json()

        def fetch_total_value_lifetime(metric):
            params = {
                "metric": metric,
                "period": "day",  # or "day", "days_28"
                "metric_type": "total_value",
                "access_token": ACCESS_TOKEN
            }
            r = requests.get(BASE_URL, params=params)
            return r.json()

        # Fetch time_series (only for reach)
        def fetch_time_series(metric):
            params = {
                "metric": metric,
                "period": "day",  # or "day", "week"
                "metric_type": "time_series",
                "access_token": ACCESS_TOKEN
            }
            r = requests.get(BASE_URL, params=params)
            return r.json()

        # Process total or time-series data
        def get_metric_data(metric):
            if metric in TIME_SERIES_SUPPORTED:
                res = fetch_time_series(metric)
                if "error" in res or not res.get("data"):
                    return None, None, res.get("error", {}).get("message", "No data")
                values = res["data"][0].get("values", [])
                df = pd.DataFrame(values)
                df["end_time"] = pd.to_datetime(df["end_time"])
                df.rename(columns={"value": "Value", "end_time": "Date"}, inplace=True)
                return df, df["Value"].sum(), None
            else:
                res = fetch_total_value(metric)
                if "error" in res or not res.get("data"):
                    return None, None, res.get("error", {}).get("message", "No data")
                val = res["data"][0]["total_value"].get("value", 0)
                today = pd.to_datetime("today").normalize()
                df = pd.DataFrame([{"Date": today, "Value": val}])
                return df, val, None

        def get_aggregated_metric(metric):
            url = f"https://graph.facebook.com/{API_VERSION}/{IG_USER_ID}/media"
            params = {
                "fields": f"{metric}",
                "access_token": ACCESS_TOKEN,
                "limit": 100  # adjust as needed
            }
            r = requests.get(url, params=params)
            data = r.json().get("data", [])
            return sum(item.get(metric, 0) for item in data)


        st.title("📊 Instagram Insights Dashboard")

        tab1, tab2 = st.tabs(["📋 Table View", "📈 Charts View"])

        # --- TAB 1: TABLE VIEW ---
        with tab1:
            METRIC_FIELD_MAP = {
                "likes": "like_count",
                "comments": "comments_count",
                # "shares": "shares_count",  # Only if available
            }    
            st.subheader("📋 Summary Table")
            rows = []
            # List of metrics to aggregate from media
            AGGREGATE_FROM_MEDIA = list(METRIC_FIELD_MAP.keys())

            for metric in METRICS:
                if metric in AGGREGATE_FROM_MEDIA:
                    field = METRIC_FIELD_MAP[metric]
                    val = get_aggregated_metric(field)
                    err = None
                else:
                    _, val, err = get_metric_data(metric)
                rows.append({
                    "Metric": metric.replace("_", " ").title(),
                    "Value": val if val is not None else f"⚠️ {err}"
                })
            st.table(pd.DataFrame(rows))

            with tab2:
                st.subheader("📈 Metric Visualizations")

                # Each row contains 3 charts
                col_index = 0
                chart_cols = st.columns(2)

                # Define a funnel order if you want to show a funnel
                FUNNEL_METRICS = ["reach", "accounts_engaged", "total_interactions"]

                # Prepare funnel data
                funnel_data = []
                for metric in FUNNEL_METRICS:
                    _, val, err = get_metric_data(metric)
                    funnel_data.append({"Metric": metric.replace("_", " ").title(), "Value": val if val is not None else 0})

                for idx, metric in enumerate(METRICS):
                    col = chart_cols[col_index]
                    with col:
                        st.markdown(f"#### {metric.replace('_', ' ').title()}")

                        # Area chart for time series
                        if metric in TIME_SERIES_SUPPORTED:
                            df_ts, _, err = get_metric_data(metric)
                            if err:
                                st.warning(f"{metric}: {err}")
                            elif df_ts is not None:
                                # Convert to date only and group by date (in case there are multiple times per day)
                                df_ts["Date"] = pd.to_datetime(df_ts["Date"]).dt.date
                                df_ts = df_ts.groupby("Date", as_index=False)["Value"].sum()
                                # Sort by date ascending
                                df_ts = df_ts.sort_values("Date", ascending=True)
                                st.write(df_ts)  # Add this line to inspect your data
                                fig = px.bar(df_ts, x="Date", y="Value", title=metric.replace("_", " ").title())
                                st.plotly_chart(fig, use_container_width=True)

                        # Funnel chart for the funnel metrics (only show once)
                        elif metric == FUNNEL_METRICS[0]:
                            df_funnel = pd.DataFrame(funnel_data)
                            fig = px.funnel(df_funnel, x="Value", y="Metric", title="Funnel: Reach → Engaged → Interactions")
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            if metric in AGGREGATE_FROM_MEDIA:
                                field = METRIC_FIELD_MAP[metric]
                                total = get_aggregated_metric(field)
                                df = pd.DataFrame([{"Metric": metric.replace("_", " ").title(), "Value": total}])
                                fig = px.bar(df, x="Metric", y="Value", title=f"{metric.replace('_', ' ').title()} (Aggregated)")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                # Try breakdowns for donut chart
                                res = fetch_total_value(metric)

                                if "error" in res or not res.get("data"):
                                    st.warning(f"{metric}: {res.get('error', {}).get('message', 'No data')}")
                                else:
                                    item = res["data"][0]
                                    breakdowns = item["total_value"].get("breakdowns", [])
                                    if breakdowns:
                                        breakdown_data = []
                                        for br in breakdowns:
                                            for r in br["results"]:
                                                dims = " | ".join(r["dimension_values"])
                                                breakdown_data.append({"Category": dims, "Value": r["value"]})
                                        df = pd.DataFrame(breakdown_data)
                                        if not df.empty:
                                            fig = px.pie(df, names="Category", values="Value", hole=0.4)
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.info("No breakdown data available.")
                                    else:
                                        # Just show total as bar
                                        total = item["total_value"].get("value", 0)
                                        df = pd.DataFrame([{"Metric": metric, "Value": total}])
                                        fig = px.bar(df, x="Metric", y="Value")
                                        st.plotly_chart(fig, use_container_width=True)

                    col_index = (col_index + 1) % 2
                    if col_index == 0 and idx != len(METRICS) - 1:
                        chart_cols = st.columns(2)
        st.markdown("----")

    elif menu == "Scheduled Posts":
        st.title("📅 Scheduled Posts Calendar View")
        tab1, tab2 = st.tabs(["📅 Calendar View", "📝 Manage Scheduled Posts"])
        with tab1:
            posts = get_all_posts()
            # print("Fetched posts", posts)

            if posts:
                # Transform posts into calendar events
                calendar_events = []
                for post in posts:
                    # Create a hover-friendly string with ID, status, caption
                    hover_text = (
                        f"ID: {post['id']}\n"
                        f"Status: {post['posted']}\n"
                        
                        # f"Caption: {post.get('caption', 'No caption')}"
                    )
                    
                    calendar_events.append({
                        "title": hover_text,  # This will show on hover
                        "start": post['scheduled_time'],
                        "color": "#28a745" if post["posted"] else "#ffc107",
                    })
                
                options = {
                    "initialView": "dayGridMonth",
                    "editable": False,
                    "selectable": False,
                    "height": 650,
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay"
                    },
                    "eventTimeFormat": {
                        "hour": "numeric",
                        "minute": "2-digit",
                        "meridiem": "short",
                        "hour12": True
                    }
                }

                calendar(events=calendar_events, options=options)

            else:
                st.info("No scheduled posts found.")

            with tab2:
                st.subheader("Manage Scheduled Posts")
                posts = sorted(posts, key=lambda x: x['id'], reverse=True)

                for post in posts:
                    with st.expander(f"📌 Post ID {post['id']}", expanded=False):
                        action_col1, action_col2, action_col3 = st.columns([6, 2, 2])
                        with action_col1:
                            st.write(
                                f"**ID:** {post['id']} | "
                                f"**Time:** {post['scheduled_time']} | "
                                f"**Status:** {post['posted']} |"
                            )

                        with action_col2:
                            if st.button("Delete", key=f"delete_{post['id']}"):
                                delete_post(post['id'])
                                st.success(f"Deleted post ID {post['id']}")
                                st.rerun()

                        with action_col3:
                            edit_date = st.checkbox("✏️ Edit Date", key=f"edit_date_toggle_{post['id']}")

                        if edit_date:
                            post_dt = (
                                datetime.fromisoformat(post['scheduled_time'])
                                if isinstance(post['scheduled_time'], str)
                                else post['scheduled_time']
                            )
                            new_date = st.date_input(f"Date", value=post_dt.date())
                            new_time = st.time_input(f"Time", value=post_dt.time())
                            new_datetime = datetime.combine(new_date, new_time)

                            if new_datetime != post_dt:
                                if st.button("Save New Time", key=f"save_{post['id']}"):
                                    update_post(post['id'], 'scheduled_time', new_datetime)
                                    st.success(f"Updated post ID {post['id']} to {new_datetime}")
                                    time.sleep(1)
                                    st.rerun()

                        # Layout for caption and image
                        left_col, right_col = st.columns([3, 1])

                        with left_col:
                            if post.get("caption"):
                                default_caption = post.get("caption", "")
                                new_caption = st.text_area(
                                    "Edit Caption",
                                    value=default_caption,
                                    key=f"caption_input_{post['id']}",
                                    height=150,
                                )

                                if new_caption != default_caption:
                                    if st.button("Update Caption", key=f"update_caption_{post['id']}"):
                                        update_post(post['id'], 'caption', new_caption)
                                        st.success("Caption updated successfully.")
                                        time.sleep(1)
                                        st.rerun()

                        with right_col:
                            if post.get("image_url"):
                                st.image(post["image_url"], width=150, caption="Preview")

    elif menu == "Configuration":
        st.warning("This feature is under development. Please check back later.")
    #     DEFAULT_CONFIG_KEYS = [
    #     "ACCESS_TOKEN", "IG_USER_ID"
    # ]
    #     st.title("🔧 Configuration")
    #     st.write("Configure your Instagram API settings here.")

        # for key in DEFAULT_CONFIG_KEYS:
        #     config[key] = st.text_input(
        #         f"Enter {key.replace('_', ' ').title()}:",
        #         value=config.get(key, ""),
        #         type="password" if "TOKEN" in key or "SECRET" in key or "KEY" in key else "default"
        #     )

        # if st.button("Save Configuration"):
        #     save_config(config)
        #     st.success("Configuration saved! Please reload the app.")
        #     st.stop()

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.success("You have been logged out successfully.")
        st.rerun()