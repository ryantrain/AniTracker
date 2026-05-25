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

def search_anime_by_id(id: int, retries: int = 3, retry_delay: float = 1.0):
    for attempt in range(retries):
        response = requests.get(f"https://api.jikan.moe/v4/anime/{id}")
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                return data

        if response.status_code == 429 and attempt < retries - 1:
            retry_after = response.headers.get('Retry-After')
            delay = float(retry_after) if retry_after else retry_delay
            time.sleep(delay)
        elif attempt < retries - 1:
            time.sleep(retry_delay)

    return None