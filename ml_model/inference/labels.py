"""
=========================================================
Disease Label Registry
=========================================================

Contains metadata for every disease class predicted
by the AI model.

The order MUST match the model output layer.

Author : Nigusu Tgabu
Project: AI Maize Disease Detection System
=========================================================
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Disease:

    id: int

    class_name: str

    display_name: str

    scientific_name: str

    description: str


DISEASES: List[Disease] = [

    Disease(
        id=0,
        class_name="Blight",
        display_name="Northern Leaf Blight",
        scientific_name="Exserohilum turcicum",
        description="A fungal disease that produces long gray lesions on maize leaves."
    ),

    Disease(
        id=1,
        class_name="Common_Rust",
        display_name="Common Rust",
        scientific_name="Puccinia sorghi",
        description="A fungal disease characterized by reddish-brown pustules."
    ),

    Disease(
        id=2,
        class_name="Gray_Leaf_Spot",
        display_name="Gray Leaf Spot",
        scientific_name="Cercospora zeae-maydis",
        description="A fungal disease causing rectangular gray lesions."
    ),

    Disease(
        id=3,
        class_name="Healthy",
        display_name="Healthy Leaf",
        scientific_name="None",
        description="No visible disease detected."
    )

]


CLASS_NAMES = [

    disease.class_name

    for disease in DISEASES

]


DISEASE_MAP: Dict[int, Disease] = {

    disease.id: disease

    for disease in DISEASES

}


CLASS_NAME_MAP: Dict[str, Disease] = {

    disease.class_name: disease

    for disease in DISEASES

}


def get_disease_by_id(class_id: int) -> Disease:
    """
    Return disease metadata using class index.
    """

    return DISEASE_MAP[class_id]


def get_disease_by_name(name: str) -> Disease:
    """
    Return disease metadata using class name.
    """

    return CLASS_NAME_MAP[name]