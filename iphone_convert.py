#!/usr/bin/env python3
"""
Конвертирует фото в HEIC с iPhone EXIF и обходом AI-детекторов.
Зависимости: pip install pillow pillow-heif piexif numpy
"""

import sys
import io
import json
import piexif
import pillow_heif
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from datetime import datetime
from pathlib import Path

# ── Настройки ────────────────────────────────────────────────────────────────

INPUT_DIR    = "./input"
OUTPUT_DIR   = "./output"  # Main output folder
HEIC_DIR     = "./output/HEIC"
JPEG_DIR     = "./output/JPEG"
METADATA_DIR = "./output/Metadata"
IPHONE_MODEL = "iPhone 15 Pro Max"
IOS_VERSION  = "26.3"
QUALITY      = 100
BOTH_FORMATS = True  # Output both HEIC and JPEG

# Сила обработки: "soft" / "medium" / "hard"
# soft  — почти незаметно, может не помочь
# medium — лёгкие артефакты, хороший баланс
# hard  — заметное зерно, максимальный эффект
MODE = "hard"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# ── iPhone EXIF ───────────────────────────────────────────────────────────────

IPHONE_EXIF_BASE = {
    "0th": {
        piexif.ImageIFD.Make:             b"Apple",
        piexif.ImageIFD.Model:            IPHONE_MODEL.encode(),
        piexif.ImageIFD.Software:         IOS_VERSION.encode(),
        piexif.ImageIFD.Orientation:      1,
        piexif.ImageIFD.XResolution:      (72, 1),
        piexif.ImageIFD.YResolution:      (72, 1),
        piexif.ImageIFD.ResolutionUnit:   2,
        piexif.ImageIFD.YCbCrPositioning: 1,
    },
    "Exif": {
        piexif.ExifIFD.ExposureProgram:       2,
        piexif.ExifIFD.MeteringMode:          5,
        piexif.ExifIFD.Flash:                 16,
        piexif.ExifIFD.FocalLength:           (77, 10),
        piexif.ExifIFD.ColorSpace:            65535,
        piexif.ExifIFD.ExposureMode:          0,
        piexif.ExifIFD.WhiteBalance:          0,
        piexif.ExifIFD.SceneCaptureType:      0,
        piexif.ExifIFD.LensSpecification:     ((13, 10), (90, 10), (0, 1), (0, 1)),
        piexif.ExifIFD.LensMake:              b"Apple",
        piexif.ExifIFD.LensModel:             b"iPhone 15 Pro Max back triple camera 7.7mm f/2.8",
        piexif.ExifIFD.FNumber:               (28, 10),
        piexif.ExifIFD.ISOSpeedRatings:       64,
        piexif.ExifIFD.ExposureTime:          (1, 120),
        piexif.ExifIFD.ShutterSpeedValue:     (6965784, 1000000),
        piexif.ExifIFD.ApertureValue:         (2970854, 1000000),
        piexif.ExifIFD.BrightnessValue:       (3200000, 1000000),
        piexif.ExifIFD.ExposureBiasValue:     (0, 1),
        piexif.ExifIFD.SubjectDistance:       (0, 1),
        piexif.ExifIFD.FocalLengthIn35mmFilm: 57,
        piexif.ExifIFD.SensingMethod:         2,
        piexif.ExifIFD.CustomRendered:        2,
        piexif.ExifIFD.UserComment:           b"ASCII\x00\x00\x00",
    },
    "GPS": {}, "1st": {}, "Interop": {},
}

# ── Параметры по MODE ─────────────────────────────────────────────────────────

PARAMS = {
    "soft":   dict(jpeg_passes=2, jpeg_q=(78, 84), noise_sigma=(1.0, 2.0), grain=3,  resize_scale=(0.985, 0.995)),
    "medium": dict(jpeg_passes=3, jpeg_q=(68, 76), noise_sigma=(2.0, 4.0), grain=6,  resize_scale=(0.970, 0.985)),
    "hard":   dict(jpeg_passes=4, jpeg_q=(55, 68), noise_sigma=(3.5, 6.0), grain=10, resize_scale=(0.950, 0.970)),
}

P = PARAMS[MODE]

# ── Обработка пикселей ────────────────────────────────────────────────────────

def jpeg_pass(img: Image.Image) -> Image.Image:
    """Один JPEG round-trip — разрушает частотные AI-паттерны."""
    q = int(np.random.uniform(*P["jpeg_q"]))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=q, subsampling=2)
    buf.seek(0)
    return Image.open(buf).copy()


def add_film_grain(img: Image.Image) -> Image.Image:
    """
    Реалистичное зерно плёнки: шум зависит от яркости (тени шумят больше),
    немного коррелирован между пикселями — как у реального сенсора.
    """
    arr = np.array(img, dtype=np.float32)
    sigma = np.random.uniform(*P["noise_sigma"])

    # Люминансный шум (как ISO-шум камеры)
    lum_noise = np.random.normal(0, sigma, arr.shape[:2])
    # Размываем чуть-чуть чтобы был коррелирован (реальный шум не совсем случаен)
    from PIL import ImageFilter as IF
    noise_img = Image.fromarray(np.clip(lum_noise + 128, 0, 255).astype(np.uint8))
    noise_img = noise_img.filter(IF.GaussianBlur(radius=0.4))
    lum_noise = np.array(noise_img, dtype=np.float32) - 128

    for c in range(arr.shape[2]):
        channel_noise = lum_noise * np.random.uniform(0.7, 1.3)
        arr[:, :, c] = np.clip(arr[:, :, c] + channel_noise, 0, 255)

    # Дополнительное зерно в тёмных областях (как у реальных камер)
    dark_mask = (arr.mean(axis=2) < 80).astype(np.float32)
    extra = np.random.normal(0, sigma * 0.5, arr.shape)
    arr += extra * dark_mask[:, :, np.newaxis] * P["grain"] / 5
    arr = np.clip(arr, 0, 255)

    return Image.fromarray(arr.astype(np.uint8))


def resize_attack(img: Image.Image) -> Image.Image:
    """Resize разными фильтрами — ломает пространственные паттерны."""
    w, h = img.size
    scale = np.random.uniform(*P["resize_scale"])
    filters = [Image.BILINEAR, Image.BICUBIC, Image.LANCZOS]
    f1, f2 = np.random.choice(filters, 2, replace=False)
    small = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), f1)
    return small.resize((w, h), f2)


def color_shift(img: Image.Image) -> Image.Image:
    """Небольшой случайный сдвиг цвета — меняет статистику каналов."""
    img = ImageEnhance.Brightness(img).enhance(np.random.uniform(0.95, 1.05))
    img = ImageEnhance.Contrast(img).enhance(np.random.uniform(0.95, 1.05))
    img = ImageEnhance.Color(img).enhance(np.random.uniform(0.93, 1.07))
    img = ImageEnhance.Sharpness(img).enhance(np.random.uniform(0.85, 1.15))
    return img


def remove_ai_traces(img: Image.Image) -> Image.Image:
    """Полный пайплайн."""
    # Несколько JPEG-проходов — главный инструмент
    for _ in range(P["jpeg_passes"]):
        img = jpeg_pass(img)

    # Плёночное зерно
    img = add_film_grain(img)

    # Resize-атака
    img = resize_attack(img)

    # Цветовой сдвиг
    img = color_shift(img)

    # Финальный JPEG-проход
    img = jpeg_pass(img)

    return img


# ── EXIF ──────────────────────────────────────────────────────────────────────

def build_clean_exif(original_date: bytes | None, w: int, h: int) -> bytes:
    exif = {k: dict(v) for k, v in IPHONE_EXIF_BASE.items()}
    date_str = original_date or datetime.now().strftime("%Y:%m:%d %H:%M:%S").encode()
    exif["0th"][piexif.ImageIFD.DateTime]          = date_str
    exif["Exif"][piexif.ExifIFD.DateTimeOriginal]  = date_str
    exif["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
    exif["Exif"][piexif.ExifIFD.PixelXDimension]   = w
    exif["Exif"][piexif.ExifIFD.PixelYDimension]   = h
    return piexif.dump(exif)


def get_original_date(img: Image.Image) -> bytes | None:
    try:
        raw = img.info.get("exif")
        if raw:
            d = piexif.load(raw)
            return (d.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
                    or d.get("0th", {}).get(piexif.ImageIFD.DateTime))
    except Exception:
        pass
    return None


# ── Конвертация ───────────────────────────────────────────────────────────────

def convert_to_heic(src_path: Path, dst_path: Path) -> None:
    with Image.open(src_path) as img:
        original_date = get_original_date(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        img = remove_ai_traces(img)

        w, h = img.size
        exif_bytes = build_clean_exif(original_date, w, h)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst_path, format="HEIF", quality=QUALITY, exif=exif_bytes)
        
        # Save metadata
        base_name = dst_path.stem
        save_metadata(base_name, original_date, w, h)


def convert_to_both(src_path: Path, heic_dst: Path, jpeg_dst: Path) -> None:
    """Convert to both HEIC and JPEG with shared metadata"""
    with Image.open(src_path) as img:
        original_date = get_original_date(img)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        img = remove_ai_traces(img)

        w, h = img.size
        exif_bytes = build_clean_exif(original_date, w, h)
        
        heic_dst.parent.mkdir(parents=True, exist_ok=True)
        jpeg_dst.parent.mkdir(parents=True, exist_ok=True)
        Path(METADATA_DIR).mkdir(parents=True, exist_ok=True)
        
        # Save HEIC
        img.save(heic_dst, format="HEIF", quality=QUALITY, exif=exif_bytes)
        
        # Save JPEG
        img.save(jpeg_dst, format="JPEG", quality=QUALITY, exif=exif_bytes)
        
        # Save metadata
        base_name = heic_dst.stem
        save_metadata(base_name, original_date, w, h)


def save_metadata(base_name: str, original_date: bytes | None, w: int, h: int) -> None:
    """Save metadata to JSON file"""
    import json
    from datetime import datetime
    
    metadata = {
        "device_model": IPHONE_MODEL,
        "ios_version": IOS_VERSION,
        "conversion_date": datetime.now().isoformat(),
        "image_dimensions": f"{w}x{h}",
        "original_date": original_date.decode('utf-8', errors='replace') if original_date else None,
    }
    
    metadata_path = Path(METADATA_DIR) / (base_name + ".metadata.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        print(f"  Warning: Could not save metadata: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    pillow_heif.register_heif_opener()
    input_path  = Path(INPUT_DIR)

    if not input_path.exists():
        print(f"[!] Папка не найдена: {input_path.resolve()}")
        sys.exit(1)

    files = [f for f in input_path.iterdir()
             if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]

    if not files:
        print(f"[!] Нет фото в {input_path.resolve()}")
        sys.exit(1)

    print(f"Найдено файлов : {len(files)}")
    print(f"Режим          : {MODE.upper()}")
    print(f"Модель         : {IPHONE_MODEL}  |  iOS {IOS_VERSION}")
    print(f"Выходные форматы: HEIC + JPEG + Metadata\n")

    ok = err = 0
    for src in sorted(files):
        base_name = f"{src.stem}_{IPHONE_MODEL.replace(' ', '')}_{MODE}"
        heic_dst = Path(HEIC_DIR) / (base_name + ".heic")
        jpeg_dst = Path(JPEG_DIR) / (base_name + ".jpg")
        
        try:
            convert_to_both(src, heic_dst, jpeg_dst)
            print(f"  ✓  {src.name}")
            print(f"     ├─ HEIC: {heic_dst.name}")
            print(f"     ├─ JPEG: {jpeg_dst.name}")
            print(f"     └─ Metadata: {base_name}.metadata.json")
            ok += 1
        except Exception as e:
            print(f"  ✗  {src.name}  —  {e}")
            err += 1

    print(f"\nГотово: {ok} успешно, {err} ошибок.")
    print(f"\nВыходная структура:")
    print(f"  {Path(OUTPUT_DIR).resolve()}/")
    print(f"  ├─ HEIC/        (HEIC files)")
    print(f"  ├─ JPEG/        (JPEG files)")
    print(f"  └─ Metadata/    (JSON metadata files)")


if __name__ == "__main__":
    main()
