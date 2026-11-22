<div align="center">

# 🖼️ OCR Image Translator

**Upload an image in one language — get the same image back with the text translated and overlaid in place.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![EasyOCR](https://img.shields.io/badge/OCR-EasyOCR-yellow?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## What it does
Most translators give you text back. This one gives you your **image** back — with every detected text region replaced by its translation, rendered at a font size fitted to the original box.

1. **Detect & read** text in the image with EasyOCR (bounding boxes + confidence)
2. **Translate** each region with Google Translate (via deep-translator)
3. **Re-render** the image with translated text overlaid in place (Pillow, with automatic font-size fitting and Arabic reshaping support)

## ✨ Key features
- 8 OCR source languages (English, Hindi, Spanish, French, German, Chinese, Japanese, Korean)
- 12 translation target languages, including Arabic and Russian
- In-place overlay — layout of the original image is preserved
- Smart text wrapping / font fitting per bounding box
- One-click Streamlit UI

## 🛠️ Tech stack
| Part | Tech |
|---|---|
| OCR | EasyOCR (PyTorch) |
| Translation | deep-translator (Google Translate) |
| Image rendering | Pillow, arabic-reshaper, python-bidi |
| UI | Streamlit |

## 🚀 Run it locally
```bash
pip install -r requirements.txt
streamlit run app.py
```
Then upload an image, choose source and target languages, and download the translated image.

## 📸 Sample
Input and translated output samples are in this repo (`Provisional.png`, `translated_output.jpg`).

## 🗺️ Roadmap
- [ ] Batch image processing
- [ ] Handwriting support evaluation
- [ ] Side-by-side original/translated comparison view

## 📄 License
MIT

---
*Built by [Daksh Sharma](https://github.com/Daksharma90) — Lead AI/ML Engineer @ TAILAI Labs.*
