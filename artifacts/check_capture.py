import json

d = json.load(open(r"C:\Users\samle\Aureon-OS-hf-publish\artifacts\space-runtime\capture-receipt.json", encoding="utf-8"))
print("file_count    :", d["file_count"])
print("source_commit :", d["source_commit"])
rows = {r["path"]: r for r in d["files"]}
print("total paths   :", len(rows))
for k in (
    "app.py",
    "requirements.txt",
    "app.yaml",
    "docker-compose.yml",
    "Dockerfile",
    ".dockerignore",
    "README.md",
    "sources/NEXUS-LIVE-FEED-/docs/CALANAIS_STANDING_STONES_NODE.md",
    "sources/NEXUS-LIVE-FEED-/docs/calanais_standing_stones_node.md",
):
    row = rows.get(k)
    print(f"{k:60} {row['size_bytes'] if row else 'MISSING'}")
