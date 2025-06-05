import json
with open('marvel_dataset.json', 'r') as file:
    content = json.load(file)['characters']

print(len(content))
