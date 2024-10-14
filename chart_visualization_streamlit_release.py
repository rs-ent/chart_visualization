import requests
import streamlit as st

url = 'https://circlechart.kr/page_chart/onoff.circle?nationGbn=T&serviceGbn=S1040&targetTime=8&hitYear=2024&termGbn=month&yearTime=3'
try:
    response = requests.get(url)
    if response.status_code == 200:
        st.write(f"Successfully accessed {url}")
    else:
        st.write(f"Failed to access {url} with status code {response.status_code}")
except Exception as e:
    st.write(f"Error accessing {url}: {e}")
