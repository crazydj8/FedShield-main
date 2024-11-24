# dataloader/datastplitter.py
import numpy as np
import torch

from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset, DataLoader

# Create PyTorch dataset
class VideoDataset(Dataset):
    def __init__(self, X: np.ndarray, y_like: np.ndarray):
        self.X = torch.FloatTensor(X.astype(np.float32))
        self.y_like = torch.FloatTensor(y_like.astype(np.float32))

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int) -> tuple[torch.FloatTensor, torch.FloatTensor]:
        return self.X[idx], self.y_like[idx]

class DataSplitter():
    def __init__(self, X: np.ndarray, y: np.ndarray, mode: int):
        self.mode = mode # 0 = train split, 1 = full split
        self.test_size = 0.2
        self.__X, self.__y = X, y
        self.__X_train, self.__X_test, self.__y_train, self.__y_test  = train_test_split(self.__X, self.__y, test_size = self.test_size, random_state = 42)
        self.__train_loader = None
        self.__test_loader = None
        
    def create_data_loader(self, batch_size: int) -> tuple[DataLoader, DataLoader] | DataLoader:
        if self.mode == 0:
            train_dataset = VideoDataset(self.__X_train, self.__y_train)
            test_dataset = VideoDataset(self.__X_test, self.__y_test)
            self.__train_loader = DataLoader(train_dataset, batch_size = batch_size, shuffle = True)
            self.__test_loader = DataLoader(test_dataset, batch_size = batch_size, shuffle = False)
            return self.__train_loader, self.__test_loader
        else:
            full_dataset = VideoDataset(self.__X, self.__y)
            self.__full_loader = DataLoader(full_dataset, batch_size = batch_size, shuffle = False)
            return self.__full_loader
        
    def extract_test_data(self) -> np.ndarray:
        return self.__X_test