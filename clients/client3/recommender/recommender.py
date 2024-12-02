# recommender/recommender.py
import pandas as pd
import numpy as np
import torch

from .nlpcontextmaker import NlpContextMaker

class Recommender():
    def __init__(self, client_id, dataframes):
        self.__client_id = int(client_id)
        self.__dataframes = dataframes
        self.__contextmaker = NlpContextMaker()
        
        np.random.seed(self.__client_id)
                
    def __get_prediction(self, user_id, model):
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

    def __get_similarity_score(self, input_tag):
        self.__predictions['tag_similarity'] = self.__predictions['tags'].apply(lambda tags: self.__contextmaker.calculate_tag_similarity(input_tag, tags))

        
    def get_top_recommendations(self, user_id, input_tag, model, N=10):
        # we generate the like predicitons
        self.__get_prediction(user_id, model)
        if isinstance(self.__predictions, str):
            return self.__predictions
        
        #we generate the tag similairty
        self.__get_similarity_score(input_tag)
        
        # Drop rows where 'like_prob' is below 0.5
        self.__predictions = self.__predictions[self.__predictions['like_prob'] >= 0.5]
        
        # Sort by tag similarity and then by like probability
        top_recommendations = self.__predictions.sort_values(by=['tag_similarity', 'like_prob'], ascending=[False, False]).head(N)

        if top_recommendations.empty:
            return f"No video found on {input_tag} for user {user_id}"
        
        if top_recommendations.iloc[0]['tag_similarity'] < 0.5:
            return "Input tag does not match"
        
        return top_recommendations