"""Unwrap the transport envelope in memory and store the key in Secret Manager."""
import base64, pathlib, subprocess
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

root = pathlib.Path(__file__).resolve().parent
private = serialization.load_pem_private_key((root/'transport-private.pem').read_bytes(), password=None)
key = private.decrypt((root/'recovery-key.rsa').read_bytes(), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=b'Aureon Google Cloud deployment'))
if len(key) != 32:
    raise ValueError('Invalid recovery key size')
base = ['gcloud', 'secrets']
opts = ['--project=aureon-trading', '--quiet']
name = 'aureon-sero-workspace-recovery'
probe = subprocess.run(base+['describe', name]+opts, capture_output=True)
if probe.returncode == 0:
    command = base+['versions', 'add', name, '--data-file=-']+opts
elif b'NOT_FOUND' in probe.stderr:
    command = base+['create', name, '--replication-policy=automatic', '--data-file=-']+opts
else:
    raise RuntimeError('Unable to check Secret Manager metadata')
result = subprocess.run(command, input=base64.b64encode(key), capture_output=True)
if result.returncode:
    raise RuntimeError('Secret Manager write failed; no key value was logged')
print('Recovery key stored in Secret Manager: '+name)
