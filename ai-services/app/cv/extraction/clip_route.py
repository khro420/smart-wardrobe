import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel


class CLIPTemplateRouter:

    def __init__(self, model_name="openai/clip-vit-base-patch32"):

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)

        self.model.eval()

        # -------------------------
        # GARMENT TYPES (STRUCTURE)
        # -------------------------
        self.templates = {
            "short_sleeve_top": "a photo of a short sleeve t-shirt worn on a person",
            "long_sleeve_top": "a photo of a long sleeve shirt worn on a person",
            "hoodie": "a hoodie worn on a person, casual streetwear",
            "jacket": "a jacket worn on upper body",
            "coat": "a long coat worn on a person",
            "jeans": "denim jeans worn on legs",
            "trousers": "formal trousers worn on legs",
            "cargo_pants": "cargo pants with pockets worn on legs",
            "shorts": "short pants worn above knees",
            "dress": "a dress worn on a person"
        }

        # -------------------------
        # STYLE LAYER (NEW 🔥)
        # -------------------------
        self.style_templates = {
            "streetwear": "streetwear outfit, urban fashion style",
            "formal": "formal business outfit, professional clothing",
            "sport": "athletic sportswear outfit, gym clothing",
            "casual": "casual everyday outfit",
            "minimal": "minimal clean fashion outfit"
        }

        self.template_keys = list(self.templates.keys())
        self.style_keys = list(self.style_templates.keys())

        self.text_features = self._encode_texts(list(self.templates.values()))
        self.style_features = self._encode_texts(list(self.style_templates.values()))

    # -------------------------
    # TEXT ENCODING
    # -------------------------
    def _encode_texts(self, texts):

        inputs = self.processor(
            text=texts,
            return_tensors="pt",
            padding=True
        ).to(self.device)

        with torch.no_grad():
            features = self.model.get_text_features(**inputs)

        if hasattr(features, "pooler_output"):
            features = features.pooler_output

        features = torch.nn.functional.normalize(features, p=2, dim=-1)
        return features

    # -------------------------
    # IMAGE ROUTING
    # -------------------------
    def predict(self, image_bgr):

        image_rgb = image_bgr[:, :, ::-1]
        image = Image.fromarray(image_rgb.astype(np.uint8))

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            img_features = self.model.get_image_features(**inputs)

        if hasattr(img_features, "pooler_output"):
            img_features = img_features.pooler_output

        img_features = torch.nn.functional.normalize(img_features, p=2, dim=-1)

        # -------------------------
        # GARMENT SIMILARITY
        # -------------------------
        logits = (img_features @ self.text_features.T).squeeze(0)

        # temperature scaling (IMPORTANT)
        logits = logits * 20.0

        probs = torch.softmax(logits, dim=0)

        top_idx = torch.argmax(probs).item()

        # -------------------------
        # STYLE SIMILARITY
        # -------------------------
        style_logits = (img_features @ self.style_features.T).squeeze(0)
        style_logits = style_logits * 20.0
        style_probs = torch.softmax(style_logits, dim=0)

        style_result = {
            self.style_keys[i]: float(style_probs[i].item())
            for i in range(len(self.style_keys))
        }

        return {
            "template": self.template_keys[top_idx],
            "confidence": float(probs[top_idx].item()),
            "top_k": {
                self.template_keys[i]: float(probs[i].item())
                for i in torch.topk(probs, 3).indices.tolist()
            },
            "style": style_result
        }