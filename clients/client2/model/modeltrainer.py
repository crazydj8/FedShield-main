# model/modeltrainer.py
import torch
from torch.utils.data import DataLoader

from .models import VideoRecommendationModel

class ModelTrainer():
    
    def __init__(self, model: VideoRecommendationModel, loss_func: torch.nn.Module, optimizer: torch.optim.Optimizer):
        self.__model = model
        self.__loss_func = loss_func
        self.__optimizer = optimizer

    # Training function
    def train(self, train_loader: DataLoader) -> tuple[float, float]:
        self.__model.train()
        total_loss = 0
        correct_likes = 0
        total_samples = 0
        for batch_X, batch_y_like in train_loader:
            self.__optimizer.zero_grad()
            like_pred = self.__model(batch_X)
            loss_like = self.__loss_func(like_pred.squeeze(), batch_y_like)
            loss = loss_like
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.__model.parameters(), max_norm=1.0)
            self.__optimizer.step()
            total_loss += loss.item()
            predicted_likes = (like_pred.squeeze() > 0.5).float()
            correct_likes += (predicted_likes == batch_y_like).sum().item()
            total_samples += batch_y_like.size(0)        
        accuracy = correct_likes / total_samples
        return total_loss / len(train_loader), accuracy
    
    # Evaluation function
    def evaluate(self, test_loader: DataLoader) -> tuple[float, float]:
        self.__model.eval()
        total_loss = 0
        correct_likes = 0
        total_samples = 0
        with torch.no_grad():
            for batch_X, batch_y_like in test_loader:
                like_pred = self.__model(batch_X)
                loss_like = self.__loss_func(like_pred.squeeze(), batch_y_like)
                loss = loss_like
                total_loss += loss.item()
                
                predicted_likes = (like_pred.squeeze() > 0.5).float()
                correct_likes += (predicted_likes == batch_y_like).sum().item()
                total_samples += batch_y_like.size(0)
        
        accuracy = correct_likes / total_samples
        return total_loss / len(test_loader), accuracy
