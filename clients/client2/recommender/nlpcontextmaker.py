# recommender/nlpcontextmaker.py
import csv
import json
import os
import ast
import torch

from sentence_transformers import SentenceTransformer, util

class NlpContextMaker():
    def __init__(self):
        self.__model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        self.__datasetpath = os.path.join(os.path.dirname(__file__), "..", "dataset")
        self.__generateEncodings()
        self.__generateSimilarity()
        self.__load_Similarity()
        self.__last_input = (None, None, 0.0) # last_input, last_match_tag_id, last_match_similarity_score

    def __generateEncodings(self) -> None:
        csv_filepath =  os.path.join(self.__datasetpath, "tag_map.csv")
        self.__tags = []
        self.__ids = []
        with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                self.__ids.append(row['tag_id'])
                self.__tags.append(row['tag_content'])
        self.__embeddings = self.__model.encode(self.__tags, convert_to_tensor=True)

    def __generateSimilarity(self) -> None:
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
    
    def __load_Similarity(self) -> None:
        similarity_filepath = os.path.join(self.__datasetpath, "tag_similarity.json" )
        with open(similarity_filepath, 'r') as f:
            self.__similarity_dict = json.load(f)

    def __convert_tag_to_id(self, input_tag: str) -> tuple[str, float]: 
        #Convert an input tag to the most similar tag ID.
        input_embedding = self.__model.encode(input_tag, convert_to_tensor=True)
        cosine_similarities = util.pytorch_cos_sim(input_embedding, self.__embeddings)
        
        # Clamp values to be within the range [0, 1]
        cosine_similarities = torch.clamp(cosine_similarities, max=1.0)
        
        max_index = cosine_similarities.argmax().item()
        print(f"Input tag matched with: {self.__tags[max_index]}, with a similarity score of {cosine_similarities[0][max_index].item()}")
        return self.__ids[max_index], cosine_similarities[0][max_index].item()

    def calculate_tag_similarity(self, input_tag: str, tags: str) -> float:
        if input_tag != self.__last_input[0]:
            # convert tag into tag_id
            input_tag_id, similarity_score = self.__convert_tag_to_id(input_tag)
            if similarity_score < 0.5:
                input_tag_id, similarity_score = None, 0.0
            self.__last_input = (input_tag, input_tag_id, similarity_score)
        else:
            _, input_tag_id, similarity_score = self.__last_input
        
        score = 0.0
        if input_tag_id:
            synonym_list = self.__similarity_dict[input_tag_id]
            video_tags = set(ast.literal_eval(tags))
            for tag in synonym_list:
                if int(tag[0]) in video_tags:
                    score = tag[1] * similarity_score
                    break
        
        return score