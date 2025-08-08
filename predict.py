import os
import torch
import torchvision.transforms as transforms
import torchvision
from PIL import Image
from config import BASE_DIR

class_names = [
    'bacterial_leaf_blight',
    'bacterial_leaf_streak',
    'bacterial_panicle_blight',
    'blast',
    'brown_spot',
    'dead_heart',
    'downy_mildew',
    'hispa',
    'normal',
    'tungro'
]

_model = None
_transform = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_model():
    global _model, _transform
    if _model is None:
        model_path = os.path.join(BASE_DIR, 'best_efficientnet_b4.pth')
        weights = torchvision.models.EfficientNet_B4_Weights.IMAGENET1K_V1
        _transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize(mean=weights.transforms().mean, std=weights.transforms().std),
        ])
        _model = torchvision.models.efficientnet_b4(weights=None)
        _model.classifier[1] = torch.nn.Linear(_model.classifier[1].in_features, len(class_names))
        _model.load_state_dict(torch.load(model_path, map_location=_device))
        _model.to(_device)
        _model.eval()

def predict_rice_disease(image_path):
    load_model()
    image = Image.open(image_path).convert("RGB")
    input_tensor = _transform(image).unsqueeze(0).to(_device)
    with torch.no_grad():
        outputs = _model(input_tensor)
        probs = torch.nn.functional.softmax(outputs, dim=1)
        conf, pred = torch.max(probs, 1)
    return class_names[pred.item()], conf.item() * 100
