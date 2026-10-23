import re

with open('aureon_phi_radar.py', 'r', encoding='utf-8') as f:
    text = f.read()

def strip_emojis_from_logger(match):
    line = match.group(0)
    cleaned = ''.join(c for c in line if ord(c) < 128)
    return cleaned

pattern = r'logger\.info\(f"[^"]*"'
text = re.sub(pattern, strip_emojis_from_logger, text)

with open('aureon_phi_radar.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('All unicode stripped from logger lines')
