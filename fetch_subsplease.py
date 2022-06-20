from bs4 import BeautifulSoup
from PIL import Image
import requests
from io import BytesIO
import json

SCRAPED_SITE = 'https://subsplease.org'
MEDIA_FOLDER = 'media/'
SHOWS_FOLDER = '/shows/'
JSON_URL = 'https://subsplease.org/api/?f=schedule&tz=Europe/Moscow'

def get_image(url, save_filename):
    rimg = requests.get(SCRAPED_SITE + url)
    img = Image.open(BytesIO(rimg.content))
    img.save(MEDIA_FOLDER+save_filename+'.jpg')
    return save_filename+'.jpg'

def get_full_url(page):
    return SCRAPED_SITE + SHOWS_FOLDER + page

def get_synopsis(page):
    syn = ''
    r = requests.get(get_full_url(page))
    soup = BeautifulSoup(r.text, "html.parser")
    syn_list = soup.body.find_all('div', class_="series-syn")[0].find_all('p')

    for p in syn_list:
        syn += p.get_text() + '\n'

    return syn.strip()

animes = json.loads(requests.get(JSON_URL).text)

anime_dictionary = {}

days_list = ['Monday', 'Tuesday', 'Wednesday',
             'Thursday', 'Friday', 'Saturday', 'Sunday']

for day in days_list:
    anime_day = animes['schedule'][day]
    anime_dictionary[day] = []
    for i in range(len(anime_day)):
        show = anime_day[i]
        anime_dictionary[day].append({
            'title': show['title'],
            'time': show['time'],
            'synopsis': get_synopsis(show['page']),
            'image': get_image(show['image_url'], show['page']),
            'url' : get_full_url(show['page'])})


with open('anime.json', 'w', encoding='utf-8') as f:
    json.dump(anime_dictionary, f, ensure_ascii=False, indent=4)