import json

# Load all 805 tradable pairs from the JSON file
with open('tradable_pairs.json', 'r') as f:
    data = json.load(f)
    pairs = data.get('pairs', [])

print(f"Total pairs: {len(pairs)}")

# Example: Print top 10 by volatility
sorted_pairs = sorted(pairs, key=lambda x: x.get('volatility', 0), reverse=True)
print("Top 10 pairs by volatility:")
for pair in sorted_pairs[:10]:
    print(f"{pair['symbol']}: Volatility={pair['volatility']}, Volume={pair['volume']}")

# You can add more analytics or export logic below
