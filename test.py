import requests
import random
import threading
from concurrent.futures import ThreadPoolExecutor

def read_urls(file_path):
    with open(file_path, 'r') as file:
        urls = file.read().splitlines()
    return urls

def select_random_urls(urls, num_urls):
    return random.sample(urls, num_urls)

def send_post_request(email, urls):
    payload = {
        'email': email,
        'urls': urls
    }
    url = 'http://127.0.0.1:5000/scrape'
    return requests.post(url, json=payload)

def simulate_client_action(email, urls):
    num_urls = random.randint(1, 50)
    selected_urls = select_random_urls(urls, num_urls)
    response = send_post_request(email, selected_urls)

    if response.status_code == 200:
        try:
            data = response.json()
            request_id = data.get('request_id')
            if request_id:
                print(f'{request_id} -- {num_urls}')

            else:
                print('No request_id found in response')
        except ValueError:
            print('Response is not valid JSON')
    else:
        print(f'Request failed with status code {response.status_code}')


# File path to the urls.txt file
file_path = 'urls.txt'

# Read URLs from the file
urls = read_urls(file_path)

# Number of clients to simulate
num_clients = 10

# List of emails to use for each client
emails = [f'hungphong9a@gmail.com' for i in range(num_clients)]

# Create a ThreadPoolExecutor to simulate multiple clients
with ThreadPoolExecutor(max_workers=num_clients) as executor:
    futures = []
    for email in emails:
        futures.append(executor.submit(simulate_client_action, email, urls))

# Wait for all futures to complete
for future in futures:
    future.result()

print("Simulated client actions completed.")
