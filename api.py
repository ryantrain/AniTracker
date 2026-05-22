import requests
import time

url = "https://api.jikan.moe/v4/"

def get_anime_list(count: int):
    results = []
    id = 1
    while len(results) < count:
        time.sleep(0.335)
        response = requests.get(f"{url}anime/{id}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                results.append(data)
        id += 1
    return results

def search_anime_by_title(title: str, page_number: int = 1):
    response = requests.get(f"https://api.jikan.moe/v4/anime?q={title}&page={page_number}")
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            return data
    return []  # If there is no data or if the request fails, return an empty list