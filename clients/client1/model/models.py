# model/models.py
import torch
import torch.nn as nn
import torch.nn.functional as F

class VideoRecommendationModel(nn.Module):
    def __init__(self, input_dim: int):
        super(VideoRecommendationModel, self).__init__()
        self.fc1 = nn.Linear(input_dim, 512)
        self.bn1 = nn.BatchNorm1d(512)
        self.fc2 = nn.Linear(512, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.fc3 = nn.Linear(256, 128)
        self.bn3 = nn.BatchNorm1d(128)
        self.fc4 = nn.Linear(128, 64)
        self.bn4 = nn.BatchNorm1d(64)
        self.fc5 = nn.Linear(64, 32)  # New layer added
        self.bn5 = nn.BatchNorm1d(32)
        self.fc_like = nn.Linear(32, 1)  # Adjusted for the new layer
        self.dropout = nn.Dropout(0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.dropout(F.leaky_relu(self.bn1(self.fc1(x))))
        x = self.dropout(F.leaky_relu(self.bn2(self.fc2(x))))
        x = self.dropout(F.relu(self.bn3(self.fc3(x))))
        x = self.dropout(F.relu(self.bn4(self.fc4(x))))
        x = self.dropout(F.relu(self.bn5(self.fc5(x))))
        if x.shape[1] == residual.shape[1]:
            x = x + residual
        like = torch.sigmoid(self.fc_like(x))
        return like
    
#any other models can be defined here
