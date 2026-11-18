import zipfile, struct

p = "/projects/u6vs/hnc-organism/runs/aureon-7b-pretrain/ckpt_0000030.pt"
z = zipfile.ZipFile(p)
pkls = [n for n in z.namelist() if n.endswith("data.pkl")]
print("pkl members:", pkls, flush=True)
blob = z.read(pkls[0])
print("data.pkl bytes:", len(blob), flush=True)

key = blob.find(b"embed_tokens.weight")
print("embed key offset:", key, flush=True)
seg = blob[max(0, key - 200): key + 600]

a152 = struct.pack("<q", 152064)
a65 = struct.pack("<q", 65536)
a152_4 = struct.pack("<i", 152064)
a65_4 = struct.pack("<i", 65536)
print("near key  count le-int64 152064:", seg.count(a152), " 65536:", seg.count(a65), flush=True)
print("near key  count le-int32 152064:", seg.count(a152_4), " 65536:", seg.count(a65_4), flush=True)
print("GLOBAL    count le-int64 152064:", blob.count(a152), " 65536:", blob.count(a65), flush=True)
print("GLOBAL    count le-int32 152064:", blob.count(a152_4), " 65536:", blob.count(a65_4), flush=True)

# numel encodings as additional witness
n152 = struct.pack("<i", 152064 * 3584)
n65 = struct.pack("<i", 65536 * 3584)
print("GLOBAL    numel(152064x3584):", blob.count(n152), " numel(65536x3584):", blob.count(n65), flush=True)

# top-level payload keys
for k in [b"step", b"tokens", b"model", b"optim"]:
    print("toplevel key", k, "at", blob.find(b"\x94" + k), flush=True)

# list the first storage records: persistent ids encode ('storage', key, numel)
print("first 24 namelist members:", z.namelist()[:24], flush=True)
print("num storage members:", sum(1 for n in z.namelist() if "/data/" in n and not n.endswith(".pkl")), flush=True)
