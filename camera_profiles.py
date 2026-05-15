IPHONE_MODELS = [
    "iPhone 15 Pro Max",
    "iPhone 15 Pro",
    "iPhone 15",
    "iPhone 15 Plus",
    "iPhone 14 Pro Max",
    "iPhone 14 Pro",
    "iPhone 14",
    "iPhone 14 Plus",
    "iPhone 13 Pro Max",
    "iPhone 13 Pro",
    "iPhone 13",
    "iPhone 13 mini",
]

IOS_VERSIONS = [
    "18.5",
    "18.4",
    "18.3",
    "18.2",
    "18.1",
    "18.0",
    "17.6",
    "17.5",
    "17.4",
    "17.3",
    "17.2",
    "17.1",
    "17.0",
    "16.7",
    "16.6",
    "16.5",
    "16.4",
    "16.3",
    "16.2",
    "16.1",
    "16.0",
    "15.8",
    "15.7",
    "15.6",
    "15.5",
    "15.4",
    "15.3",
    "15.2",
    "15.1",
    "15.0",
]

CAMERA_PROFILE_DEFINITIONS = {
    "rear_wide": {
        "label": "Rear Wide 1x",
        "lens_model_template": "{model} back wide camera 6.765mm f/1.78",
        "focal_length": (677, 100),
        "f_number": (178, 100),
        "focal_length_35mm": 24,
        "lens_spec": ((677, 100), (677, 100), (178, 100), (178, 100)),
    },
    "rear_ultra_wide": {
        "label": "Rear Ultra Wide 0.5x",
        "lens_model_template": "{model} back ultra wide camera 1.54mm f/2.4",
        "focal_length": (154, 100),
        "f_number": (24, 10),
        "focal_length_35mm": 13,
        "lens_spec": ((154, 100), (154, 100), (24, 10), (24, 10)),
    },
    "rear_telephoto_3x": {
        "label": "Rear Telephoto 3x",
        "lens_model_template": "{model} back telephoto camera 9.0mm f/2.8",
        "focal_length": (900, 100),
        "f_number": (28, 10),
        "focal_length_35mm": 77,
        "lens_spec": ((900, 100), (900, 100), (28, 10), (28, 10)),
    },
    "rear_telephoto_5x": {
        "label": "Rear Telephoto 5x",
        "lens_model_template": "{model} back telephoto camera 12.0mm f/2.8",
        "focal_length": (1200, 100),
        "f_number": (28, 10),
        "focal_length_35mm": 120,
        "lens_spec": ((1200, 100), (1200, 100), (28, 10), (28, 10)),
    },
    "rear_macro": {
        "label": "Rear Macro 0.5x",
        "lens_model_template": "{model} back ultra wide macro camera 1.54mm f/2.4",
        "focal_length": (154, 100),
        "f_number": (24, 10),
        "focal_length_35mm": 13,
        "lens_spec": ((154, 100), (154, 100), (24, 10), (24, 10)),
    },
    "front_true_depth": {
        "label": "Front TrueDepth 1x",
        "lens_model_template": "{model} front TrueDepth camera 2.71mm f/1.9",
        "focal_length": (271, 100),
        "f_number": (19, 10),
        "focal_length_35mm": 23,
        "lens_spec": ((271, 100), (271, 100), (19, 10), (19, 10)),
    },
}

MODEL_CAMERA_PROFILE_KEYS = {
    "iPhone 15 Pro Max": ["rear_wide", "rear_ultra_wide", "rear_telephoto_5x", "rear_macro", "front_true_depth"],
    "iPhone 15 Pro": ["rear_wide", "rear_ultra_wide", "rear_telephoto_3x", "rear_macro", "front_true_depth"],
    "iPhone 15": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
    "iPhone 15 Plus": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
    "iPhone 14 Pro Max": ["rear_wide", "rear_ultra_wide", "rear_telephoto_3x", "rear_macro", "front_true_depth"],
    "iPhone 14 Pro": ["rear_wide", "rear_ultra_wide", "rear_telephoto_3x", "rear_macro", "front_true_depth"],
    "iPhone 14": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
    "iPhone 14 Plus": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
    "iPhone 13 Pro Max": ["rear_wide", "rear_ultra_wide", "rear_telephoto_3x", "rear_macro", "front_true_depth"],
    "iPhone 13 Pro": ["rear_wide", "rear_ultra_wide", "rear_telephoto_3x", "rear_macro", "front_true_depth"],
    "iPhone 13": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
    "iPhone 13 mini": ["rear_wide", "rear_ultra_wide", "front_true_depth"],
}

DEFAULT_CAMERA_PROFILE_KEY = "rear_wide"


def build_camera_profile(profile_key: str, model: str) -> dict:
    profile = dict(CAMERA_PROFILE_DEFINITIONS[profile_key])
    profile["key"] = profile_key
    profile["model"] = model
    profile["lens_model"] = profile["lens_model_template"].format(model=model)
    return profile


def get_available_camera_profiles(model: str) -> list[dict]:
    profile_keys = MODEL_CAMERA_PROFILE_KEYS.get(model, [DEFAULT_CAMERA_PROFILE_KEY])
    return [build_camera_profile(profile_key, model) for profile_key in profile_keys]


def get_unavailable_camera_labels(model: str) -> list[str]:
    available_keys = set(MODEL_CAMERA_PROFILE_KEYS.get(model, [DEFAULT_CAMERA_PROFILE_KEY]))
    return [definition["label"] for key, definition in CAMERA_PROFILE_DEFINITIONS.items() if key not in available_keys]


def get_default_camera_profile(model: str) -> dict:
    return get_available_camera_profiles(model)[0]