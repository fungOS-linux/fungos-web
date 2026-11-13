---
title: Install and first boot
source_commit: 6bb83c9bb3b650483e0dbcb9c6a14b37906671b9
watches:
  - README.md
  - base/interfaces.md
  - docs/edge-dogfood.md
---
# Install and first boot

## Install on an existing machine

The unified installer brings Mycelium, Soil, Canvas and the terminal Spore to a
macOS or Linux machine you already use. It does not reinstall the operating
system.

```sh
curl -fsSL https://sh.fungos.dev/install.sh | bash -s --
```

Join an existing fleet with a short-lived code minted on the authority:

```sh
curl -fsSL https://sh.fungos.dev/install.sh | bash -s -- --code "MYC1-..."
```

Once the 0.1.0 archives are public, add `--release latest` to download and verify
the prebuilt binaries instead of building from source. The installer installs
Mycelium, the mesh DNS resolver, the iroh-tun overlay, Soil, the Canvas
workspace and the terminal Spore; on macOS it also installs `fungOS.app`. Linux
hosts need systemd. Sudo is used for the root tunnel and DNS services.

## Install fungOS Linux

Start with an isolated QEMU guest on a Linux KVM host. The fungOS repository includes the root filesystem builder. You must supply the boot components and configure enrollment separately. **Ready-to-flash installer images are not yet available.**

## Choose a target

| Target | Starting point | Remaining work |
| --- | --- | --- |
| Existing Linux/macOS machine | The one-line installer above | Installs Mycelium, Soil and Canvas; it does not install the fungOS image |
| QEMU/KVM | Generic rootfs plus matching boot components | Persistent disk, kernel/initramfs, enrollment and signed applications |
| Raspberry Pi | arm64 rootfs | Board firmware, kernel/modules, disk assembly and hardware qualification |
| Cloud VM | Cloud rootfs profile | Provider boot image and provisioning integration |

Mycelium owns machine identity and service/update policy. Genesis owns bootstrap/disk provisioning where used. Unibus owns application transport. The distribution should not replace these owners with a parallel implementation.

## First boot runbook

1. [Build and inspect](https://fungos.dev/docs/base.html) the chosen runtime profile on a Linux build host.
2. Assemble a new persistent boot target with a matching kernel and public recovery SSH key. Never clone another enrolled machine's private identity.
3. Install one first-contact adapter. Provide its machine-specific claim through an owner-only, protected single-use channel.
4. Boot and check that enrollment completed and the machine received its identity certificate.
5. Remove consumed claim media and plaintext bootstrap logs; retain the persistent root disk.
6. Install signed application packages and local service bindings using the chosen activation owner.
7. Configure explicit update policy, verify application-owned readiness and reboot without the claim media.

The generic first-contact adapter receives an environment file path, not embedded authority. A Mycelium adapter consumes an owner-only claim file. Do not deliver a secret through TFTP, public iPXE text or kernel arguments.

## Verify the installed guest

Run these only where the corresponding Mycelium CLI and edge bindings are installed:

```sh
mycelium node status --json
mycelium software reconcile --dry-run --json
mycelium update policy status --json
systemctl is-active mycelium mycelium-update.timer

# Display-edge bindings:
systemctl is-active unibus-router canvas-compositor canvas canvas-edge
```

Compare enrolled-certificate, machine-ID and SSH-host-public-key hashes before and after reboot. Inspect the actual framebuffer as well as the native units. A healthy service process is not proof of visible scanout.

## Tested configurations

The `docs/edge-dogfood.md` test record covers a persistent amd64 QEMU guest on 8 October 2026. Machine identity and the Canvas workspace survived restarts and reboot, and Unibus recovered through a same-version service repair. The test did not install a newer release.

The separate offline visual rollback fixture records recovery from signed failing Canvas and Unibus candidates. It is not a procedure to run on a personal machine or fleet node. See [updates](https://fungos.dev/docs/updates.html) for scope.

## Recovery

Inspect failed units and their journals. Preserve the previous verified artifact and a public-key SSH recovery route. Correct service or network drift without re-enrolling an otherwise healthy identity. Check certificate names rather than bypassing TLS verification.

Do not infer Pi hardware readiness, fresh PXE enrollment, encrypted-root unlock, GPU passthrough or TV media delivery from the QEMU test. Sources: public fungOS `README.md`, `base/interfaces.md`, `docs/edge-dogfood.md`.
