import requests

ZEPHYR_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJjb250ZXh0Ijp7ImJhc2VVcmwiOiJodHRwczovL25pZmFzYXRoZmFyaGFuYWsuYXRsYXNzaWFuLm5ldCIsInVzZXIiOnsiYWNjb3VudElkIjoiNzEyMDIwOjI0MTMzM2EzLWNlODctNDNhZi1iOTIzLWYyZjA1MTRmM2QxZCIsInRva2VuSWQiOiI2MjFhOGQ3Ny1lYjZkLTRmNjYtOTUwMC01NTkxNDE1ZjhjYjkifX0sImlzcyI6ImNvbS5rYW5vYWgudGVzdC1tYW5hZ2VyIiwic3ViIjoiMjRjYmZiMzAtNDY5My0zZjZmLWEzMTAtNTZkOWI2NDM1MTdhIiwiZXhwIjoxNzkzNTUxNzIyLCJpYXQiOjE3NjIwMTU3MjJ9.ys7WKD4S3h2jZm-XxtvSe3pkfn5aI1TpCO3yq7AgO0Y"

headers = {
    "Authorization": f"Bearer {ZEPHYR_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

url = "https://api.zephyrscale.smartbear.com/v2/projects"

r = requests.get(url, headers=headers)
print("Status:", r.status_code)
print("Response:", r.text)
