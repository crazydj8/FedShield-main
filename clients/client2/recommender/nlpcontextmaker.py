# recommender/nlpcontextmaker.py
import csv
import json
import os
import ast

from sentence_transformers import SentenceTransformer, util

class NlpContextMaker():
    def __init__(self):
        self.__model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.__datasetpath = os.path.join(os.path.dirname(__file__), "..", "dataset")
        self.__generateEncodings()
        self.__generateSimilarity()
        self.__load_Similarity()

    def __generateEncodings(self):
        csv_filepath =  os.path.join(self.__datasetpath, "tag_map.csv")
        self.__tags = []
        self.__ids = []
        with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                self.__ids.append(row['tag_id'])
                self.__tags.append(row['tag_content'])
        self.__embeddings = self.__model.encode(self.__tags, convert_to_tensor=True)

    def __generateSimilarity(self):
        similarity_filepath = os.path.join(self.__datasetpath, "tag_similarity.json" )
        if not os.path.exists(similarity_filepath):
            print("Tag similarity file not found. Generating...")

            # generate the similarity matrix for all tags
            cosine_similarities = util.pytorch_cos_sim(self.__embeddings, self.__embeddings)

            # Creation of similarity json
            synonyms_dict = {tagid: [] for tagid in self.__ids}
            for i, tag in enumerate(self.__tags):
                for j, other_tag in enumerate(self.__tags):

                    # using cosine threshold = 0.5 (>0.5 is synonym)
                    if i != j and cosine_similarities[i][j].item() > 0.5 and cosine_similarities[i][j].item() <= 1.0:
                        synonyms_dict[self.__ids[i]].append((self.__ids[j], cosine_similarities[i][j].item()))
                        synonyms_dict[self.__ids[j]].append((self.__ids[i], cosine_similarities[i][j].item())) 

            for i, tag in enumerate(synonyms_dict):
                synonyms_dict[tag] = list(set(synonyms_dict[tag]))  # Remove duplicates
                synonyms_dict[tag].sort(key=lambda x: x[1], reverse=True)  # Sort by similarity
                synonyms_dict[tag].insert(0, (tag, 1.0))  # Insert the tag itself with a similarity of 1.0

            print(f"Saving synonyms dictionary to dataset/tag_similarity.json")
            output_filepath =  os.path.join(self.__datasetpath, "tag_similarity.json")
            with open(output_filepath, 'w') as f:
                json.dump(synonyms_dict, f)
    
    def __load_Similarity(self):
        similarity_filepath = os.path.join(self.__datasetpath, "tag_similarity.json" )
        with open(similarity_filepath, 'r') as f:
            self.__similarity_dict = json.load(f)

    def __convert_tag_to_id(self, input_tag):
        #Convert an input tag to the most similar tag ID.
        input_embedding = self.__model.encode(input_tag, convert_to_tensor=True)
        cosine_similarities = util.pytorch_cos_sim(input_embedding, self.__embeddings)
        max_index = cosine_similarities.argmax().item()
        return self.__ids[max_index]
        

    def calculate_tag_similarity(self, input_tag, tags):
        # convert tag into tag_id
        input_tag_id = self.__convert_tag_to_id(input_tag)
        synonym_list = self.__similarity_dict[input_tag_id]
        video_tags = set(ast.literal_eval(tags))
        score = 0.0
        for tag in synonym_list:
            if int(tag[0]) in video_tags:
                score = tag[1]
                break
        
        return score