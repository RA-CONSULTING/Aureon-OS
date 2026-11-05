# Native process containment — receipt 1

Stage 7 only. This is a measured cold boot. It is not a claim that a live Aureon instance exists, and it is not a claim that the system is alive.

Verdict: **pass**. Allowed at default: **none**.
Release boundary: **HOLD**. Orange badge: unchanged.
Public pin: `34864ff0547d2cff03e707414743a3b0cc8770b5` (changed: False).
Live trading: false. Orders placed: false. Market data fetched: false.

## Cold boot

```bash
python -m aureon.containment.cold_boot
```

Command included `unshare --net`: **True** (measured).
Parent net namespace `net:[4026531840]`, child `net:[4026532213]` (measured).

## Zero-network default

Measurer control, outside the namespace: TCP 1.1.1.1:443 ok=True errno=None error=None bytes_read=0 (measured). No application payload was read.
Contained TCP 1.1.1.1:443 ok=False errno=101 error=ENETUNREACH (measured).
Contained libc connect to 1.1.1.1:443 ok=False errno=101 error=ENETUNREACH (measured).
Contained UDP 8.8.8.8:53 ok=False errno=101 error=ENETUNREACH (measured). Payload was one NUL byte, not a DNS query.
Contained TCP 2001:4860:4860::8888:53 ok=False errno=99 error=EADDRNOTAVAIL (measured).
Contained TCP 1.1.1.1:443 after importlib.reload(socket) ok=False errno=101 error=ENETUNREACH (measured).
Contained ICMP raw socket create ok=False errno=1 error=EPERM (measured). No datagram was sent.
Contained TCP 127.0.0.1:9 ok=False errno=101 error=ENETUNREACH (measured). Default allow is `none`.
`/proc/net/dev` interfaces: ['lo'] (measured).
lo flags before admin: {'errno': None, 'flags': 8, 'ok': True, 'up': False} (measured).
Effective caps after exec: 0000000000000000 (measured).

## What remains allowed

At process start, with capabilities already dropped: none. Localhost is not up. There is no default route.
The explicit allow path was not used for this cold boot. A separate probe passed a grant, did not connect, and shared the parent net namespace: True (measured).

## Gaps

- (measured) Before capability drop, mapped root set lo up. 127.0.0.1 then returned ECONNREFUSED. 1.1.1.1 stayed unreachable. The default payload drops capabilities first, and that same ioctl returns EPERM.
- (measured) Before capability drop, creating an ICMP raw socket returned ok=True errno=None error=None. No datagram was sent.
- (measured) The contained process is a new python -I. It does not import aureon and does not assign socket.socket. socket module at start: socket.
- (cited) mcp/aureon_public/sweep_guard.py replaces socket.socket in-process during a sweep. That is not a network namespace. This stage does not change that file or the public pin 34864ff0547d2cff03e707414743a3b0cc8770b5.
- (inferred) No seccomp filter and no landlock are installed. A kernel flaw in user or network namespaces is outside this receipt.
- (inferred) Mapped root in a new user namespace is not treated as CAP_NET_ADMIN on the parent network namespace. This receipt does not flip a host interface to test that.
- (measured) Before the sysfs remount, /sys/class/net listed docker0, enp0s3, lo. After remount it listed lo only. /proc/net/dev is the namespace device list and listed lo.
- (measured) Filesystem isolation is not this receipt. The go-live runbook was readable=True and /etc/passwd was readable=True. Contents were not recorded.
- (cited) Receipts 2, 3, 4, and 5 remain HOLD. The orange release-boundary badge is unchanged. scripts/linux/install-linux.sh still execs the isolated bootstrap and does not start this cold boot. No live Aureon instance is claimed. The system is not claimed alive.
- (measured) issued_at on the allow-path audit is this machine's UTC clock. It is not an external monotonic head.

## Still HOLD

- Receipt 2: exact target-source measurement and immutable release provenance — HOLD
- Receipt 3: durable HNC evidence with an external monotonic head anchor — HOLD
- Receipt 4: complete source-boundary census closure — HOLD
- Receipt 5: authenticated deployment receipt and provider-side read-back — HOLD

Started from `c68a89d2a184d99582bb24310b91e024323a212c`. Git HEAD at measurement: `c68a89d2a184d99582bb24310b91e024323a212c`.
source_sha256 binds the containment sources in this worktree. git_head_at_measurement is HEAD when the command ran. The commit that adds this file is not a second measurement. The UTC stamps are this machine's clock, not receipt 3.
