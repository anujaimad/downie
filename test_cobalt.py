import requests
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
}
json_data = {
    'url': 'https://www.youtube.com/watch?v=hM8Su6CJ-C0',
}
response = requests.post('https://api.cobalt.tools/api/json', headers=headers, json=json_data)
print(response.json())
