# app.py
import streamlit as st
import os
import io
from easyocr import Reader
from PIL import Image, ImageDraw, ImageFont
from deep_translator import GoogleTranslator
import time # To simulate processing time if needed

# ============================================
# Page Configuration (Streamlit)
# ============================================
st.set_page_config(layout="wide", page_title="Image Translator")

st.title("🖼️ Image Text Translator")
st.info("Upload an image, select the languages, and see the translated text overlaid.")

# ============================================
# Original Helper Functions (from run_translation.py)
# ============================================
# Font for rendering text. Place the .ttf file in the same folder.
FONT_PATH = "DejaVuSans.ttf" 

# Language Mappings (Expand as needed)
# Mapping display names to EasyOCR codes
ocr_lang_map = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese (Simplified)": "ch_sim",
    "Japanese": "ja",
    "Korean": "ko",
    # Add more languages supported by EasyOCR: https://www.jaided.ai/easyocr
}
# Mapping display names to GoogleTranslator codes (usually lowercase name or standard code)
translator_lang_map = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese (Simplified)": "zh-CN",
    "Japanese": "ja",
    "Korean": "ko",
    "Arabic": "ar",
    "Russian": "ru",
    "Portuguese": "pt",
    "Italian": "it",
    # Add more languages supported by deep-translator: https://deep-translator.readthedocs.io/en/latest/languages.html
}

def load_font(size=15):
    """Loads a font from the specified path, falling back to default if not found."""
    try:
        # Check if the font file exists
        if not os.path.exists(FONT_PATH):
             st.error(f"⚠️ Font file '{FONT_PATH}' not found in the script's directory. Using default font.")
             return ImageFont.load_default()
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        st.warning(f"⚠️ Error loading font '{FONT_PATH}'. Using default font.")
        return ImageFont.load_default()

def wrap_text_and_find_font(draw, text, box_width, box_height):
    """
    Finds the largest font size (minimum 12) where the text can be wrapped
    to fit within the given box dimensions.
    """
    # Adjust range if needed, starting smaller might be faster sometimes
    for size in range(40, 11, -2):  # Start medium, decrease size, stop at 12
        font = load_font(size)
        words = text.split()
        if not words:
            return font, [] # Return empty list if text is empty

        # --- Efficient Word Wrapping Logic ---
        wrapped_lines = []
        current_line = ""
        
        # Calculate approximate line height (adjust multiplier if needed)
        # We use a fixed multiplier initially; font metrics could be more precise but complex
        line_height_approx = size * 1.2 
        max_lines = int(box_height / line_height_approx)
        if max_lines == 0: continue # Cannot fit even one line at this size


        for word in words:
            # Check if adding the word exceeds width
            test_line = current_line + (" " if current_line else "") + word
            if draw.textlength(test_line, font=font) <= box_width:
                current_line = test_line
            else:
                # Add the completed line
                wrapped_lines.append(current_line)
                # Check if we exceeded max lines allowed by height
                if len(wrapped_lines) >= max_lines: 
                    current_line = "" # Indicate failure due to height
                    break
                # Start a new line with the current word
                current_line = word
                # Check if the new word itself is too long (rare case)
                if draw.textlength(current_line, font=font) > box_width:
                    # If a single word is too long, we might need to hyphenate or just let it overflow slightly.
                    # For simplicity here, we'll consider it a failure for this font size.
                    current_line = "" # Indicate failure due to width
                    break

        # If loop finished and current_line has content, add it
        if current_line:
             wrapped_lines.append(current_line)
             # Final height check after adding the last line
             if len(wrapped_lines) > max_lines:
                 continue # Failed due to height on the last line

        # If we successfully wrapped without breaking early
        if current_line != "": # Check if we bailed early due to width/height
            return font, wrapped_lines # Success! Found font size and wrapped lines

    # --- Fallback to smallest font size (12) if no larger size worked ---
    font = load_font(12)
    line_height_approx = 12 * 1.2
    max_lines = int(box_height / line_height_approx) if line_height_approx > 0 else 0
    words = text.split()
    wrapped_lines = []
    current_line = ""
    
    if not words: return font, [] # Handle empty text case
    if max_lines == 0: return font, [] # Cannot fit even one line of smallest font


    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if draw.textlength(test_line, font=font) <= box_width:
            current_line = test_line
        else:
            if len(wrapped_lines) < max_lines: # Check height *before* adding
               wrapped_lines.append(current_line)
               current_line = word
               if draw.textlength(current_line, font=font) > box_width: # Single word too long
                   # Truncate word or handle differently if needed. For now, we allow overflow.
                   pass 
            else:
                 current_line = "" # Stop adding lines if max height reached
                 break

    if current_line and len(wrapped_lines) < max_lines:
        wrapped_lines.append(current_line)
        
    # Only return lines if we have any (prevents errors if box is too small)
    return font, wrapped_lines if wrapped_lines else []


# ============================================
# Streamlit UI Elements
# ============================================
st.sidebar.header("⚙️ Configuration")

# File Uploader
uploaded_file = st.sidebar.file_uploader("1. Upload Image", type=["png", "jpg", "jpeg"])

# Language Selection
ocr_lang_names = list(ocr_lang_map.keys())
translator_lang_names = list(translator_lang_map.keys())

detected_langs_names = st.sidebar.multiselect(
    "2. Select Language(s) to Detect",
    options=ocr_lang_names,
    default=["Hindi", "English"] # Default detection as requested
)

# Ensure default doesn't cause error if list changes
default_target_lang = "Spanish" if "Spanish" in translator_lang_names else translator_lang_names[0] if translator_lang_names else "English"

target_lang_name = st.sidebar.selectbox(
    "3. Select Target Language for Translation",
    options=translator_lang_names,
    index=translator_lang_names.index(default_target_lang) if default_target_lang in translator_lang_names else 0
)

st.sidebar.info("The DejaVuSans.ttf font file must be in the same directory as this script for proper text rendering.")

# ============================================
# Main Execution Pipeline (Streamlit Triggered)
# ============================================
if uploaded_file is not None:
    # Convert uploaded file to PIL Image
    image_bytes = uploaded_file.getvalue()
    original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Get language codes from selected names
    detect_lang_codes = [ocr_lang_map[name] for name in detected_langs_names if name in ocr_lang_map]
    target_lang_code = translator_lang_map.get(target_lang_name, "en") # Default to english if not found

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Original Image")
        st.image(original_image, caption="Uploaded Image", use_container_width=True)

    # --- Initialize Libraries (Inside the check to use selected languages) ---
    if not detect_lang_codes:
        st.error("Please select at least one language to detect.")
    else:
        try:
             # --- Perform OCR, Translation, and Rendering ---
             with st.spinner(f"🔄 Initializing OCR for {', '.join(detected_langs_names)}..."):
                 reader = Reader(['hi'])
             st.info(f"✅ OCR Engine Ready for {', '.join(detected_langs_names)}!")

             with st.spinner(f"🔍 Running OCR on the image..."):
                 start_time = time.time()
                 # Use paragraph=True as in the original script
                 ocr_results = reader.readtext(image_bytes, paragraph=True)
                 ocr_time = time.time() - start_time
             st.info(f"✅ Detected {len(ocr_results)} text blocks in {ocr_time:.2f} seconds.")

             with st.spinner(f"🌐 Translating text to {target_lang_name}..."):
                 start_time = time.time()
                 translator = GoogleTranslator(source="auto", target=target_lang_code)
                 translated_blocks = []
                 error_count = 0
                 for i, (bbox, text) in enumerate(ocr_results):
                     try:
                         # Basic text cleaning (optional, can be expanded)
                         cleaned_text = text.strip()
                         if not cleaned_text: # Skip empty blocks
                             translated_text = ""
                         else:
                             translated_text = translator.translate(cleaned_text)
                             if translated_text is None: # Handle None return from translator
                                 translated_text = cleaned_text # Keep original if translation is None
                                 st.warning(f"⚠️ Translation returned None for block {i+1}. Keeping original: '{text[:30]}...'")
                         translated_blocks.append({"bbox": bbox, "text": translated_text if translated_text else " "}) # Use space if empty after translation
                     except Exception as e:
                         error_count += 1
                         # Keep original text on error
                         translated_blocks.append({"bbox": bbox, "text": text})
                 translate_time = time.time() - start_time
                 if error_count > 0:
                      st.warning(f"⚠️ Encountered {error_count} errors during translation. Original text kept for those blocks.")
             st.info(f"✅ Translation complete in {translate_time:.2f} seconds.")


             with st.spinner("🎨 Rendering translated overlay..."):
                start_time = time.time()
                # Use a fresh copy for drawing to not alter the original display
                img_to_draw = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                draw = ImageDraw.Draw(img_to_draw)

                for block in translated_blocks:
                    bbox = block['bbox']
                    text = block['text']

                    # Ensure bbox points are tuples of numbers
                    try:
                        bbox = [(int(p[0]), int(p[1])) for p in bbox]
                    except (ValueError, TypeError):
                        st.warning(f"Skipping block with invalid bounding box format: {bbox}")
                        continue


                    # Get bounding box coordinates accurately
                    # Bbox from easyocr paragraph=True is [top_left, top_right, bottom_right, bottom_left]
                    # It *should* already be sorted, but min/max ensures robustness
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    x1, y1 = min(x_coords), min(y_coords)
                    x2, y2 = max(x_coords), max(y_coords)
                    
                    # Ensure coordinates are valid
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(img_to_draw.width, x2), min(img_to_draw.height, y2)
                    
                    box_width = x2 - x1
                    box_height = y2 - y1

                    if box_width <= 0 or box_height <= 0:
                        st.warning(f"Skipping block with zero width/height: {bbox}")
                        continue # Skip if box has no area


                    # Erase original text area with a white box
                    draw.rectangle([(x1, y1), (x2, y2)], fill='white', outline="lightgray") # Slight outline for debug

                    # Get the best font and wrapped lines
                    final_font, lines_to_draw = wrap_text_and_find_font(draw, text, box_width, box_height)

                    # Draw the new text
                    if lines_to_draw: # Only draw if lines were successfully generated
                        current_y = y1
                        # Estimate line height more accurately using font metrics if possible
                        try:
                            # Using getbbox for a sample character (adjust if needed)
                            _ , top, _ , bottom = final_font.getbbox("A")
                            actual_char_height = bottom - top
                            # Add some leading (adjust 1.2 multiplier as needed for spacing)
                            line_height = actual_char_height * 1.2
                            if line_height <= 0: line_height = final_font.size * 1.2 # Fallback
                        except AttributeError: # Fallback for older PIL/Pillow or default font
                             line_height = final_font.size * 1.2
                             
                        # Center text vertically (optional)
                        total_text_height = len(lines_to_draw) * line_height
                        start_y = y1 + (box_height - total_text_height) / 2
                        current_y = max(y1, start_y) # Ensure text starts within the box

                        for line in lines_to_draw:
                            # Center text horizontally (optional)
                            line_width = draw.textlength(line, font=final_font)
                            start_x = x1 + (box_width - line_width) / 2
                            draw_x = max(x1, start_x) # Ensure text starts within the box

                            # Check if the drawing position is valid before drawing
                            if current_y + line_height <= y2 + 5: # Allow slight overflow vertically
                                draw.text((draw_x, current_y), line, font=final_font, fill="black")
                            current_y += line_height
                            if current_y > y2: # Stop if exceeding box height significantly
                                break
                    else:
                        st.warning(f"Could not fit text '{text[:30]}...' into box [{x1},{y1},{x2},{y2}]. Box may be too small.")


                render_time = time.time() - start_time
             st.info(f"✅ Rendering complete in {render_time:.2f} seconds.")

             # Convert finished image to bytes for display and download
             output_buffer = io.BytesIO()
             img_to_draw.save(output_buffer, format="JPEG") # Save as JPEG
             output_bytes = output_buffer.getvalue()

             with col2:
                 st.subheader("Translated Image")
                 st.image(output_bytes, caption=f"Translated ({target_lang_name})", use_container_width=True)

                 # --- Download Button ---
                 st.download_button(
                     label=f"⬇️ Download Translated Image (JPG)",
                     data=output_bytes,
                     file_name=f"translated_{uploaded_file.name.split('.')[0]}.jpg",
                     mime="image/jpeg"
                 )
             st.success("🎉 Processing Finished!")

        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            import traceback
            st.error(traceback.format_exc()) # Show detailed error for debugging

else:

    st.info("Please upload an image using the sidebar to start.")
