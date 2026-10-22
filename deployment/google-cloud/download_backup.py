"""Download and verify the six encrypted snapshot pieces on the new VM."""
import concurrent.futures, hashlib, json, pathlib, urllib.request

root = pathlib.Path(__file__).resolve().parent
links = json.loads((root/'download-links.json').read_text())
manifest = json.loads((root/'backup-manifest.json').read_text())

def download(part):
    dest = root/part['file']
    if dest.parent != root or '/' in part['file'] or '\\' in part['file']:
        raise ValueError('Unsafe archive filename')
    def valid():
        if not dest.exists() or dest.stat().st_size != part['bytes']:
            return False
        h = hashlib.sha256()
        with dest.open('rb') as stream:
            while chunk := stream.read(4*1024*1024): h.update(chunk)
        return h.hexdigest() == part['sha256']
    if not valid():
        try:
            with urllib.request.urlopen(links[part['file']], timeout=180) as response, dest.open('wb') as out:
                while block := response.read(4*1024*1024): out.write(block)
        except Exception:
            raise RuntimeError('Encrypted part download failed: '+part['file']) from None
        if not valid(): raise ValueError('Ciphertext checksum failed: '+part['file'])
    print('Verified '+part['file'], flush=True)

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(download, manifest['parts']))
print('All encrypted snapshot parts verified', flush=True)
