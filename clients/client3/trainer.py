import torch

from model import NNModel
from dataloader import DFMaker, DataSplitter
from requesthandler import RequestHandler

def set_seed(seed: int = 42) -> None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

client_id = "3"

if __name__ == "__main__":
    # set the seed
    set_seed(int(client_id))
    
    # initialize paths to dataset
    interaction_path = f"dataset/interaction_split_{client_id}.csv"
    user_path = f"dataset/user_split_{client_id}.csv"
    video_path = "dataset/video.csv"
    bigfive_path = f"dataset/bigfive_split_{client_id}.csv"
    tagmap_path = "dataset/tag_map.csv"
    
    data = DFMaker(client_id)
    
    data.load_data(interaction_path, user_path, video_path, bigfive_path, tagmap_path)
    
    # create dataframe
    
    # interactions, users, videos, bigfive, tag_map = data.interactions, data.users, data.videos, data.bigfive, data.tag_map
    X, y_like = data.process_train_data()

    # create train test split and load data onto data loader
    datasplit = DataSplitter(X, y_like, mode=0)
    batch_size = 64
    train_loader, test_loader = datasplit.create_data_loader(batch_size)
    
    # Initialize model, loss function, and optimizer
    input_dim = X.shape[1]
    criterion_like = torch.nn.BCELoss()
    optimizer_class = torch.optim.RMSprop
    optimizer_params = {'lr': 0.001, 'weight_decay':1e-4}
    
    model = NNModel(input_dim, criterion_like, optimizer_class, optimizer_params, client_id)

    # Training loop
    num_epochs = 25
    train_accuracy, test_accuracy = model.train(num_epochs, train_loader, test_loader)
    print(f"\nFinal Train Accuracy: {train_accuracy:.4f}, Final Test Accuracy: {test_accuracy:.4f}")
    
    X_test = datasplit.extract_test_data()
    payload = model.generateAndAttachProof(X_test)
    
    # Save the trained model locally (optional)
    filepath = f"local_update_{client_id}"
    model.saveLocally(filepath)
    
    # sending over to network
    reqhandler = RequestHandler(client_id)
    locality = "local"
    reqhandler.storeModelUpdates(payload, locality)