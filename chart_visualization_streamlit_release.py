# 스포티파이 특성 추출 최종본
# Streamlit 라이브러리
import streamlit as st
st.set_page_config(layout="wide",
                   page_title='Chart Data Visualization')

# 스포티파이 API 및 차트 크롤링용 라이브러리
import time
import spotipy
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from spotipy.oauth2 import SpotifyClientCredentials
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
#from webdriver_manager.chrome import ChromeDriverManager

# 시각화용 라이브러리
import numpy as np
import itertools
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 날짜 변환 라이브러리
from datetime import datetime, timedelta

# 스포티파이 API 접근
client_id = st.secrets['client_id']
client_secret = st.secrets['client_secret']

auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

# API 검색 ID Max 100개 반영 리스트 분할
def get_chunks(lst, chunk_size):
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

# Selenium 으로 Circle Chart 크롤링
def circle_chart_crawling(year, mon):
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    #driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(f"https://circlechart.kr/page_chart/onoff.circle?nationGbn=T&serviceGbn=S1040&targetTime={mon}&hitYear={year}&termGbn=month&yearTime=3")

    html_source = driver.page_source
    soup = BeautifulSoup(html_source, 'html.parser')
    time.sleep(5)

    chart_list = []
    chart_dict = {}

    trs = soup.find('tbody', id='pc_chart_tbody').select('tr')
    for tr in trs:
        chart_in_song = tr.find('div', class_='font-bold mb-2').text
        if '(' in chart_in_song:
            chart_in_song = chart_in_song.split(' (')[0]
        chart_in_artist = tr.find('div', class_='text-sm text-gray-400 font-bold').text.split(' | ')[0]
        if ',' in chart_in_artist:
            chart_in_artist = chart_in_artist.split(',')[0]
        chart_dict[chart_in_song] = chart_in_artist

    driver.quit()

    # 스포티파이 검색용 검색어 추가 (제목 가수)
    for title, artist in chart_dict.items():
        chart_list.append(f'{title} {artist}')

    # 스포티파이 검색
    track_ids = []
    for track in chart_list:
        results = sp.search(track, type='track', market='KR')
        track_id = results['tracks']['items'][0]['id']
        track_ids.append(track_id)

    # 트랙 특성 추출 (최종, max : 100ids 반영)
    track_feature_dict = {}
    track_names_list = list(chart_dict.keys())

    chunk_size = 100
    track_id_chunks = get_chunks(track_ids, chunk_size)
    track_name_chunks = get_chunks(track_names_list, chunk_size)

    rank = 1
    for i, chunk in enumerate(track_id_chunks):
        track_features = sp.audio_features(chunk)
        track_names = track_name_chunks[i]
        for i, track_name in enumerate(track_names):
            features = ['acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms']
            filtered_features = {feature: track_features[i][feature] for feature in features}
            filtered_features['rank'] = rank
            track_feature_dict[track_name] = filtered_features
            rank += 1
    
    # DataFrame 생성
    data = pd.DataFrame(track_feature_dict).T.reset_index()
    title_data = pd.DataFrame(list(chart_dict.items()), columns=['song', 'artist'])

    data.columns = ['song', 'acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms', 'rank']
    combinations = list(itertools.combinations(['acousticness', 'danceability', 'energy', 'valence'], 2))
    return chart_list, chart_dict, track_ids, track_feature_dict, data, title_data, combinations

# 원하는 트랙 데이터
def new_track_data(track_id):
    new_track_id = str(track_id)
    new_track_feature_dict = {}
    new_track_features = sp.audio_features(new_track_id)[0]
    new_track_name = sp.track(new_track_id)['name']

    features = ['acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms']
    new_filtered_features = {feature: new_track_features[feature] for feature in features}
    new_track_feature_dict[new_track_name] = new_filtered_features

    new_data = pd.DataFrame(new_track_feature_dict).T.reset_index()
    new_data.columns = ['song', 'acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms']
    return new_data

def circle_chart():
    st.title("Circle Chart Data Visualization")

    if 'input_year' not in st.session_state:
        st.session_state['input_year'] = 2024
    if 'input_month' not in st.session_state:
        st.session_state['input_month'] = 1
    if 'input_track_id' not in st.session_state:
        st.session_state['input_track_id'] = ''

    year = st.number_input("Enter Year", min_value=2010, max_value=2024, value=st.session_state['input_year'])
    mon = st.number_input("Enter Month", min_value=1, max_value=12, value=st.session_state['input_month'])
    track_id = st.text_input("Enter Track ID", value=st.session_state['input_track_id'])

    st.session_state['input_year'] = year
    st.session_state['input_month'] = mon
    st.session_state['input_track_id'] = track_id

    if st.button("Show Chart"):
        with st.spinner("Waiting..."):
            if f'is_get_circle_chart_{year}_{mon}' not in st.session_state:
                chart_list, chart_dict, track_ids, track_feature_dict, data, title_data, combinations = circle_chart_crawling(year, mon)
                st.session_state[f'chart_list_{year}_{mon}'] = chart_list
                st.session_state[f'chart_dict_{year}_{mon}'] = chart_dict
                st.session_state[f'track_ids_{year}_{mon}'] = track_ids
                st.session_state[f'track_feature_dict_{year}_{mon}'] = track_feature_dict
                st.session_state[f'data_{year}_{mon}'] = data
                st.session_state[f'title_data_{year}_{mon}'] = title_data
                st.session_state[f'combinations_{year}_{mon}'] = combinations
                st.session_state[f'is_get_circle_chart_{year}_{mon}'] = True
            if f'is_get_circle_chart_{year}_{mon}' in st.session_state:
                chart_list = st.session_state[f'chart_list_{year}_{mon}']
                chart_dict = st.session_state[f'chart_dict_{year}_{mon}']
                track_ids = st.session_state[f'track_ids_{year}_{mon}']
                track_feature_dict = st.session_state[f'track_feature_dict_{year}_{mon}']
                data = st.session_state[f'data_{year}_{mon}']
                title_data = st.session_state[f'title_data_{year}_{mon}']
                combinations = st.session_state[f'combinations_{year}_{mon}']

            new_data = new_track_data(track_id)

            if data is not None:
                st.header("Visualization", divider="gray")

                fig = go.Figure()
                fig = make_subplots(rows=2, cols=3, subplot_titles=[f'{x} vs {y}' for x, y in combinations])

                for i, (x_feature, y_feature) in enumerate(combinations):
                    row = i // 3 + 1
                    col = i % 3 + 1
                    
                    fig.add_trace(go.Scatter(
                        x=data[x_feature],
                        y=data[y_feature],
                        mode='markers',
                        name='data',
                        marker=dict(size=5),
                        text=[f"{int(rank)}위. {artist} - {song}" for rank, artist, song in zip(data['rank'], title_data['artist'], title_data['song'])],
                        hoverinfo='text',
                    ), row=row, col=col)
                    
                    fig.add_trace(go.Scatter(
                        x=new_data[x_feature],
                        y=new_data[y_feature],
                        mode='markers',
                        name='NEW',
                        marker=dict(color='black', size=12),
                        text=new_data['song'],
                        hoverinfo='text'
                    ), row=row, col=col)

                    fig.update_xaxes(title_text=x_feature, title_font=dict(size=12), row=row, col=col)
                    fig.update_yaxes(title_text=y_feature, title_font=dict(size=12), row=row, col=col)

                for annotation in fig['layout']['annotations']:
                    annotation['font'] = dict(size=12)

                fig.update_layout(height=810, width=1080, title_text=f"Feature Comparisons ({year}-{mon})", showlegend=False)
                st.session_state['circle_chart_fig'] = fig

                st.session_state['mean_loudness_circle'] = round(np.mean(data['loudness']), 2)
                st.session_state['song_loudness_circle'] = round(np.mean(new_data['loudness']), 2)
                st.session_state['mean_duration_circle'] = round(np.mean(data['duration_ms'])/1000, 2)
                st.session_state['song_duration_circle'] = round(np.mean(new_data['duration_ms'])/1000, 2)

                st.subheader(f"Mean Of Loudness: {st.session_state['mean_loudness_circle']} dB")
                st.markdown(f"Your Song's Loudness: {st.session_state['song_loudness_circle']} dB")
                st.subheader(f"Mean Of Duration: {st.session_state['mean_duration_circle']} seconds")
                st.markdown(f"Your Song's Duration: {st.session_state['song_duration_circle']} seconds")
                st.plotly_chart(go.Figure(fig))
                st.page_link(f"https://circlechart.kr/page_chart/onoff.circle?nationGbn=T&serviceGbn=S1040&targetTime={mon}&hitYear={year}&termGbn=month&yearTime=3", label="Circle Chart (Monthly)")
                st.page_link(f"https://open.spotify.com/track/{track_id}", label="Your Song Info (Spotify)")
    
    elif 'circle_chart_fig' in st.session_state:
        st.header("Visualization", divider="gray")
        st.subheader(f"Mean Of Loudness: {st.session_state['mean_loudness_circle']} dB")
        st.markdown(f"Your Song's Loudness: {st.session_state['song_loudness_circle']} dB")
        st.subheader(f"Mean Of Duration: {st.session_state['mean_duration_circle']} seconds")
        st.markdown(f"Your Song's Duration: {st.session_state['song_duration_circle']} seconds")
        st.plotly_chart(st.session_state['circle_chart_fig'])
        st.page_link(f"https://circlechart.kr/page_chart/onoff.circle?nationGbn=T&serviceGbn=S1040&targetTime={mon}&hitYear={year}&termGbn=month&yearTime=3", label="Circle Chart (Monthly)")
        st.page_link(f"https://open.spotify.com/track/{track_id}", label="Your Song Info (Spotify)")

# 빌보드 URL용 날짜 변환
def date_converting(date):
    current_weekday = date.weekday()
    days_to_sat = 5 - current_weekday
    sat_date = date + timedelta(days=days_to_sat)
    return sat_date.strftime("%Y-%m-%d")

# Request 로 Billboard Chart 크롤링
def billboard_chart_crawling(date):
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'}
    URL=f'https://www.billboard.com/charts/hot-100/{date}/'
    html = requests.get(URL, headers = header).text
    soup = BeautifulSoup(html, 'html.parser')

    title_soup = soup.find_all("h3", {"class": "a-no-trucate"})
    artist_soup = soup.find_all("span", {"class": "a-no-trucate"})

    ranks = []
    titles = []
    artists = []

    for i in range(0, 100):
        ranks.append(str(i+1))
    for t in title_soup:
        titles.append(t.text.strip())
    for a in artist_soup:
        artists.append(a.text.strip())

    # 스포티파이 검색용 검색어 추가 (제목 가수)
    chart_list = []
    chart_dict = {}
    for title, artist in zip(titles, artists):
        chart_list.append(f'{title} {artist}')
        chart_dict[title] = artist

    # 스포티파이 검색
    track_ids = []
    for track in chart_list:
        results = sp.search(track, type='track', market='KR')
        track_id = results['tracks']['items'][0]['id']
        track_ids.append(track_id)

    track_feature_dict = {}
    track_names_list = list(chart_dict.keys())

    chunk_size = 100
    track_id_chunks = get_chunks(track_ids, chunk_size)
    track_name_chunks = get_chunks(track_names_list, chunk_size)

    rank = 1
    for i, chunk in enumerate(track_id_chunks):
        track_features = sp.audio_features(chunk)
        track_names = track_name_chunks[i]
        for i, track_name in enumerate(track_names):
            features = ['acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms']
            filtered_features = {feature: track_features[i][feature] for feature in features}
            filtered_features['rank'] = rank
            track_feature_dict[track_name] = filtered_features
            rank += 1

    # DataFrame 생성
    data = pd.DataFrame(track_feature_dict).T.reset_index()
    title_data = pd.DataFrame(list(chart_dict.items()), columns=['song', 'artist'])

    #data.columns = ['song', 'acousticness', 'danceability', 'energy', 'valence', 'loudness', 'duration_ms', 'rank']
    combinations = list(itertools.combinations(['acousticness', 'danceability', 'energy', 'valence'], 2))
    
    return chart_list, chart_dict, track_ids, track_feature_dict, data, title_data, combinations
        
def billboard_chart():
    st.title("Billboard Chart Data Visualization")

    if 'input_date' not in st.session_state:
        st.session_state['input_date'] = datetime.now().date()
    if 'input_track_id_for_billboard' not in st.session_state:
        st.session_state['input_track_id_for_billboard'] = ''

    date = st.date_input("Enter Date", value=st.session_state['input_date'])
    track_id = st.text_input("Enter Track ID", value=st.session_state['input_track_id_for_billboard'])
    sat_date_conv = date_converting(date)

    st.session_state['input_date'] = date
    st.session_state['input_track_id_for_billboard'] = track_id

    if st.button("Show Chart"):
        with st.spinner("Waiting..."):
            if f'is_get_billboard_chart_{sat_date_conv}' not in st.session_state:
                chart_list, chart_dict, track_ids, track_feature_dict, data, title_data, combinations = billboard_chart_crawling(sat_date_conv)
                st.session_state[f'chart_list_{sat_date_conv}'] = chart_list
                st.session_state[f'chart_dict_{sat_date_conv}'] = chart_dict
                st.session_state[f'track_ids_{sat_date_conv}'] = track_ids
                st.session_state[f'track_feature_dict_{sat_date_conv}'] = track_feature_dict
                st.session_state[f'data_{sat_date_conv}'] = data
                st.session_state[f'title_data_{sat_date_conv}'] = title_data
                st.session_state[f'combinations_{sat_date_conv}'] = combinations
                st.session_state[f'is_get_billboard_chart_{sat_date_conv}'] = True
            if f'is_get_billboard_chart_{sat_date_conv}' in st.session_state:
                chart_list = st.session_state[f'chart_list_{sat_date_conv}']
                chart_dict = st.session_state[f'chart_dict_{sat_date_conv}']
                track_ids = st.session_state[f'track_ids_{sat_date_conv}']
                track_feature_dict = st.session_state[f'track_feature_dict_{sat_date_conv}']
                data = st.session_state[f'data_{sat_date_conv}']
                title_data = st.session_state[f'title_data_{sat_date_conv}']
                combinations = st.session_state[f'combinations_{sat_date_conv}']

            new_data = new_track_data(track_id)

            if data is not None:
                st.header("Visualization", divider="gray")

                fig = go.Figure()
                fig = make_subplots(rows=2, cols=3, subplot_titles=[f'{x} vs {y}' for x, y in combinations])

                for i, (x_feature, y_feature) in enumerate(combinations):
                    row = i // 3 + 1
                    col = i % 3 + 1
                    
                    fig.add_trace(go.Scatter(
                        x=data[x_feature],
                        y=data[y_feature],
                        mode='markers',
                        name='data',
                        marker=dict(size=5),
                        text=[f"{int(rank)}위. {artist} - {song}" for rank, artist, song in zip(data['rank'], title_data['artist'], title_data['song'])],
                        hoverinfo='text',
                    ), row=row, col=col)
                    
                    fig.add_trace(go.Scatter(
                        x=new_data[x_feature],
                        y=new_data[y_feature],
                        mode='markers',
                        name='NEW',
                        marker=dict(color='black', size=12),
                        text=new_data['song'],
                        hoverinfo='text'
                    ), row=row, col=col)

                    fig.update_xaxes(title_text=x_feature, title_font=dict(size=12), row=row, col=col)
                    fig.update_yaxes(title_text=y_feature, title_font=dict(size=12), row=row, col=col)

                for annotation in fig['layout']['annotations']:
                    annotation['font'] = dict(size=12)

                fig.update_layout(height=810, width=1080, title_text=f"Feature Comparisons ({sat_date_conv})", showlegend=False)
                st.session_state['billboard_chart_fig'] = fig

                st.session_state['mean_loudness_billboard'] = round(np.mean(data['loudness']), 2)
                st.session_state['song_loudness_billboard'] = round(np.mean(new_data['loudness']), 2)
                st.session_state['mean_duration_billboard'] = round(np.mean(data['duration_ms'])/1000, 2)
                st.session_state['song_duration_billboard'] = round(np.mean(new_data['duration_ms'])/1000, 2)

                st.subheader(f"Mean Of Loudness: {st.session_state['mean_loudness_billboard']} dB")
                st.markdown(f"Your Song's Loudness: {st.session_state['song_loudness_billboard']} dB")
                st.subheader(f"Mean Of Duration: {st.session_state['mean_duration_billboard']} seconds")
                st.markdown(f"Your Song's Duration: {st.session_state['song_duration_billboard']} seconds")
                st.plotly_chart(go.Figure(fig))
                st.page_link(f"https://www.billboard.com/charts/hot-100/{sat_date_conv}/", label="Billboard Chart (Weekly)")
                st.page_link(f"https://open.spotify.com/track/{track_id}", label="Your Song Info (Spotify)")

    elif 'billboard_chart_fig' in st.session_state:
        st.header("Visualization", divider="gray")
        st.subheader(f"Mean Of Loudness: {st.session_state['mean_loudness_billboard']} dB")
        st.markdown(f"Your Song's Loudness: {st.session_state['song_loudness_billboard']} dB")
        st.subheader(f"Mean Of Duration: {st.session_state['mean_duration_billboard']} seconds")
        st.markdown(f"Your Song's Duration: {st.session_state['song_duration_billboard']} seconds")
        st.plotly_chart(st.session_state['billboard_chart_fig'])
        st.page_link(f"https://www.billboard.com/charts/hot-100/{sat_date_conv}/", label="Billboard Chart (Weekly)")
        st.page_link(f"https://open.spotify.com/track/{track_id}", label="Your Song Info (Spotify)")

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = '🎶 Circle Chart'

button1 = st.sidebar.button('🎶 Circle Chart')
button2 = st.sidebar.button('🌎 Billboard Chart')

if button1:
    st.session_state['current_page'] = '🎶 Circle Chart'
    st.rerun()
if button2:
    st.session_state['current_page'] = '🌎 Billboard Chart'
    st.rerun()
    
if st.session_state['current_page'] == '🎶 Circle Chart':
    circle_chart()
elif st.session_state['current_page'] == '🌎 Billboard Chart':
    billboard_chart()
