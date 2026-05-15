# iPhone Photo to HEIC & JPEG Converter

A tool to convert photos to both HEIC and JPEG formats with iPhone EXIF metadata that bypasses AI detection while **preserving camera information**.

## ✨ Features

- **Output both HEIC and JPEG** - Get both formats from one conversion
- **Organized folder structure** - Automatically organized into HEIC/, JPEG/, and Metadata/ folders
- **Smart file naming** - Files named as: `filename_iPhoneModel_mode`
- **Multiple iPhone models** - iPhone 15, 14, 13, etc. with dropdown selector
- **Multiple iOS versions** - iOS 18.5 down to 15.0 with a broader preset list
- **Three processing modes:**
  - `soft` - Subtle changes, might not bypass AI detection
  - `medium` - Balanced approach, good results
  - `hard` - Strong AI detection removal with noticeable grain
- **Metadata Protection** - Your camera info is preserved EVEN IF messaging apps strip it:
  - ✓ EXIF embedded in both HEIC and JPEG files
  - ✓ Backup JSON files organized in Metadata/ folder

## 📁 Output Structure

```
output/
├── HEIC/
│   ├── photo1_iPhone15Pro_hard.heic
│   ├── photo2_iPhone15Pro_hard.heic
│   └── ...
├── JPEG/
│   ├── photo1_iPhone15Pro_hard.jpg
│   ├── photo2_iPhone15Pro_hard.jpg
│   └── ...
└── Metadata/
    ├── photo1_iPhone15Pro_hard.metadata.json
    ├── photo2_iPhone15Pro_hard.metadata.json
    └── ...
```

## 📋 File Naming Convention

`filename_DeviceModel_ProcessingMode`

Examples:
- `sunset_iPhone15ProMax_hard.heic`
- `sunset_iPhone15ProMax_hard.jpg`
- `sunset_iPhone15ProMax_hard.metadata.json`

## 📁 Files

- `gui.py` - Main GUI application (recommended)
- `iphone_convert.py` - CLI version for batch processing
- `metadata_viewer.py` - Tool to verify metadata in HEIC files

## 🚀 How to Use

### Option 1: GUI (Easy)

```bash
python gui.py
```

1. Place photos in the `input/` folder
2. Select iPhone model and iOS version from dropdowns
3. Choose processing mode (hard is most effective)
4. Click "Start Conversion"
5. Check `output/` folder for results:
   - `output/HEIC/` - HEIC files with embedded EXIF
   - `output/JPEG/` - JPEG files with embedded EXIF
   - `output/Metadata/` - JSON backup files

Each converted photo generates 3 files with the same name:
- `photo_iPhone15Pro_hard.heic`
- `photo_iPhone15Pro_hard.jpg`
- `photo_iPhone15Pro_hard.metadata.json`

### Option 2: Command Line

```bash
python iphone_convert.py
```

Edit settings in `iphone_convert.py`:
- `INPUT_DIR` - Input folder path
- `IPHONE_MODEL` - Device model
- `IOS_VERSION` - iOS version
- `MODE` - "soft", "medium", or "hard"
- `BOTH_FORMATS` - True for both HEIC+JPEG (default), False for HEIC only

Outputs automatically organized into:
- `output/HEIC/`
- `output/JPEG/`
- `output/Metadata/`

## 🔍 Verify Metadata

Use the metadata viewer to check if your photos have camera information:

```bash
python metadata_viewer.py
```

Click "Open HEIC/JPEG File" and check:
- **EXIF section** - Contains camera model, iOS version, lens info, etc.
- **Backup File section** - Shows the corresponding .metadata.json file
- **All metadata locations**: HEIC file, JPEG file, and JSON backup

## 🔄 Which File to Use?

| Situation | Use |
|-----------|-----|
| Send to friends/family | **JPEG** (more compatible) |
| Long-term archival | **HEIC** (smaller, better quality) |
| Need absolute proof of metadata | **Keep all 3 files** (HEIC + JPEG + JSON) |
| Transfer via cloud/email | **Either** (both have EXIF) |
| Messaging app (WhatsApp, etc) | **Either + keep JSON backup** |

## 📋 What Gets Preserved

The `.heic.metadata.json` backup file contains:

```json
{
  "device_model": "iPhone 15 Pro Max",
  "ios_version": "18.2",
  "conversion_date": "2026-05-14T...",
  "exif": {
    "0th": {
      "Make": "Apple",
      "Model": "iPhone 15 Pro Max",
      ...
    },
    "Exif": {
      "DateTimeOriginal": "...",
      "LensModel": "...",
      ...
    }
  }
}
```

## ⚠️ Important Notes

**Why metadata disappears when sending via messaging apps:**
- WhatsApp, Telegram, Signal strip EXIF data for **privacy protection**
- This happens with ALL file formats (JPEG, PNG, HEIC, etc.)
- **This is by design**, not a bug

**Solutions:**
- ✓ Use the metadata backup file (`.metadata.json`)
- ✓ Share via cloud storage (OneDrive, Google Drive) instead of messaging
- ✓ Use direct file transfer (AirDrop, email)
- ✓ Use the metadata viewer to confirm data is preserved locally

## 🔧 Requirements

```bash
pip install pillow pillow-heif piexif numpy
```

Or install everything from the included manifest:

```bash
pip install -r requirements.txt
```

## 🧱 Windows EXE Build

To package the GUI into a standalone executable on Windows:

```bash
build_exe.bat
```

The resulting file will be created at `dist/MetaIphonePhoto.exe`.

## 📝 Tips

1. **Best results** - Use "hard" mode for maximum AI detection bypass
2. **Preserve originals** - Input folder files are never modified
3. **Batch processing** - Convert multiple photos at once
4. **Verify locally** - Check metadata with `metadata_viewer.py` before sending
5. **Backup files** - Keep the `.metadata.json` files as proof of camera info

## 🎯 Workflow

```
1. Put photos in input/ folder
                ↓
2. Run gui.py or iphone_convert.py
                ↓
3. Get organized output/
   ├── HEIC/        (iPhone format, smaller files)
   ├── JPEG/        (Universal format, wider compatibility)
   └── Metadata/    (JSON backup of all camera info)
                ↓
4. Use metadata_viewer.py to verify camera info is there
                ↓
5. Send photos (use HEIC or JPEG depending on recipient)
                ↓
6. If messaging app strips EXIF:
   → You still have the JSON metadata backup
   → Proves camera info was there
   → Can restore if needed
```

## 💾 File Storage Guide

**Recommended folder structure:**
```
My Photos/
├── Raw/              (original files)
├── Converted/
│   ├── HEIC/         (keep for archival)
│   ├── JPEG/         (use for sharing)
│   └── Metadata/     (keep as proof)
└── To Send/          (copy JPEG files here before sending)
```
