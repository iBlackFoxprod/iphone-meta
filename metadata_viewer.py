#!/usr/bin/env python3
"""
Metadata Viewer - Check what camera information is in your HEIC files
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from pathlib import Path
import json
import piexif
import pillow_heif

def view_metadata(file_path):
    """Extract and display metadata from HEIC file"""
    metadata = {}
    
    try:
        pillow_heif.register_heif_opener()
        from PIL import Image
        
        with Image.open(file_path) as img:
            # Try to get EXIF
            if hasattr(img, 'info') and 'exif' in img.info:
                try:
                    exif_bytes = img.info['exif']
                    exif_dict = piexif.load(exif_bytes)
                    
                    # Format EXIF for display
                    for ifd_name, ifd_dict in exif_dict.items():
                        metadata[ifd_name] = {}
                        for tag, value in ifd_dict.items():
                            try:
                                if isinstance(value, bytes):
                                    metadata[ifd_name][piexif.TAGS[ifd_name][tag]["name"]] = value.decode('utf-8', errors='replace')
                                else:
                                    metadata[ifd_name][piexif.TAGS[ifd_name][tag]["name"]] = str(value)
                            except:
                                metadata[ifd_name][str(tag)] = str(value)
                except Exception as e:
                    metadata['Error Reading EXIF'] = str(e)
        
        if not metadata:
            metadata['Status'] = 'No EXIF data found in HEIC file'
            
    except Exception as e:
        metadata['Error'] = str(e)
    
    # Check for metadata backup file
    metadata_backup = file_path.with_suffix('.heic.metadata.json')
    if metadata_backup.exists():
        try:
            with open(metadata_backup, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            metadata['Backup File'] = backup_data
        except Exception as e:
            metadata['Backup File Error'] = str(e)
    else:
        metadata['Backup Status'] = 'No .metadata.json backup found'
    
    return metadata


class MetadataViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("HEIC Metadata Viewer")
        self.root.geometry("800x700")
        
        # Title
        title = ttk.Label(self.root, text="HEIC Photo Metadata Viewer", 
                         font=("Arial", 14, "bold"))
        title.pack(pady=10)
        
        # File selection
        button_frame = ttk.Frame(self.root)
        button_frame.pack(padx=10, pady=10, fill="x")
        
        self.open_btn = ttk.Button(button_frame, text="Open HEIC File", 
                                   command=self.open_file)
        self.open_btn.pack(side="left", padx=5)
        
        self.file_label = ttk.Label(button_frame, text="No file selected", 
                                    foreground="gray")
        self.file_label.pack(side="left", padx=10, fill="x", expand=True)
        
        # Metadata display
        display_frame = ttk.LabelFrame(self.root, text="Metadata", padding=10)
        display_frame.pack(padx=10, pady=5, fill="both", expand=True)
        
        self.text_display = scrolledtext.ScrolledText(display_frame, height=20, 
                                                       wrap="word", state="disabled")
        self.text_display.pack(fill="both", expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
    
    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Select HEIC file",
            filetypes=[("HEIC files", "*.heic"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        file_path = Path(file_path)
        self.file_label.config(text=file_path.name)
        self.status_var.set("Reading metadata...")
        self.root.update()
        
        try:
            metadata = view_metadata(file_path)
            self.display_metadata(metadata)
            self.status_var.set(f"✓ Metadata loaded from {file_path.name}")
        except Exception as e:
            self.display_error(str(e))
            self.status_var.set(f"✗ Error: {e}")
    
    def display_metadata(self, metadata):
        self.text_display.config(state="normal")
        self.text_display.delete(1.0, "end")
        
        for section, data in metadata.items():
            self.text_display.insert("end", f"\n{'='*70}\n{section}\n{'='*70}\n")
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        self.text_display.insert("end", f"\n{key}:\n")
                        for k, v in value.items():
                            self.text_display.insert("end", f"  {k}: {v}\n")
                    else:
                        # Truncate very long values
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:97] + "..."
                        self.text_display.insert("end", f"{key}: {value_str}\n")
            else:
                self.text_display.insert("end", f"{data}\n")
        
        self.text_display.config(state="disabled")
    
    def display_error(self, error):
        self.text_display.config(state="normal")
        self.text_display.delete(1.0, "end")
        self.text_display.insert("end", f"Error: {error}\n\n")
        self.text_display.insert("end", "Make sure the file is a valid HEIC image.")
        self.text_display.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = MetadataViewer(root)
    root.mainloop()
