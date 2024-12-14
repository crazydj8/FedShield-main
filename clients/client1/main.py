import torch

from model import NNModel
from model.models import VideoRecommendationModel
from dataloader import DFMaker, DataSplitter
from requesthandler import RequestHandler
from recommender import Recommender

client_id = "1"

def load_global() -> list:
    locality = "global"
    
    requesthandler = RequestHandler(client_id)
    resp = requesthandler.retrieveModelUpdates(locality)
    # resp = []
    return resp

def generate_recommendations(user_id: int, input_tag: str, model: VideoRecommendationModel, N: int, recommender: Recommender) -> None:
    user_not_found, is_less_than_10, predictions_match, predictions_no_match = recommender.get_top_recommendations(user_id, input_tag, model, N)
    
    if user_not_found:
        print(f"User ID {user_id} not found in database, Please try again.")
        return

    print(f"Video recommendations on {input_tag} that user_id: {user_id} may like:")
    print(predictions_match)
    predictions_match.to_csv("tag_recommendations.csv")
    
    if is_less_than_10:    
        print(f"Less than {N} recommendations found")
        print(f"You may also like:")
        print(predictions_no_match)
        predictions_no_match.to_csv("no_tag_recommendations.csv")

if __name__ == "__main__":
    # initialize paths to dataset
    interaction_path = f"dataset/interaction_split_{client_id}.csv"
    user_path = f"dataset/user_split_{client_id}.csv"
    video_path = "dataset/video.csv"
    bigfive_path = f"dataset/bigfive_split_{client_id}.csv"
    tagmap_path = "dataset/tag_map.csv"
    
    data = DFMaker(client_id)
    
    data.load_data(interaction_path, user_path, video_path, bigfive_path, tagmap_path)
    
    # create dataframe
    X, y_like = data.process_train_data()
    
    # create train test split and load data onto data loader
    datasplit = DataSplitter(X, y_like, mode=1)

    batch_size = 64
    full_loader = datasplit.create_data_loader(batch_size)

    # Initialize model, loss function, and optimizer
    input_dim = X.shape[1]
    criterion_like = torch.nn.BCELoss()
    optimizer_class = torch.optim.Adam
    optimizer_params = {'lr': 0.01}
    
    model = NNModel(input_dim, criterion_like, optimizer_class, optimizer_params, client_id)
    
    global_list = load_global()
    g_state_dict = [global_list[-1] if global_list else None][0]
    if g_state_dict:
        l_update = torch.load(f"local_update_{client_id}_enc.pth")
    else:
        l_update = torch.load(f"local_update_{client_id}.pth")
    l_state_dict = l_update['state_dict']
    
    model.updateModel(l_state_dict, g_state_dict)
    
    test_loss, test_accuracy = model.evaluate(full_loader)
    print("\nFinal Model Metrics:")
    print(f"Test Loss: {test_loss:.4f}, Test Accuracy: {test_accuracy:.4f}")
    
    print("\n--RECOMMENDATIONS--\n")
    #END USER
    user_id = int(input("Enter User ID: "))
    #user_id = 30
    input_tag = input("Enter Input Tag: ")
    #input_tag = "Comedy"
    
    recommender = Recommender(client_id, data)
    
    generate_recommendations(user_id, input_tag, model.model, 10, recommender)