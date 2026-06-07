import easyocr
from PIL import Image
import os
import json
import numpy as np

reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

base = r'C:\Users\Administrator\Desktop\违规情况'
results = {}

for folder in os.listdir(base):
    folder_path = os.path.join(base, folder)
    if not os.path.isdir(folder_path):
        continue
    results[folder] = []
    for fname in os.listdir(folder_path):
        if fname.endswith('.png'):
            fpath = os.path.join(folder_path, fname)
            try:
                img = Image.open(fpath)
                img_np = np.array(img)
                text = reader.readtext(img_np, detail=0)
                results[folder].append({'file': fname, 'text': text})
                print(f'OK: {folder}/{fname}')
                print(f'  Text: {text}')
            except Exception as e:
                results[folder].append({'file': fname, 'text': [], 'error': str(e)})
                print(f'ERR: {folder}/{fname}: {e}')

out_path = os.path.join(base, 'ocr_results.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nDONE - saved to', out_path)
