#!/usr/bin/env python3
"""
GUI для конвертера фото в HEIC с iPhone EXIF и защитой метаданных
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import sys
import io
import json
import struct
from pathlib import Path
from datetime import datetime

import piexif
import pillow_heif
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

from camera_profiles import (
    IPHONE_MODELS,
    IOS_VERSIONS,
    get_available_camera_profiles,
    get_default_camera_profile,
    get_unavailable_camera_labels,
)

# ── Настройки ────────────────────────────────────────────────────────────────

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

MODES = ["soft", "medium", "hard"]

PARAMS = {
    "soft":   dict(jpeg_passes=2, jpeg_q=(78, 84), noise_sigma=(1.0, 2.0), grain=3,  resize_scale=(0.985, 0.995)),
    "medium": dict(jpeg_passes=3, jpeg_q=(68, 76), noise_sigma=(2.0, 4.0), grain=6,  resize_scale=(0.970, 0.985)),
    "hard":   dict(jpeg_passes=4, jpeg_q=(55, 68), noise_sigma=(3.5, 6.0), grain=10, resize_scale=(0.950, 0.970)),
}


class ImageConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("iPhone Photo Converter")
        self.root.geometry("700x850")
        self.root.resizable(False, False)
        
        self.input_dir = Path("./input")
        self.output_heic_dir = Path("./output/HEIC")
        self.output_jpeg_dir = Path("./output/JPEG")
        self.output_metadata_dir = Path("./output/Metadata")
        self.is_converting = False
        self.camera_profiles = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        # Title
        title = ttk.Label(self.root, text="iPhone Photo to HEIC Converter", 
                         font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # Info frame about metadata
        info_frame = ttk.Frame(self.root)
        info_frame.pack(padx=10, pady=5, fill="x")
        info_text = "Metadata Protection: EXIF is embedded in HEIC files + backed up as .metadata.json\nMessaging apps may still strip EXIF, but your backup file preserves all camera info."
        info_label = ttk.Label(info_frame, text=info_text, foreground="green", 
                              font=("Arial", 9), wraplength=650, justify="left")
        info_label.pack(fill="x")
        
        # Frame for settings
        settings_frame = ttk.LabelFrame(self.root, text="Settings", padding=10)
        settings_frame.pack(padx=10, pady=5, fill="both", expand=False)
        
        # iPhone Model
        ttk.Label(settings_frame, text="iPhone Model:").grid(row=0, column=0, sticky="w", pady=5)
        self.model_var = tk.StringVar(value=IPHONE_MODELS[0])
        model_combo = ttk.Combobox(settings_frame, textvariable=self.model_var, 
                                   values=IPHONE_MODELS, state="readonly", width=30)
        model_combo.grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        
        # iOS Version
        ttk.Label(settings_frame, text="iOS Version:").grid(row=1, column=0, sticky="w", pady=5)
        self.ios_var = tk.StringVar(value=IOS_VERSIONS[0])
        ios_combo = ttk.Combobox(settings_frame, textvariable=self.ios_var, 
                                values=IOS_VERSIONS, state="readonly", width=30)
        ios_combo.grid(row=1, column=1, sticky="ew", pady=5, padx=5)

        # Camera Profile
        ttk.Label(settings_frame, text="Camera Profile:").grid(row=2, column=0, sticky="w", pady=5)
        self.camera_var = tk.StringVar()
        self.camera_combo = ttk.Combobox(settings_frame, textvariable=self.camera_var, state="readonly", width=30)
        self.camera_combo.grid(row=2, column=1, sticky="ew", pady=5, padx=5)

        self.camera_note = ttk.Label(settings_frame, text="", foreground="#777777", wraplength=430, justify="left")
        self.camera_note.grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 6))
        
        # Processing Mode
        ttk.Label(settings_frame, text="Processing Mode:").grid(row=4, column=0, sticky="w", pady=5)
        self.mode_var = tk.StringVar(value="hard")
        mode_combo = ttk.Combobox(settings_frame, textvariable=self.mode_var, 
                                 values=MODES, state="readonly", width=30)
        mode_combo.grid(row=4, column=1, sticky="ew", pady=5, padx=5)
        
        # Mode description
        mode_desc = ttk.Label(settings_frame, 
                             text="soft: subtle  |  medium: balanced  |  hard: strong AI-detection removal",
                             font=("Arial", 9), foreground="gray")
        mode_desc.grid(row=5, column=0, columnspan=2, sticky="w", pady=3)
        
        # Quality
        ttk.Label(settings_frame, text="HEIC Quality:").grid(row=6, column=0, sticky="w", pady=5)
        self.quality_var = tk.IntVar(value=100)
        quality_scale = ttk.Scale(settings_frame, from_=60, to=100, orient="horizontal", 
                                 variable=self.quality_var)
        quality_scale.grid(row=6, column=1, sticky="ew", pady=5, padx=5)
        self.quality_label = ttk.Label(settings_frame, text="100")
        self.quality_label.grid(row=6, column=2, padx=5)
        quality_scale.bind("<B1-Motion>", lambda e: self.update_quality_label())
        quality_scale.bind("<ButtonRelease-1>", lambda e: self.update_quality_label())
        
        settings_frame.columnconfigure(1, weight=1)
        self.model_var.trace_add("write", self.refresh_camera_options)
        self.refresh_camera_options()
        
        # Folder selection frame
        folder_frame = ttk.LabelFrame(self.root, text="Folders", padding=10)
        folder_frame.pack(padx=10, pady=5, fill="both", expand=False)
        
        ttk.Label(folder_frame, text="Input Folder:").grid(row=0, column=0, sticky="w", pady=5)
        self.input_label = ttk.Label(folder_frame, text=str(self.input_dir), 
                                    foreground="blue", wraplength=300)
        self.input_label.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        input_btn = ttk.Button(folder_frame, text="Browse", command=self.select_input_folder)
        input_btn.grid(row=0, column=2, padx=5)
        
        ttk.Label(folder_frame, text="Output Structure:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(folder_frame, text="output/  ├─ HEIC/  ├─ JPEG/  └─ Metadata/", 
                 foreground="green", font=("Courier", 9)).grid(row=1, column=1, columnspan=2, sticky="w", pady=5, padx=5)
        
        folder_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(self.root)
        button_frame.pack(padx=10, pady=10, fill="x")
        
        self.convert_btn = ttk.Button(button_frame, text="Start Conversion", 
                                     command=self.start_conversion)
        self.convert_btn.pack(side="left", padx=5)
        
        stop_btn = ttk.Button(button_frame, text="Stop", command=self.stop_conversion)
        stop_btn.pack(side="left", padx=5)
        
        # Output log
        log_frame = ttk.LabelFrame(self.root, text="Log", padding=5)
        log_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, 
                                                  state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
    
    def update_quality_label(self):
        self.quality_label.config(text=str(self.quality_var.get()))

    def refresh_camera_options(self, *_):
        model = self.model_var.get()
        profiles = get_available_camera_profiles(model)
        self.camera_profiles = {profile["label"]: profile for profile in profiles}

        labels = [profile["label"] for profile in profiles]
        self.camera_combo["values"] = labels

        current_label = self.camera_var.get()
        if current_label not in self.camera_profiles:
            default_profile = get_default_camera_profile(model)
            self.camera_var.set(default_profile["label"])

        unavailable = get_unavailable_camera_labels(model)
        if unavailable:
            self.camera_note.config(text=f"Disabled for this model: {', '.join(unavailable)}")
        else:
            self.camera_note.config(text="All camera profiles are compatible with this model.")

    def get_selected_camera_profile(self) -> dict:
        camera_label = self.camera_var.get()
        camera_profile = self.camera_profiles.get(camera_label)
        if not camera_profile:
            raise ValueError("Select a valid camera profile for the chosen iPhone model.")
        return camera_profile
    
    def log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update()
    
    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Select Input Folder", 
                                        initialdir=str(self.input_dir))
        if folder:
            self.input_dir = Path(folder)
            self.input_label.config(text=str(self.input_dir))
    
    def start_conversion(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, "end")
        self.log_text.config(state="disabled")
        
        self.is_converting = True
        self.convert_btn.config(state="disabled")
        
        thread = threading.Thread(target=self.run_conversion, daemon=True)
        thread.start()
    
    def stop_conversion(self):
        self.is_converting = False
        self.log("Conversion stopped by user.")
        self.convert_btn.config(state="normal")
    
    def run_conversion(self):
        try:
            pillow_heif.register_heif_opener()
            
            model = self.model_var.get()
            ios_version = self.ios_var.get()
            camera_profile = self.get_selected_camera_profile()
            mode = self.mode_var.get()
            quality = self.quality_var.get()
            
            self.log(f"Device: {model} | iOS: {ios_version}")
            self.log(f"Camera: {camera_profile['label']}")
            self.log(f"Mode: {mode.upper()} | Quality: {quality}\n")
            
            if not self.input_dir.exists():
                self.log(f"❌ Input folder not found: {self.input_dir}")
                self.convert_btn.config(state="normal")
                return
            
            files = [f for f in self.input_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS]
            
            if not files:
                self.log(f"❌ No images found in {self.input_dir}")
                self.convert_btn.config(state="normal")
                return
            
            self.log(f"Found {len(files)} files\n")
            
            ok = err = 0
            for src in sorted(files):
                if not self.is_converting:
                    break
                
                # Better naming: filename_device_mode
                base_name = f"{src.stem}_{model.replace(' ', '')}_{mode}"
                
                heic_dst = self.output_heic_dir / (base_name + ".heic")
                jpeg_dst = self.output_jpeg_dir / (base_name + ".jpg")
                
                try:
                    self.convert_to_both(src, heic_dst, jpeg_dst, model, ios_version, camera_profile, mode, quality)
                    self.log(f"✓ {src.name}")
                    self.log(f"  ├─ HEIC: {heic_dst.name}")
                    self.log(f"  ├─ JPEG: {jpeg_dst.name}")
                    self.log(f"  └─ Metadata: {base_name}.metadata.json\n")
                    ok += 1
                except Exception as e:
                    self.log(f"✗ {src.name} — {e}\n")
                    err += 1
            
            self.log(f"✅ Done: {ok} successful, {err} errors")
            self.log(f"\nOutput structure:")
            self.log(f"  {self.output_heic_dir.parent}/")
            self.log(f"  ├─ HEIC/")
            self.log(f"  ├─ JPEG/")
            self.log(f"  └─ Metadata/")
            
        except Exception as e:
            self.log(f"❌ Error: {e}")
        
        finally:
            self.convert_btn.config(state="normal")
    
    def convert_to_heic(self, src_path: Path, dst_path: Path, model: str, ios_version: str, 
                       camera_profile: dict, mode: str, quality: int) -> None:
        params = PARAMS[mode]
        
        with Image.open(src_path) as img:
            original_date = self.get_original_date(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            img = self.remove_ai_traces(img, params)
            
            w, h = img.size
            exif_dict = self.build_exif_dict(model, ios_version, camera_profile, original_date, w, h)
            exif_bytes = piexif.dump(exif_dict)
            
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save HEIC with EXIF
            try:
                img.save(dst_path, format="HEIF", quality=quality, exif=exif_bytes)
            except Exception as e:
                # Fallback: save without EXIF parameter, then add metadata via sidecar
                img.save(dst_path, format="HEIF", quality=quality)
            
            # Save metadata to dedicated folder
            base_name = dst_path.stem
            self.save_metadata_sidecar(self.output_metadata_dir / (base_name + ".metadata.json"), exif_dict, model, ios_version, camera_profile)
    
    def convert_to_both(self, src_path: Path, heic_dst: Path, jpeg_dst: Path, model: str, 
                    ios_version: str, camera_profile: dict, mode: str, quality: int) -> None:
        """Convert to both HEIC and JPEG with shared metadata"""
        params = PARAMS[mode]
        
        with Image.open(src_path) as img:
            original_date = self.get_original_date(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            
            # Apply processing once, save to both formats
            processed_img = self.remove_ai_traces(img, params)
            
            w, h = processed_img.size
            exif_dict = self.build_exif_dict(model, ios_version, camera_profile, original_date, w, h)
            exif_bytes = piexif.dump(exif_dict)
            
            # Ensure directories exist
            heic_dst.parent.mkdir(parents=True, exist_ok=True)
            jpeg_dst.parent.mkdir(parents=True, exist_ok=True)
            self.output_metadata_dir.mkdir(parents=True, exist_ok=True)
            
            # Save HEIC with EXIF
            try:
                processed_img.save(heic_dst, format="HEIF", quality=quality, exif=exif_bytes)
            except Exception as e:
                processed_img.save(heic_dst, format="HEIF", quality=quality)
            
            # Save JPEG with EXIF
            try:
                processed_img.save(jpeg_dst, format="JPEG", quality=quality, exif=exif_bytes)
            except Exception:
                processed_img.save(jpeg_dst, format="JPEG", quality=quality)
            
            # Save metadata to dedicated folder with better naming
            base_name = heic_dst.stem
            metadata_path = self.output_metadata_dir / (base_name + ".metadata.json")
            self.save_metadata_sidecar(metadata_path, exif_dict, model, ios_version, camera_profile)
    
    def jpeg_pass(self, img: Image.Image, params: dict) -> Image.Image:
        q = int(np.random.uniform(*params["jpeg_q"]))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, subsampling=2)
        buf.seek(0)
        return Image.open(buf).copy()
    
    def add_film_grain(self, img: Image.Image, params: dict) -> Image.Image:
        arr = np.array(img, dtype=np.float32)
        sigma = np.random.uniform(*params["noise_sigma"])
        
        lum_noise = np.random.normal(0, sigma, arr.shape[:2])
        noise_img = Image.fromarray(np.clip(lum_noise + 128, 0, 255).astype(np.uint8))
        noise_img = noise_img.filter(ImageFilter.GaussianBlur(radius=0.4))
        lum_noise = np.array(noise_img, dtype=np.float32) - 128
        
        for c in range(arr.shape[2]):
            channel_noise = lum_noise * np.random.uniform(0.7, 1.3)
            arr[:, :, c] = np.clip(arr[:, :, c] + channel_noise, 0, 255)
        
        dark_mask = (arr.mean(axis=2) < 80).astype(np.float32)
        extra = np.random.normal(0, sigma * 0.5, arr.shape)
        arr += extra * dark_mask[:, :, np.newaxis] * params["grain"] / 5
        arr = np.clip(arr, 0, 255)
        
        return Image.fromarray(arr.astype(np.uint8))
    
    def resize_attack(self, img: Image.Image, params: dict) -> Image.Image:
        w, h = img.size
        scale = np.random.uniform(*params["resize_scale"])
        filters = [Image.BILINEAR, Image.BICUBIC, Image.LANCZOS]
        f1, f2 = np.random.choice(filters, 2, replace=False)
        small = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), f1)
        return small.resize((w, h), f2)
    
    def color_shift(self, img: Image.Image) -> Image.Image:
        img = ImageEnhance.Brightness(img).enhance(np.random.uniform(0.95, 1.05))
        img = ImageEnhance.Contrast(img).enhance(np.random.uniform(0.95, 1.05))
        img = ImageEnhance.Color(img).enhance(np.random.uniform(0.93, 1.07))
        img = ImageEnhance.Sharpness(img).enhance(np.random.uniform(0.85, 1.15))
        return img
    
    def remove_ai_traces(self, img: Image.Image, params: dict) -> Image.Image:
        for _ in range(params["jpeg_passes"]):
            img = self.jpeg_pass(img, params)
        
        img = self.add_film_grain(img, params)
        img = self.resize_attack(img, params)
        img = self.color_shift(img)
        img = self.jpeg_pass(img, params)
        
        return img
    
    def build_exif_dict(self, model: str, ios_version: str, camera_profile: dict, original_date: bytes | None, 
                        w: int, h: int) -> dict:
        """Build EXIF dictionary (returns dict, not bytes)"""
        exif_base = {
            "0th": {
                piexif.ImageIFD.Make:             b"Apple",
                piexif.ImageIFD.Model:            model.encode(),
                piexif.ImageIFD.Software:         ios_version.encode(),
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
                piexif.ExifIFD.ColorSpace:            65535,
                piexif.ExifIFD.ExposureMode:          0,
                piexif.ExifIFD.WhiteBalance:          0,
                piexif.ExifIFD.SceneCaptureType:      0,
                piexif.ExifIFD.LensSpecification:     camera_profile["lens_spec"],
                piexif.ExifIFD.LensMake:              b"Apple",
                piexif.ExifIFD.LensModel:             camera_profile["lens_model"].encode(),
                piexif.ExifIFD.FNumber:               camera_profile["f_number"],
                piexif.ExifIFD.ISOSpeedRatings:       64,
                piexif.ExifIFD.ExposureTime:          (1, 120),
                piexif.ExifIFD.ShutterSpeedValue:     (6965784, 1000000),
                piexif.ExifIFD.ApertureValue:         (2970854, 1000000),
                piexif.ExifIFD.BrightnessValue:       (3200000, 1000000),
                piexif.ExifIFD.ExposureBiasValue:     (0, 1),
                piexif.ExifIFD.SubjectDistance:       (0, 1),
                piexif.ExifIFD.FocalLength:           camera_profile["focal_length"],
                piexif.ExifIFD.FocalLengthIn35mmFilm: camera_profile["focal_length_35mm"],
                piexif.ExifIFD.SensingMethod:         2,
                piexif.ExifIFD.CustomRendered:        2,
                piexif.ExifIFD.UserComment:           b"ASCII\x00\x00\x00",
            },
            "GPS": {}, "1st": {}, "Interop": {},
        }
        
        exif = {k: dict(v) for k, v in exif_base.items()}
        date_str = original_date or datetime.now().strftime("%Y:%m:%d %H:%M:%S").encode()
        exif["0th"][piexif.ImageIFD.DateTime]          = date_str
        exif["Exif"][piexif.ExifIFD.DateTimeOriginal]  = date_str
        exif["Exif"][piexif.ExifIFD.DateTimeDigitized] = date_str
        exif["Exif"][piexif.ExifIFD.PixelXDimension]   = w
        exif["Exif"][piexif.ExifIFD.PixelYDimension]   = h
        return exif
    
    def save_metadata_sidecar(self, metadata_path: Path, exif_dict: dict, model: str, ios_version: str, camera_profile: dict) -> None:
        """Save metadata as backup JSON file"""
        metadata = {
            "device_model": model,
            "ios_version": ios_version,
            "camera_profile": {
                "key": camera_profile["key"],
                "label": camera_profile["label"],
                "lens_model": camera_profile["lens_model"],
                "focal_length": str(camera_profile["focal_length"]),
                "f_number": str(camera_profile["f_number"]),
                "focal_length_35mm": camera_profile["focal_length_35mm"],
            },
            "conversion_date": datetime.now().isoformat(),
            "exif": self.exif_dict_to_readable(exif_dict),
        }
        
        try:
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            self.log(f"  (warning: could not save metadata backup: {e})")
    
    def exif_dict_to_readable(self, exif_dict: dict) -> dict:
        """Convert EXIF dict to readable format for JSON storage"""
        readable = {}
        try:
            for ifd_name, ifd_dict in exif_dict.items():
                readable[ifd_name] = {}
                for tag, value in ifd_dict.items():
                    # Try to decode bytes to string
                    if isinstance(value, bytes):
                        try:
                            readable[ifd_name][str(tag)] = value.decode('utf-8', errors='replace')
                        except:
                            readable[ifd_name][str(tag)] = str(value)
                    else:
                        readable[ifd_name][str(tag)] = str(value)
        except Exception as e:
            pass
        return readable
    
    def get_original_date(self, img: Image.Image) -> bytes | None:
        try:
            raw = img.info.get("exif")
            if raw:
                d = piexif.load(raw)
                return (d.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
                        or d.get("0th", {}).get(piexif.ImageIFD.DateTime))
        except Exception:
            pass
        return None
    



if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterGUI(root)
    root.mainloop()
