import torch
import torch.nn as nn
import torch.nn.functional as F

import timm

from base.base_model import BaseModel



class MnistModel(BaseModel):
    def __init__(self, num_classes=10):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
        self.conv2_drop = nn.Dropout2d()
        self.fc1 = nn.Linear(320, 50)
        self.fc2 = nn.Linear(50, num_classes)

    def forward(self, x):
        x = F.relu(F.max_pool2d(self.conv1(x), 2))
        x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)), 2))
        x = x.view(-1, 320)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


class EfficientNetB0MultiHead(BaseModel):
    def __init__(self, num_classes):
        super().__init__()
        self.model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=0)  # num_features : 1280
        for param in self.model.parameters():
            param.requires_grad = False

        self.mask = nn.Sequential(
            nn.Linear(1280, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )

        self.age = nn.Sequential(
            nn.Linear(1280, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )
        
        self.gender = nn.Sequential(
            nn.Linear(1280, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )

    def forward(self, x):
        x = self.model(x)
        mask = self.mask(x)
        gender = self.gender(x)
        age = self.age(x)
        return mask, gender, age


class FocalNetTinySRFMultiHead(BaseModel):
    def __init__(self, num_classes):
        super().__init__()
        self.model = timm.create_model("focalnet_tiny_srf", pretrained=True, num_classes=0)  # num_features = 768
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        self.model.head.fc = nn.Linear(768, 1000)  # 모델의 classifier(출력단)
        self.gelu = nn.GELU()
        self.mask = nn.Linear(1000, 3)
        self.age = nn.Linear(1000, 3)
        self.gender = nn.Linear(1000, 2)
    
    def forward(self, x):
        x = self.model(x)
        mask = self.mask(self.gelu(x))
        gender = self.gender(self.gelu(x))
        age = self.age(self.gelu(x))
        return mask, gender, age


class EfficientViTB3MultiHead(BaseModel):
    def __init__(self, num_classes):
        super().__init__()
        self.model = timm.create_model("efficientvit_b3", pretrained=True, num_classes=0)  # num_features = 512
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        self.model.head = nn.Sequential(
            nn.Dropout(p=0.0),
            nn.Conv2d(512, 2304, kernel_size=(1, 1), stride=(1, 1), bias=False),
            nn.BatchNorm2d(2304),
            nn.Hardswish(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            
            nn.Linear(2304, 2560, bias=False),
            nn.LayerNorm((2560,)),
            nn.Hardswish(),
            nn.Dropout(p=0.0),
            nn.Linear(2560, 1000, bias=False),
            nn.LayerNorm((1000,))
        )
        self.hardswish = nn.Hardswish()
        self.mask = nn.Linear(1000, 3)
        self.age = nn.Linear(1000, 3)
        self.gender = nn.Linear(1000, 2)
    
    def forward(self, x):
        x = self.model(x)
        mask = self.mask(self.hardswish(x))
        gender = self.gender(self.hardswish(x))
        age = self.age(self.hardswish(x))
        return mask, gender, age



class SwinTransformerBase224V1(BaseModel):
    def __init__(self, num_classes):
        super().__init__()
        self.model = timm.create_model("swin_base_patch4_window7_224", pretrained=True, num_classes=0)  # num_features = 1024
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        self.mask = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )
        self.gender = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )
        self.age = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )
        
    
    def forward(self, x):
        x = self.model(x)
        mask = self.mask(x)
        gender = self.gender(x)
        age = self.age(x)
        return mask, gender, age


class SwinTransformerBase224V2(BaseModel):
    def __init__(self, num_classes):
        super().__init__()
        self.model = timm.create_model("swin_base_patch4_window7_224", pretrained=True, num_classes=0)  # num_features = 1024
        
        for param in self.model.parameters():
            param.requires_grad = False
        
        self.mask = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(128, 3)
        )
        self.gender = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(128, 2)
        )
        self.age = nn.Sequential(
            nn.Linear(1024, 512, bias=False),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(512, 128, bias=False),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(),
            nn.Linear(128, 3)
        )
        
    
    def forward(self, x):
        x = self.model(x)
        mask = self.mask(x)
        gender = self.gender(x)
        age = self.age(x)
        return mask, gender, age
    

# Custom Model Template
class MyModel(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        """
        1. 위와 같이 생성자의 parameter 에 num_claases 를 포함해주세요.
        2. 나만의 모델 아키텍쳐를 디자인 해봅니다.
        3. 모델의 output_dimension 은 num_classes 로 설정해주세요.
        """

    def forward(self, x):
        """
        1. 위에서 정의한 모델 아키텍쳐를 forward propagation 을 진행해주세요
        2. 결과로 나온 output 을 return 해주세요
        """
        return x
