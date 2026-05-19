import requests
import re

url = "https://elibrary.ferc.gov/eLibraryWebAPI/api/File/DownloadP8File"

payload = {
    "FileType": "",
    "accession": "",
    "fileid": 0,
    "FileIDAll": "",
    "fileidLst": [
        "32A8715D-223D-C369-8547-9E40BE100000"
    ],
    "Islegacy": False
}

response = requests.post(url, json=payload, stream=True)

response.raise_for_status()

# Get filename from response header
content_disposition = response.headers.get("Content-Disposition", "")
match = re.search(r'filename="?([^"]+)"?', content_disposition)

filename = match.group(1) if match else "downloaded_file"

with open(filename, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Downloaded:", filename)