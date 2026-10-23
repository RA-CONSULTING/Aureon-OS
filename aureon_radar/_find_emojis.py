import re

with open(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\aureon_phi_radar.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF\U00002600-\U000026FF\U00002700-\U000027BF\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\U0001F100-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF]')

results = []
for i, line in enumerate(lines, 1):
    if emoji_pattern.search(line):
        results.append(f"{i}: {line.rstrip()}")

with open(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\_emoji_lines.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f"Found {len(results)} lines with emojis")
