import pandas as pd
import numpy as np
import torch

from fuzzywuzzy import fuzz

from dataloader import DFMaker
from model.models import VideoRecommendationModel

class Recommender():
    def __init__(self, client_id: str, dataframes: DFMaker):
        self.__client_id = int(client_id)
        self.__dataframes = dataframes

        np.random.seed(self.__client_id)
        
    def __get_prediction(self, user_id: int, model: VideoRecommendationModel) -> None:
        X, all_videos = self.__dataframes.process_eval_data(user_id)
        if X is not None:
            # Get predictions
            X_tensor = torch.FloatTensor(X.astype(np.float32))
            
            model.eval()
            with torch.no_grad():
                like_pred = model(X_tensor)
                
            # Combine predictions with video IDs
            self.__predictions = pd.DataFrame({
                'video_id': all_videos['video_id'],
                'title': all_videos['title'],
                'tags': all_videos['tags'],
                'like_prob': like_pred.squeeze().numpy()
            })
        else:
            self.__predictions = "User not found"
        
    def get_top_recommendations(self, user_id: int, input_tag: str, model: VideoRecommendationModel, N: int = 10) -> str | pd.DataFrame:
        self.__get_prediction(user_id, model)
        if isinstance(self.__predictions, str):
            return self.__predictions

        tag_id_to_name = dict(zip(self.__dataframes.tag_map['tag_id'], self.__dataframes.tag_map['tag_content']))
        
        def calculate_tag_similarity(tags: list) -> float:
            tag_names = [tag_id_to_name.get(int(tag_id), "") for tag_id in eval(tags)]
            return max([fuzz.ratio(input_tag.lower(), tag_name.lower()) for tag_name in tag_names if tag_name])
        
        self.__predictions['tag_similarity'] = self.__predictions['tags'].apply(lambda tags: calculate_tag_similarity(tags))

        # Sort by tag similarity and then by like probability
        top_recommendations = self.__predictions.sort_values(by=['tag_similarity', 'like_prob'], ascending=[False, False]).head(N)
        
        if top_recommendations.iloc[0]['tag_similarity'] < 50:
            return "Input tag does not match"
        
        if top_recommendations.iloc[0]['like_prob'] < 0.5:
            return f"No video found on {input_tag} for user {user_id}"
        
        return top_recommendations