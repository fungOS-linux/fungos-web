---
title: hyphae — open IMS/VoLTE control plane
source_commit: ee181b9261e2da6d280be7e85d6a695cf222f26e
watches:
  - README.md
  - docs/specs.md
  - docs/architecture.md
---
# hyphae

hyphae is a GPL-3.0-or-later, specification-derived IMS/VoLTE client for Linux
phones. When 2G and 3G were switched off, Linux phones lost voice, because the
AP-side IMS stack has never been open source. hyphae is the missing control
plane: SIP, IMS-AKA, registration, dialogs, SDP, carrier profiles, the Gm
security plane and a codec-agnostic media boundary.

It is a library and a lab client, not a shipping dialer. The protocol surface is
implemented and tested on a host with no modem and no network; the modem byte
I/O and the licensed speech codec are the two pieces that stay outside the core.

## What it owns

| Layer | Owner | Responsibility |
| --- | --- | --- |
| SIP messages and transactions | `sip` | RFC 3261 encoding, headers, client/server transactions |
| Subscriber key and USIM | `aka`, `usim` | Milenage, AUTN checks, TS 31.102 `AUTHENTICATE` |
| Control plane | `ims` | REGISTER/AKA, dialogs, MO/MT calls, SMS, hold/resume, E911 construction |
| Carrier data | `carrier` | TOML profiles keyed by MCC/MNC |
| Media framing | `media` | RTP/RTCP, jitter buffer, packet-loss concealment |
| Payload formats | `codec-amr`, `evs` | RFC 4867 and TS 26.445 packet layout only |
| Bearer and security | `transport` | mock, UDP/TCP, AT/QMI, MBIM, CCCI boundary, ESP/IPsec |

No default crate starts a thread, opens a socket or links a codec, so the whole
protocol surface builds and tests on a laptop.

## Status

Every implemented behaviour names a normative clause and the executable test
that proves it; the requirement matrix is the project's evidence.

| Area | State |
| --- | --- |
| Registration, IMS-AKA, USIM | implemented |
| Originating and terminating calls, CANCEL, PRACK, BYE | implemented |
| Hold/resume, call waiting, re-INVITE and UPDATE renegotiation | implemented |
| Forked INVITE, OPTIONS keepalive | implemented |
| SMS over IMS, both directions | implemented |
| Gm IPsec: authenticated ESP, SA negotiation, Linux XFRM | implemented |
| RTP/RTCP, jitter buffer, PLC | implemented |
| AT/QMI, MBIM, CCCI transports | modelled or boundary only |
| Emergency request construction | implemented; never transmitted |
| Byte-level modem I/O, live emergency calling | out of tree or regulated |

## The licensing seam

IMS voice uses AMR-WB and EVS, which are patent-encumbered. hyphae keeps the
protocol work separate from the codecs:

- the core is GPL-3.0-or-later and contains no AMR-WB or EVS implementation;
  `codec` ships the trait plus royalty-free Opus.
- AMR-WB lives in a separate, feature-off, patent-noticed package; its
  Apache-2.0 implementation library does not grant AMR-WB patent rights.
- retrofit mode runs the phone's own licensed codec; manufacture mode uses an
  ODM or licensed build. Vendor blobs are never redistributed.
- no code, strings or constants were derived from decompiled vendor binaries.

## Try it

The client builds and tests against host-only code:

```sh
cargo test --workspace
cargo run -p ims --example register_flow
cargo run -p ims --example call_flow
cd lab/pris && ./run.sh   # full REGISTER over real UDP against a P-CSCF stand-in
```

The lab uses public 3GPP test credentials only. Live emergency calling is
deliberately not reachable: the client builds the request and refuses to
transmit it over any real transport.

## Where it fits

hyphae is a consumer of the rest of the stack, not a replacement for it: the
modem supplies the IMS bearer, the network supplies the P-CSCF and S-CSCF, and
the host supplies identity and policy. It belongs beside the other runtime
components rather than inside provisioning or transport.

Source, matrix, architecture notes and the codec-licensing decision:
[github.com/ajmwagar/hyphae](https://github.com/ajmwagar/hyphae).
