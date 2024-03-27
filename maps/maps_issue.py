import json
import random

from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('sentence-transformers/distiluse-base-multilingual-cased-v1')

data = []
with open('metadata.jsonl', 'r') as file:
    for line in file:
        data.append(json.loads(line))

sentences = []
dictionary = {}
for item in data:
    file_name = item['file_name']
    text = item['text']
    dictionary[file_name] = text[text.find(',') + 2:].split(' - ')
    sentences.append(text)


def random_biom(biom):     # возвращает ссылку на карту / сообщение о том что ничего не найдено
    point = random.randint(0, len(dictionary) - 1)
    for i in range(0, len(dictionary)):
        if point + i == len(dictionary):
            point = -i
        if dictionary[list(dictionary.keys())[point+i]][0] == biom:
            return list(dictionary.keys())[point+i]
    return 'Карт данного биома не найдено'


def similar_description(user_description):  # возвращает массив из трех ссылок на карты, по убыванию "подходящести"
    embeddings = model.encode(sentences)
    user_embedding = model.encode(user_description)
    cos_sim = util.cos_sim(embeddings, user_embedding)
    sim_arr = []
    for i in range(len(cos_sim) - 1):
        sim_arr.append([cos_sim[i], i])
    sim_arr = sorted(sim_arr, key=lambda x: x[0], reverse=True)
    ans = []
    for score, i in sim_arr[0:3]:
        ans.append("img/image_" + str(i + 1).zfill(3) + ".jpg")
