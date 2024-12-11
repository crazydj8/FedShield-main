# recommender/recommender.py
import pandas as pd
import numpy as np
import torch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.models import VideoRecommendationModel
from dataloader import DFMaker
from .nlpcontextmaker import NlpContextMaker

class Recommender():
    def __init__(self, client_id: str, dataframes: DFMaker):
        self.__client_id = int(client_id)
        self.__dataframes = dataframes
        self.__contextmaker = NlpContextMaker()
        
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

    def __get_similarity_score(self, input_tag: str) -> None:
        self.__predictions['tag_similarity'] = self.__predictions['tags'].apply(lambda tags: self.__contextmaker.calculate_tag_similarity(input_tag, tags))

        
    def get_top_recommendations(self, user_id: int, input_tag: str, model: VideoRecommendationModel, N: int = 10) -> tuple[bool, pd.DataFrame, pd.DataFrame]:
        # we generate the like predicitons
        self.__get_prediction(user_id, model)
        if isinstance(self.__predictions, str):
            return self.__predictions
        
        #we generate the tag similairty
        self.__get_similarity_score(input_tag)
        
        # create two DFs: 1) tag_similarity matches, 2) no similar tags
        similar_tag_predictions = self.__predictions[self.__predictions['tag_similarity'] >= 0.5].copy()
        no_similar_tag_predictions = self.__predictions[self.__predictions['tag_similarity'] < 0.5].copy()
        
        # define a function to calculate total score
        def calculate_score(df):
            df['total_score'] = df['tag_similarity'] * 0.3 + df['like_prob'] * 0.7
        
        # generate the score based on tag similarity and like probability
        for df in (similar_tag_predictions, no_similar_tag_predictions):
            calculate_score(df)
        
        # Sort by tag similarity and then by like probability
        top_tag_recommendations = similar_tag_predictions.sort_values(by=['total_score'], ascending=[False]).head(N)
        top_no_tag_recommendations = no_similar_tag_predictions.sort_values(by=['like_prob'], ascending=[False]).head(N)
        
        
        num_recommendation = top_tag_recommendations.shape[0]
        is_less_than_10 = False
        if num_recommendation < N:
            is_less_than_10 = True
            top_no_tag_recommendations = top_no_tag_recommendations.head(N - num_recommendation)
        
        return is_less_than_10, top_tag_recommendations, top_no_tag_recommendations