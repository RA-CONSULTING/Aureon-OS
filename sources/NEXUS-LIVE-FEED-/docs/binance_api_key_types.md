# Binance API Key Types

>> main

Binance requires API keys to authenticate trading, account, and other private endpoints. The platform currently supports three key types. Ed25519 keys are recommended for new integrations because they deliver the best mix of security and performance.

## Supported Key Types

- **Ed25519 (recommended)** — Asymmetric, compact signatures and fast verification.
- **HMAC** — Symmetric secret shared with Binance; deprecated in favor of asymmetric keys.
- **RSA** — Asymmetric keys supported at 2048 or 4096 bits.

Refer to the [REST](./binance_general_api_information.md) or [WebSocket](./binance_ws_api_general_info.md) documentation for request examples using each key type.

## Ed25519

Ed25519 keys use asymmetric cryptography. You register the public key with Binance and sign requests using the private key. Binance verifies the signature with the public key.

Ed25519 delivers security comparable to 3072-bit RSA while keeping both the key material and generated signatures small, which accelerates signing and verification. The combination of high security and low overhead makes Ed25519 the recommended choice for most workloads.

**Sample public key**

```
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAgmDRTtj2FA+wzJUIlAL9ly1eovjLBu7uXUFR+jFULmg=
-----END PUBLIC KEY-----
```

**Sample signature**

```
E7luAubOlcRxL10iQszvNCff+xJjwJrfajEHj1hOncmsgaSB4NE+A/BbQhCWwit/usNJ32/LeTwDYPoA7Qz4BA==
```

## HMAC

HMAC keys rely on symmetric cryptography. Binance generates a shared secret that both parties use to sign and verify payloads.

HMAC signatures are fast to compute and compact, but sharing the secret among multiple services or operators increases exposure relative to asymmetric approaches. Binance is deprecating HMAC keys, so migrate to Ed25519 or RSA when possible.

**Sample secret**

```
Fhs4lGae2qAi6VNjbJjebUAwXrIChb7mlf372UOICMwdKaNdNBGKtfdeUff2TTTT
```

**Sample signature**

```
7f3fc79c57d7a70d2b644ad4589672f4a5d55a62af2a336a0af7d4896f8d48b8
```

## RSA

RSA keys are also asymmetric. You provide Binance with your public key and use the private key to produce signatures that Binance can verify.

Binance supports 2048-bit and 4096-bit RSA keys. While secure, RSA signatures are significantly larger than Ed25519 or HMAC, which can reduce throughput or increase network overhead for high-frequency trading applications.

**Sample 2048-bit public key**

```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyfKiFXpcOhF5rX1XxePN
akwN7Etwtn3v05cZNY+ftDHbVZHs/kY6Ruj5lhxVFAq5dv7Ba9/4jPijXuMuIc6Y
8nUlqtrrxC8DEOAczw9SKATDYZN9nbLfYlbBFfHzRQUXdAtYCPI6XtxmJBS7aOBb
4nZe1SVm+bhLrp0YQnx2P0s+37qkGeVn09m6w9MnWxjgCkkYFPWQkXIu5qOnwx6p
NfqDmFD7d7dUc/6PZQ1bKFALu/UETsobmBk82ShbrBhlc0JXuhf9qBR7QASjHjFQ
2N+VF2PfH8dm5prZIpz/MFKPkBW4Yuss0OXiD+jQt1J2JUKspLqsIqoXjHQQGjL7
3wIDAQAB
-----END PUBLIC KEY-----
```

**Sample signature**

```
wS6q6h77AvH1TqwInoTDdWIIubRCiUP4RLG++GI24twL3BMtX0EEV+YT1eH8Hb8bLe0Rb9OhOHbt1CC3aurzoCTgZvhNek47mg+Bpu8fwQ7eRkXEiWBx5C8BNN73JwnnkZw4UzYvqiwAs162jToV8AL0eN043KJ3MEKCy3C6nyeYOFSg+1Cp637KtAZk3z7aHknSu7/PXSPuwMIpBgFctf8YKGZFAVRbgwlcgUDhXyaGts6OFePGy0jkZKJHawb/w5hoatatsfVmVC4hZ8fsfystQ9k5DNjTm7ROApWaXy9BsfAYcj13O424mqlpkKG4EGnIjOIWB/pRDDQEm2O/xg==
```

