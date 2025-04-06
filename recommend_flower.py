# recommend_flower.py

flower_keywords = {
    "love": "Red Rose",
    "romantic": "Tulip",
    "congratulations": "Sunflower",
    "birthday": "Gerbera Daisy",
    "apology": "Lily",
    "funeral": "White Lily",
    "sympathy": "Chrysanthemum",
    "wedding": "Peony",
    "graduation": "Orchid",
    "friendship": "Yellow Rose",
    "get well": "Daffodil",
    "thank you": "Pink Carnation",
    "celebration": "Hydrangea",
    "baby": "Baby's Breath",
    "mother": "Carnation",
    "father": "Iris",
}

def recommend_flower(text):
    text_lower = text.lower()
    for keyword, flower in flower_keywords.items():
        if keyword in text_lower:
            return flower
    return "Mixed Bouquet"

