function decodeBase64(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
}

function encodeBase64(value: Uint8Array): string {
  return btoa(String.fromCharCode(...value));
}

async function credentialKey(usages: KeyUsage[]): Promise<CryptoKey> {
  const configured = Deno.env.get("MASTER_ENCRYPTION_KEY")?.trim();
  if (!configured) throw new Error("MASTER_ENCRYPTION_KEY_NOT_CONFIGURED");
  const keyMaterial = new TextEncoder().encode(configured);
  if (keyMaterial.byteLength < 32) throw new Error("MASTER_ENCRYPTION_KEY_TOO_SHORT");
  return await crypto.subtle.importKey(
    "raw",
    keyMaterial.slice(0, 32),
    { name: "AES-GCM", length: 256 },
    false,
    usages,
  );
}

export async function encryptCredential(value: string, iv?: Uint8Array): Promise<{ encrypted: string; iv: string }> {
  if (!value) throw new Error("EMPTY_CREDENTIAL_REFUSED");
  const nonce = iv ?? crypto.getRandomValues(new Uint8Array(12));
  if (nonce.byteLength !== 12) throw new Error("INVALID_AES_GCM_IV");
  const key = await credentialKey(["encrypt"]);
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce as BufferSource },
    key,
    new TextEncoder().encode(value),
  );
  return { encrypted: encodeBase64(new Uint8Array(encrypted)), iv: encodeBase64(nonce) };
}

export async function encryptCredentialPacked(value: string): Promise<string> {
  const result = await encryptCredential(value);
  return `v2.${result.iv}.${result.encrypted}`;
}

export async function decryptCredential(encrypted: string, iv = ""): Promise<string> {
  if (!encrypted) throw new Error("MISSING_ENCRYPTED_CREDENTIAL");
  let ciphertext = encrypted;
  let encodedIv = iv;
  if (encrypted.startsWith("v2.")) {
    const parts = encrypted.split(".");
    if (parts.length !== 3) throw new Error("INVALID_PACKED_CREDENTIAL");
    [, encodedIv, ciphertext] = parts;
  }
  if (!encodedIv) throw new Error("MISSING_ENCRYPTED_CREDENTIAL_IV");
  const nonce = decodeBase64(encodedIv);
  if (nonce.byteLength !== 12) throw new Error("INVALID_AES_GCM_IV");
  const key = await credentialKey(["decrypt"]);
  const ciphertextBytes = decodeBase64(ciphertext);
  const ciphertextBuffer = ciphertextBytes.buffer.slice(
    ciphertextBytes.byteOffset,
    ciphertextBytes.byteOffset + ciphertextBytes.byteLength,
  ) as ArrayBuffer;
  const clear = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: nonce as BufferSource },
    key,
    ciphertextBuffer,
  );
  const value = new TextDecoder().decode(clear).trim();
  if (!value) throw new Error("DECRYPTED_CREDENTIAL_EMPTY");
  return value;
}
