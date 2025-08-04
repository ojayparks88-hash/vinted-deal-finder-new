import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime

# Constants
FAVORITES_FILE = "favorites.json"
PREVIOUS_RESULTS_FILE = "previous_results.csv"

# Category map
CATEGORY_MAP = {
    "All": None,
    "Electronics": 3,
    "Women": 1904,
    "Men": 1905,
    "Kids": 1906,
    "Home": 5,
    "Books & Entertainment": 16,
    "Pets": 2107,
}

# Condition map
CONDITION_MAP = {
    1: "New with tag",
    2: "New without tag",
    3: "Very good",
    4: "Good",
    5: "Satisfactory"
}

# Fetch listings
def fetch_vinted_items(search_term, category, limit=100):
    url = "https://www.vinted.fr/api/v2/catalog/items"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    items = []
    pages = (limit // 50) + 1
    fetched = 0

    for page in range(1, pages + 1):
        params = {
            "search_text": search_term,
            "per_page": 50,
            "page": page
        }

        if category != "All":
            params["catalog_ids"] = CATEGORY_MAP[category]

        try:
            res = requests.get(url, params=params, headers=headers)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            break

        for item in data.get("items", []):
            items.append({
                "ID": item["id"],
                "Title": item["title"],
                "Price (€)": item["price"],
                "Brand": item.get("brand", {}).get("title", "Unknown"),
                "Condition": CONDITION_MAP.get(item.get("status_id", 0), "Unknown"),
                "Link": f"https://www.vinted.fr{item['url']}",
                "Created": item.get("created_at", ""),
            })
            fetched += 1
            if fetched >= limit:
                break

    df = pd.DataFrame(items)
    df["Created"] = pd.to_datetime(df["Created"])
    return df

# Load favorites
def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        with open(FAVORITES_FILE, "r") as f:
            return json.load(f)
    return {}

# Save favorites
def save_favorite(name, query):
    favs = load_favorites()
    favs[name] = query
    with open(FAVORITES_FILE, "w") as f:
        json.dump(favs, f, indent=2)

# Compare new listings
def detect_new_items(current_df):
    if not os.path.exists(PREVIOUS_RESULTS_FILE):
        current_df.to_csv(PREVIOUS_RESULTS_FILE, index=False)
        return current_df

    prev_df = pd.read_csv(PREVIOUS_RESULTS_FILE)
    new_ids = set(current_df["ID"]) - set(prev_df["ID"])
    new_listings = current_df[current_df["ID"].isin(new_ids)]
    current_df.to_csv(PREVIOUS_RESULTS_FILE, index=False)
    return new_listings

# Streamlit App
st.title("💡 Vinted Deal Finder with Alerts")

tab1, tab2 = st.tabs(["🔍 Search", "⭐ Favorites"])

with tab1:
    search = st.text_input("Search term", "iPhone")
    category = st.selectbox("Category", list(CATEGORY_MAP.keys()), index=1)
    max_results = st.slider("Results to fetch", 50, 200, 100)

    if st.button("Search Now"):
        df = fetch_vinted_items(search, category, max_results)

        if not df.empty:
            new_items = detect_new_items(df)
            st.success(f"Total listings: {len(df)}")
            if not new_items.empty:
                st.info(f"🆕 New listings since last check: {len(new_items)}")
                st.dataframe(new_items.drop(columns=["Created"]), use_container_width=True)
            else:
                st.write("No new listings since last time.")

            st.download_button("Download All", df.to_csv(index=False), file_name="vinted_all.csv")

            # Save favorite
            fav_name = st.text_input("Save this search as favorite (optional):")
            if fav_name and st.button("Save Favorite"):
                save_favorite(fav_name, {"search": search, "category": category})
                st.success(f"Saved '{fav_name}'!")

        else:
            st.warning("No listings found.")

with tab2:
    st.subheader("Your Favorite Searches")
    favorites = load_favorites()
    if favorites:
        for name, q in favorites.items():
            if st.button(f"Run '{name}'"):
                df = fetch_vinted_items(q["search"], q["category"], 100)
                new = detect_new_items(df)
                st.write(f"Results for: {name} ({q['search']})")
                st.write(f"New listings: {len(new)}")
                st.dataframe(new.drop(columns=["Created"]), use_container_width=True)
    else:
        st.info("No favorites saved yet.")