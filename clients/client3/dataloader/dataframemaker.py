# dataloader/dataframemaker.py
import pandas as pd
import numpy as np
import ast

from sklearn.preprocessing import LabelEncoder

class DFMaker():
    def __init__(self, client_id: str):
        self.__client_id = int(client_id)
        self.__data = None
        self.__X = None
        self.__y_like = None
        np.random.seed(self.__client_id)

    def load_data(self, interaction_path: str, user_path: str, video_path: str, bigfive_path: str, tagmap_path: str) -> None:
        # basic dataframes
        self.__interactions = pd.read_csv(interaction_path, sep = '\t')
        self.__users = pd.read_csv(user_path, sep = '\t')
        self.__videos = pd.read_csv(video_path, sep = '\t')
        self.__bigfive = pd.read_csv(bigfive_path, sep = '\t')
        self.tag_map = pd.read_csv(tagmap_path, sep = '\t')

        # merged dataframe
        self.__data = self.__interactions.merge(self.__users, on = 'user_id').merge(self.__videos, on = 'video_id').merge(self.__bigfive, on = 'user_id')

    def process_train_data(self) -> tuple[np.ndarray, np.ndarray]:
        # define input features
        self.__define_input_features()
        # Encode Categorical cols
        self.__encode_cols(self.__categorical_cols)
        # generate tag embeddings
        self.__generate_embeddings()
        # convert tag cols to embeddings
        self.__convert_tag_to_embed(self.__data, self.__tag_cols)
        
        # prepare X, y
        X_features = self.__data[self.__feature_cols].values
        X_embeddings = np.array(self.__data[self.__embedding_cols].values.tolist())

        self.__X = np.concatenate([X_features, X_embeddings.reshape(X_embeddings.shape[0], -1)], axis=1)
        self.__y_like = self.__data['like'].values
        return self.__X, self.__y_like
        
    def process_eval_data(self, user_id: str) -> tuple[np.ndarray, pd.DataFrame] | tuple[None, None]:
        # define input features
        self.__define_input_features()
        # Encode Categorical cols
        self.__encode_cols(self.__categorical_cols)
        # generate tag embeddings
        self.__generate_embeddings()
        # convert tag cols to embeddings
        self.__convert_tag_to_embed(self.__data, self.__tag_cols)
        
        #define user data for the specific user_id
        user_data = self.__data[self.__data['user_id'] == user_id]
        if len(user_data) == 0:
            return None, None #indicating user has not been found
        
        #define videos data
        videos = self.__videos
        #extract video features for all videos
        all_videos = videos[self.__video_feature_cols]
        # convert tags column to embeddings
        self.__convert_tag_to_embed(all_videos, ['tags'])
        
        #extract one row of user's data
        user_features = user_data[self.__user_feature_cols].iloc[0]
        
        # add that same row to every row of all_videos
        user_features_df = pd.DataFrame([user_features] * len(all_videos))
        all_videos = pd.concat([user_features_df.reset_index(drop=True), all_videos.reset_index(drop=True)], axis=1)
        # as of now we have a df with all rows containing user's data, the specific video's data, and is missing 4 columns: rating and the 3 interaction_embeddings columns
        
        # IMPORTANT: we need to map user_id's interactions with all videos
        
        # case 2: videos for which our user_id has not interacted, but there are other interactions for that user in the dataset
        # for this first we extract all such videos' interactions from 'data', but only the 4 columns that we need
        other_videos = set(self.__data['video_id']) - set(user_data['video_id'])
        other_videos_df = self.__data[self.__data['video_id'].isin(other_videos)][['video_id', 'rating'] + self.__interaction_embeddings]
        
        # Case 3: videos who have not been interacted with
        # first we extract all video ids not in interactions, but in dataset
        missing_videos = set(all_videos['video_id']) - set(self.__data['video_id'])
        
        # 2.1 we will first resolve ratings
        # now we will calculate mean ratings for each unique video in other_videos and put it in a pandas series indexed by video_id
        mean_ratings = other_videos_df.groupby('video_id')['rating'].mean()
        
        # 3.1, we resolve rating of 2.0 for all these video ids, another pandas series indexed by video_id
        missing_ratings = pd.Series({video_id: 2.0 for video_id in missing_videos})
        
        # now we update missing_ratings and create one series containing both mean and missing into one series
        missing_ratings = pd.concat([mean_ratings, missing_ratings])
        # now just map this to our all_videos dataset
        all_videos['rating'] = all_videos['video_id'].map(missing_ratings)
        # all_videos dataset is now updated with average rating for videos in case 2 and a value of 2.0 for videos in case 3
        
        #next step is to update the 3 embedding columns using same logic for case 2 and 3
        
        # we create a dictionary of {column_name: corresponding mean_embedding series/missing embedding series} and use that to update the specific row just like we did for rating
        embedding_dict = {}
        for i in self.__interaction_embeddings:
            # 2.2 finding mean 32 bit embedding for videos in case 2 for the specific column in current iteration, create a pandas series out of it indexed by video_id
            mean_embeddings = other_videos_df.groupby('video_id')[i].apply(lambda x: np.mean(np.vstack(x), axis=0))
            # 3.2 for the videos in case 3, copy the value of 32 bit embedding in tags column to this column in current iteration, create a pandas series out of it indexed by video_id
            missing_embeddings = pd.Series({video_id: all_videos.loc[all_videos['video_id'] == video_id, 'tags_embedding'].values[0] for video_id in missing_videos})
            # concatenate both the series to create a single series of missing data
            embedding_dict[i] = pd.concat([mean_embeddings, missing_embeddings])
            # map the above created series to all_videos dataset
            all_videos[i] = all_videos['video_id'].map(embedding_dict[i])
        # all_videos dataset is now updated with mean embeddings values for interaction_embeddings columns for case 2 and a copy of tag_embedding column for all 3 interaction_embeddings columns for case 3
        
        # next step is to update the values of these 4 columns for videos user_id has interacted with
        
        # case 1: videos for which interactions exist with user_id
        # for this we simply merge the user_data df with all videos df
        all_videos = all_videos.merge(user_data[['video_id', 'rating'] + self.__interaction_embeddings], on='video_id', how='left', suffixes=('', '_new'))
        # Overwrite the NaN values in the original interaction columns
        for i in (['rating'] + self.__interaction_embeddings):
            all_videos[i] = all_videos[f'{i}_new'].combine_first(all_videos[i])
            # drop the new columns created by merge function
            all_videos.drop(columns=[f'{i}_new'], inplace=True)
        # now we have a df with user data, the specific video's data, and the interaction data
        
        # now we convert this exactly into what is to be fed into the model
        X_features = all_videos[self.__feature_cols].values
        X_embeddings = np.array(all_videos[self.__embedding_cols].values.tolist())
        
        X = np.concatenate([X_features, X_embeddings.reshape(X_embeddings.shape[0], -1)], axis=1)
        
        return X, all_videos
        
    def __define_input_features(self) -> None:
        bigfive_cols = [f'Q{i}' for i in range(1, 16)]
        # used by train data
        self.__categorical_cols = []
        self.__feature_cols = ['age', 'gender', 'education', 'career', 'income', 'address', 'duration', 'category', 'rating'] + bigfive_cols
        self.__tag_cols = ['reason_tag', 'video_tag', 'interest_tag','tags']
        self.__embedding_cols = ['reason_tag_embedding', 'video_tag_embedding', 'interest_tag_embedding', 'tags_embedding']
        
        #used by eval data
        self.__user_feature_cols = ['user_id', 'age', 'gender', 'education', 'career', 'income', 'address'] + bigfive_cols
        self.__video_feature_cols = ['video_id', 'title', 'duration', 'category', 'tags']
        self.__interaction_embeddings = ['reason_tag_embedding', 'video_tag_embedding', 'interest_tag_embedding']
    
    def __encode_cols(self, cols: list) -> None:
        for col in cols:
            le = LabelEncoder()
            self.__data[col] = le.fit_transform(self.__data[col])
            
    def __generate_embeddings(self) -> None:
        self.__tag_embeddings = {}
        for _, row in self.tag_map.iterrows():
            self.__tag_embeddings[row['tag_id']] = np.random.randn(32) 
            
    def __convert_tag_to_embed(self, df: pd.DataFrame, cols: list) -> None:
        # Function to get tag embeddingstag_list
        def get_tag_embeddings(tag_list: list) -> np.ndarray:
            return np.mean([self.__tag_embeddings.get(tag, np.zeros(32)) for tag in tag_list], axis=0)

        # Create tag embeddings for each column
        for col in cols:
            df[f'{col}_embedding'] = df[col].apply(lambda x: get_tag_embeddings(ast.literal_eval(x)))
            df[col] = df[col].apply(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)