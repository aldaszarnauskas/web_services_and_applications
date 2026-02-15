import requests, json, csv, io

r = requests.get("https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/FIQ02/CSV/1.0/en")

# Use .content.decode("utf-8-sig") to strip the BOM
content = r.content.decode("utf-8-sig")
# Convert content to a file object which has .read(), readlines() and similar functions 
csv_file = io.StringIO(content)
# Convert to the dictionary object
csv_content = list(csv.DictReader(csv_file))

# Convert the dictionary object to csv
with open("data/cso.json", "w", encoding="utf-8") as cso:
    json.dump(csv_content, cso, indent=4, ensure_ascii=False)