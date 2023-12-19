import torch
import torch.nn as nn
import torch.nn.functional as F
from base.base_model import BaseModel
import timm
import clip # https://github.com/openai/CLIP
import copy 


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

class CLIP1Head(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
            
        for name, param in self.model.named_parameters():
            if "visual.proj" in name or "text_projection" in name:
                param.requires_grad_(True)
            else: 
                param.requires_grad_(False)
        
        captions = [
            "A photo of a young man wearing a mask that covers his nose and mouth.",
            "A photo of a middle-aged man wearing a mask that covers his nose and mouth.",
            "A photo of a elderly man wearing a mask that covers his nose and mouth.",
            "A photo of a young woman wearing a mask that covers her nose and mouth.",
            "A photo of a middle-aged woman wearing a mask that covers her nose and mouth.",
            "A photo of a elderly woman wearing a mask that covers her nose and mouth.",
            "A photo of a young man wearing a mask improperly.",
            "A photo of a middle-aged man wearing a mask improperly.",
            "A photo of a elderly man wearing a mask improperly.",
            "A photo of a young woman wearing a mask improperly.",
            "A photo of a middle-aged woman wearing a mask improperly.",
            "A photo of a elderly woman wearing a mask improperly.",
            "A photo of a young man not wearing a mask.",
            "A photo of a middle-aged man not wearing a mask.",
            "A photo of an elderly man not wearing a mask.",
            "A photo of a young woman not wearing a mask.",
            "A photo of a middle-aged woman not wearing a mask.",
            "A photo of an elderly woman not wearing a mask.",
        ]
        self.captions = clip.tokenize([text for text in captions]).to(self.device)

    def forward(self, x):
        image_features = self.model.encode_image(x) # NOTE: need to resize (224, 224)
        text_features = self.model.encode_text(self.captions)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)   
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ text_features.T)
        return similarity
    
class CLIP3Head1Proj(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
            
        for name, param in self.model.named_parameters():
            if "visual.proj" in name or "text_projection" in name:
                param.requires_grad_(True)
            else: 
                param.requires_grad_(False)
            # param.requires_grad_(False)
        
        mask_captions = [
            'A person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, with either the mouth or nose exposed.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        age_captions = [
            'a photo of a young person.',
            'a photo of a middle-aged person.',
            'A photo of a person in old age.',
        ]
        
        self.mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        self.gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        self.age_captions = clip.tokenize([text for text in age_captions]).to(self.device)

    def forward(self, x):
        image_features = self.model.encode_image(x)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)   

        mask_features = self.model.encode_text(self.mask_captions)
        mask_features = mask_features / mask_features.norm(dim=-1, keepdim=True)

        gender_features = self.model.encode_text(self.gender_captions)
        gender_features = gender_features / gender_features.norm(dim=-1, keepdim=True)

        age_features = self.model.encode_text(self.age_captions)
        age_features = age_features / age_features.norm(dim=-1, keepdim=True)

        mask_logits = (100.0 * image_features @ mask_features.T)
        gender_logits = (100.0 * image_features @ gender_features.T)
        age_logits = (100.0 * image_features @ age_features.T)
        return mask_logits, gender_logits, age_logits
    
class CLIP3Head3Proj(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
            
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)

        self.mask_i = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.gender_i = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.age_i = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.mask_t = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.gender_t = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.age_t = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        
        mask_captions = [
            'A photo of a person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        age_captions = [
            'a photo of a young person under 30.',
            'a photo of a middle-aged person aged over 30 and 60.',
            'a photo of an elderly person over 60 years old.',
        ]
        
        mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        age_captions = clip.tokenize([text for text in age_captions]).to(self.device)
        # age_captions = clip.tokenize([text for text in male_2_age_captions]).to(self.device)
        
        self.text_mask_features = self.model.encode_text(mask_captions).type(torch.float32)
        self.text_gender_features = self.model.encode_text(gender_captions).type(torch.float32)
        self.text_age_features = self.model.encode_text(age_captions).type(torch.float32)

    def forward(self, x):
        image_features = self.model.encode_image(x).type(torch.float32)
        
        image_mask_features = self.mask_i(image_features)
        image_mask_features = image_mask_features / image_mask_features.norm(dim=-1, keepdim=True)
        
        image_gender_features = self.gender_i(image_features)
        image_gender_features = image_gender_features / image_gender_features.norm(dim=-1, keepdim=True)
        
        image_age_features = self.age_i(image_features)
        image_age_features = image_age_features / image_age_features.norm(dim=-1, keepdim=True)

        text_mask_features = self.mask_t(self.text_mask_features)
        text_mask_features = text_mask_features / text_mask_features.norm(dim=-1, keepdim=True)

        text_gender_features = self.gender_t(self.text_gender_features)
        text_gender_features = text_gender_features / text_gender_features.norm(dim=-1, keepdim=True)

        text_age_features = self.age_t(self.text_age_features)
        text_age_features = text_age_features / text_age_features.norm(dim=-1, keepdim=True)

        mask_logits = (100.0 * image_mask_features @ text_mask_features.T)
        gender_logits = (100.0 * image_gender_features @ text_gender_features.T)
        age_logits = (100.0 * image_age_features @ text_age_features.T)
        
        return mask_logits, gender_logits, age_logits


class CLIP3Head3Proj_Aggregation(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
        
        # load pretrained heads
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        pretrained_model.eval()
        
        print("loading age model...", end=' ')
        model_path = "/data/ephemeral/home/output/exp32/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.age_i = copy.deepcopy(pretrained_model.age_i)
        self.age_t = copy.deepcopy(pretrained_model.age_t)
        print("done.")
                
        print("loading gender model...", end=' ')
        model_path = "/data/ephemeral/home/output/exp33/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.gender_i = copy.deepcopy(pretrained_model.gender_i)
        self.gender_t = copy.deepcopy(pretrained_model.gender_t)
        print("done.")
        
        print("loading mask model...", end=' ')
        model_path = "/data/ephemeral/home/output/exp34/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.mask_i = copy.deepcopy(pretrained_model.mask_i)
        self.mask_t = copy.deepcopy(pretrained_model.mask_t)
        print("done.")
        
        del pretrained_model    # free
            
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)
        # for name, param in self.named_parameters():
        #     if param.requires_grad:
        #         print(f'{name} will be trained.')
        
        mask_captions = [
            'A photo of a person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        age_captions = [
            'a photo of a young person under 30.',
            'a photo of a middle-aged person aged over 30 and 60.',
            'a photo of an elderly person over 60 years old.',
        ]
        
        mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        age_captions = clip.tokenize([text for text in age_captions]).to(self.device)
        
        self.text_mask_features = self.model.encode_text(mask_captions).type(torch.float32)
        self.text_gender_features = self.model.encode_text(gender_captions).type(torch.float32)
        self.text_age_features = self.model.encode_text(age_captions).type(torch.float32)
        

    def forward(self, x):
        image_features = self.model.encode_image(x).type(torch.float32)
        
        image_mask_features = self.mask_i(image_features)
        image_mask_features = image_mask_features / image_mask_features.norm(dim=-1, keepdim=True)
        
        image_gender_features = self.gender_i(image_features)
        image_gender_features = image_gender_features / image_gender_features.norm(dim=-1, keepdim=True)
        
        image_age_features = self.age_i(image_features)
        image_age_features = image_age_features / image_age_features.norm(dim=-1, keepdim=True)

        # text_mask_features = self.model.encode_text(self.mask_captions).type(torch.float32)
        text_mask_features = self.mask_t(self.text_mask_features)
        text_mask_features = text_mask_features / text_mask_features.norm(dim=-1, keepdim=True)

        # text_gender_features = self.model.encode_text(self.gender_captions).type(torch.float32)
        text_gender_features = self.gender_t(self.text_gender_features)
        text_gender_features = text_gender_features / text_gender_features.norm(dim=-1, keepdim=True)

        # text_age_features = self.model.encode_text(self.age_captions).type(torch.float32)
        text_age_features = self.age_t(self.text_age_features)
        text_age_features = text_age_features / text_age_features.norm(dim=-1, keepdim=True)

        mask_logits = (100.0 * image_mask_features @ text_mask_features.T)
        gender_logits = (100.0 * image_gender_features @ text_gender_features.T)
        age_logits = (100.0 * image_age_features @ text_age_features.T)
        
        return mask_logits, gender_logits, age_logits
    
class CLIPQA(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
        
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)
        
        Q_mask = """Given a set of images, identify the one that corresponds to the following descriptions:

1. A photo of a person correctly wearing a mask, covering mouth and nose completely.
2. A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.
3. A photo of a person without a mask."""
        Q_gender = """Given a set of images, identify the one that corresponds to the following descriptions:

1. A photo of a man.
2. A photo of a woman."""
        Q_age = """Given a set of images, identify the one that corresponds to the following age categories:

1. A photo of a young person under 30.
2. A photo of a middle-aged person aged over 30 and under 60.
3. A photo of an elderly person over 60 years old."""

        self.age_features = self.model.encode_text(clip.tokenize(Q_age).cuda()).type(torch.float32)
        self.gender_features = self.model.encode_text(clip.tokenize(Q_gender).cuda()).type(torch.float32)
        self.mask_features = self.model.encode_text(clip.tokenize(Q_mask).cuda()).type(torch.float32)

        self.age = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )
        self.gender = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 2)
        )
        self.mask = nn.Sequential(
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 3)
        )

    def forward(self, x):
        x = self.model.encode_image(x).type(torch.float32)
        
        age = torch.concat([self.age_features.repeat(x.shape[0], 1), x], dim=-1)
        age = self.age(age)
        gender = torch.concat([self.gender_features.repeat(x.shape[0], 1), x], dim=-1)
        gender = self.gender(gender)
        mask = torch.concat([self.mask_features.repeat(x.shape[0], 1), x], dim=-1)
        mask = self.mask(mask)
        
        return mask, gender, age
        
        
        

class CLIP3Head3Proj_Agg_proper_prompt(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
        
        # load pretrained heads
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        pretrained_model.eval()

        print("loading age model...", end=' ')
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Age_detail/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.age_i = copy.deepcopy(pretrained_model.age_i)
        self.age_t = copy.deepcopy(pretrained_model.age_t)
        # self.age_i[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        # self.age_t[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        print("done.")
        
        print("loading gender model...", end=' ')
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Gender/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.gender_i = copy.deepcopy(pretrained_model.gender_i)
        self.gender_t = copy.deepcopy(pretrained_model.gender_t)
        # self.gender_i[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        # self.gender_t[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        print("done.")
        
        print("loading mask model...", end=' ')
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Mask_detail/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.mask_i = copy.deepcopy(pretrained_model.mask_i)
        self.mask_t = copy.deepcopy(pretrained_model.mask_t)
        # self.mask_i[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        # self.mask_t[0].register_forward_hook(lambda module,ipt,opt: F.dropout(opt, .2))
        print("done.")
        
        del pretrained_model    # free
            
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)
        # for name, param in self.named_parameters():
        #     if param.requires_grad:
        #         print(f'{name} will be trained.')
        
        mask_captions = [
            'A photo of a person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        self.age_captions = [
            [
                [
                    'a photo of a young man correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of a middle-aged man correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of an elderly man correctly wearing a mask, covering mouth and nose completely.',
                ],
                [
                    'a photo of a young man who wear a mask improperly, expose mouth or nose.',
                    'a photo of a middle-aged man who wear a mask improperly, expose mouth or nose.',
                    'a photo of an elderly man who wear a mask improperly, expose mouth or nose, or wear a scarf.',
                ],
                [
                    'a photo of a young man without mask under 30.',
                    'a photo of a middle-aged man without mask aged between 30 and 60.',
                    'a photo of an elderly man without mask over 60 years old.',
                ]
            ],
            [
                [
                    'a photo of a young woman correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of a middle-aged woman correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of an elderly woman correctly wearing a mask, covering mouth and nose completely.',
                ],
                [
                    'a photo of a young woman who wear a mask improperly, expose mouth or nose.',
                    'a photo of a middle-aged woman who wear a mask improperly, expose mouth or nose.',
                    'a photo of an elderly woman who wear a mask improperly, expose mouth or nose, or wear a scarf.',
                ],
                [
                    'a photo of a young woman without mask under 30.',
                    'a photo of a middle-aged woman without mask aged between 30 and 60.',
                    'a photo of an elderly woman without mask over 60 years old.',
                ],
            ]
        ]
        for captions_gender in self.age_captions:
            for i in range(3):
                captions_gender[i] = torch.concat([
                    self.model.encode_text(clip.tokenize(captions_age).to(self.device)) for captions_age in captions_gender[i]
                ], dim=0)
                        
        mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        # age_captions = clip.tokenize([text for text in age_captions]).to(self.device)
        
        self.text_mask_features = self.model.encode_text(mask_captions).type(torch.float32)
        self.text_gender_features = self.model.encode_text(gender_captions).type(torch.float32)
        
    def forward(self, x):
        image_features = self.model.encode_image(x).type(torch.float32)
        
        image_mask_features = self.mask_i(image_features)
        image_mask_features = image_mask_features / image_mask_features.norm(dim=-1, keepdim=True)
        
        image_gender_features = self.gender_i(image_features)
        image_gender_features = image_gender_features / image_gender_features.norm(dim=-1, keepdim=True)        

        text_mask_features = self.mask_t(self.text_mask_features)
        text_mask_features = text_mask_features / text_mask_features.norm(dim=-1, keepdim=True)

        text_gender_features = self.gender_t(self.text_gender_features)
        text_gender_features = text_gender_features / text_gender_features.norm(dim=-1, keepdim=True)

        mask_logits = (100.0 * image_mask_features @ text_mask_features.T)
        pred_mask = mask_logits.argmax(dim=-1).detach().cpu().numpy()   # bs, 
        
        gender_logits = (100.0 * image_gender_features @ text_gender_features.T)
        pred_gender = gender_logits.argmax(dim=-1).detach().cpu().numpy()   # bs, 
        
        with torch.no_grad():
            text_age_features = torch.stack([   # bs, 3, 512
                self.age_captions[pred_gender[i]][pred_mask[i]] for i in range(pred_mask.shape[0])
            ]).type(torch.float32)

        image_age_features = self.age_i(image_features)
        image_age_features = image_age_features / image_age_features.norm(dim=-1, keepdim=True) # bs, 32
        text_age_features = torch.stack([self.age_t(features) for features in text_age_features])
        text_age_features = text_age_features / text_age_features.norm(dim=-1, keepdim=True)    # bs, 3, 32

        age_logits = (100.0 * torch.einsum('ab,abc->ac',image_age_features,text_age_features.permute(0,2,1)))
        
        return mask_logits, gender_logits, age_logits



class CLIP3Head3Proj_Agg_proper_prompt2(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
        
        # load pretrained heads
        # print("loading age model...", end=' ')
        # pretrained_model = CLIP3Head3Proj_Agg_proper_prompt(num_classes=18).to(self.device)
        # model_path = "/data/ephemeral/home/output/exp16/best.pth"
        # pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        # pretrained_model.eval()
        # self.age_i = copy.deepcopy(pretrained_model.age_i)
        # self.age_t = copy.deepcopy(pretrained_model.age_t)
        # print("done.")
        self.age_i = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(.2),
            nn.Linear(128, 32)
        )
        self.age_t = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(.2),
            nn.Linear(128, 32)
        )
        
        
        print("loading gender model...", end=' ')
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Gender/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        pretrained_model.eval()
        self.gender_i = copy.deepcopy(pretrained_model.gender_i)
        self.gender_t = copy.deepcopy(pretrained_model.gender_t)
        print("done.")
        
        print("loading mask model...", end=' ')
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Mask_detail/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        pretrained_model.eval()
        self.mask_i = copy.deepcopy(pretrained_model.mask_i)
        self.mask_t = copy.deepcopy(pretrained_model.mask_t)
        print("done.")
        
        del pretrained_model    # free
            
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)
        # for name, param in self.named_parameters():
        #     if param.requires_grad:
        #         print(f'{name} will be trained.')
        
        mask_captions = [
            'A photo of a person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        self.age_captions = [
            [
                [
                    'a photo of a young man correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of a middle-aged man correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of an elderly man correctly wearing a mask, covering mouth and nose completely.',
                ],
                [
                    'a photo of a young man who take mask improperly, expose mouth or nose.',
                    'a photo of a middle-aged man who take mask improperly, expose mouth or nose.',
                    'a photo of an elderly man who take mask improperly, expose mouth or nose, or use a scarf.',
                ],
                [
                    'a photo of a young person under 30.',
                    'a photo of a middle-aged person aged between 30 and 60.',
                    'a photo of an elderly person over 60 years old.',
                ]
            ],
            [
                [
                    'a photo of a young woman correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of a middle-aged woman correctly wearing a mask, covering mouth and nose completely.',
                    'a photo of an elderly woman correctly wearing a mask, covering mouth and nose completely.',
                ],
                [
                    'a photo of a young woman who take mask improperly, expose mouth or nose.',
                    'a photo of a middle-aged woman who take mask improperly, expose mouth or nose.',
                    'a photo of an elderly woman who take mask improperly, expose mouth or nose, or use a scarf.',
                ],
                [
                    'a photo of a young person under 30.',
                    'a photo of a middle-aged person aged between 30 and 60.',
                    'a photo of an elderly person over 60 years old.',
                ],
            ]
        ]
        for captions_gender in self.age_captions:
            for i in range(3):
                captions_gender[i] = torch.concat([
                    self.model.encode_text(clip.tokenize(captions_age).to(self.device)) for captions_age in captions_gender[i]
                ], dim=0)
                        
        mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        # age_captions = clip.tokenize([text for text in age_captions]).to(self.device)
        
        self.text_mask_features = self.model.encode_text(mask_captions).type(torch.float32)
        self.text_gender_features = self.model.encode_text(gender_captions).type(torch.float32)
        
    def forward(self, x):
        image_features = self.model.encode_image(x).type(torch.float32)
        
        image_mask_features = self.mask_i(image_features)
        image_mask_features = image_mask_features / image_mask_features.norm(dim=-1, keepdim=True)
        
        image_gender_features = self.gender_i(image_features)
        image_gender_features = image_gender_features / image_gender_features.norm(dim=-1, keepdim=True)        

        text_mask_features = self.mask_t(self.text_mask_features)
        text_mask_features = text_mask_features / text_mask_features.norm(dim=-1, keepdim=True)

        text_gender_features = self.gender_t(self.text_gender_features)
        text_gender_features = text_gender_features / text_gender_features.norm(dim=-1, keepdim=True)

        mask_logits = (100.0 * image_mask_features @ text_mask_features.T)
        pred_mask = mask_logits.argmax(dim=-1).detach().cpu().numpy()   # bs, 
        
        gender_logits = (100.0 * image_gender_features @ text_gender_features.T)
        pred_gender = gender_logits.argmax(dim=-1).detach().cpu().numpy()   # bs, 
        
        with torch.no_grad():
            text_age_features = torch.stack([   # bs, 3, 512
                self.age_captions[pred_gender[i]][pred_mask[i]] for i in range(pred_mask.shape[0])
            ]).type(torch.float32)

        image_age_features = self.age_i(image_features)
        image_age_features = image_age_features / image_age_features.norm(dim=-1, keepdim=True) # bs, 32
        text_age_features = torch.stack([self.age_t(features) for features in text_age_features])
        text_age_features = text_age_features / text_age_features.norm(dim=-1, keepdim=True)    # bs, 3, 32

        age_logits = (100.0 * torch.einsum('ab,abc->ac',image_age_features,text_age_features.permute(0,2,1)))
        
        return mask_logits, gender_logits, age_logits
    

class CLIP3Head3Proj_Age_Aggregation(nn.Module):
    def __init__(self, num_classes):
        super().__init__()
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _ = clip.load("ViT-B/16", device=self.device)
        
        self.age_i = nn.Sequential(
            nn.Linear(512+64, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        self.age_t = nn.Sequential(
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Linear(128, 32)
        )
        
        # load pretrained heads
        print("loading gender model...", end=' ')
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Gender/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        pretrained_model.eval()
        self.gender_i = copy.deepcopy(pretrained_model.gender_i)
        self.gender_t = copy.deepcopy(pretrained_model.gender_t)
        print("done.")
        
        print("loading mask model...", end=' ')
        pretrained_model = CLIP3Head3Proj(num_classes=18).to(self.device)
        model_path = "/data/ephemeral/home/output/✨CLIP3Head3Proj_Mask_detail/best.pth"
        pretrained_model.load_state_dict(torch.load(model_path, map_location=self.device))
        pretrained_model.eval()
        self.mask_i = copy.deepcopy(pretrained_model.mask_i)
        self.mask_t = copy.deepcopy(pretrained_model.mask_t)
        print("done.")
        
        del pretrained_model    # free
            
        for name, param in self.model.named_parameters():
            param.requires_grad_(False)
        
        mask_captions = [
            'A photo of a person correctly wearing a mask, covering mouth and nose completely.',
            'A photo of improper mask usage, showing exposed mouth or nose, or using a scarf.',
            'A photo of a person without mask.',
        ]
        gender_captions = [
            'a photo of a man.',
            'a photo of an woman.',
        ]
        age_captions = [
            'a photo of a young person under 30.',
            'a photo of a middle-aged person aged between 30 and 60.',
            'a photo of an elderly person over 60 years old.',
        ]
        
        mask_captions = clip.tokenize([text for text in mask_captions]).to(self.device)
        gender_captions = clip.tokenize([text for text in gender_captions]).to(self.device)
        age_captions = clip.tokenize([text for text in age_captions]).to(self.device)
        
        self.text_mask_features = self.model.encode_text(mask_captions).type(torch.float32)
        self.text_gender_features = self.model.encode_text(gender_captions).type(torch.float32)
        self.text_age_features = self.model.encode_text(age_captions).type(torch.float32)

        

    def forward(self, x):
        image_features = self.model.encode_image(x).type(torch.float32)
        
        image_mask_features = self.mask_i(image_features)
        image_gender_features = self.gender_i(image_features)        
        image_age_features = self.age_i(
            torch.concat([image_mask_features, image_gender_features, image_features], axis=-1)
        )

        image_mask_features = image_mask_features / image_mask_features.norm(dim=-1, keepdim=True)
        image_gender_features = image_gender_features / image_gender_features.norm(dim=-1, keepdim=True)
        image_age_features = image_age_features / image_age_features.norm(dim=-1, keepdim=True)

        text_mask_features = self.mask_t(self.text_mask_features)

        text_gender_features = self.gender_t(self.text_gender_features)

        text_age_features = self.age_t(self.text_age_features)

        text_mask_features = text_mask_features / text_mask_features.norm(dim=-1, keepdim=True)
        text_gender_features = text_gender_features / text_gender_features.norm(dim=-1, keepdim=True)
        text_age_features = text_age_features / text_age_features.norm(dim=-1, keepdim=True)
        
        mask_logits = (100.0 * image_mask_features @ text_mask_features.T)
        gender_logits = (100.0 * image_gender_features @ text_gender_features.T)
        age_logits = (100.0 * image_age_features @ text_age_features.T)
        
        return mask_logits, gender_logits, age_logits