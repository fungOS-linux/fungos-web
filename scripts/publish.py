#!/usr/bin/env python3
"""Build fungos.dev locally, address it by CID, and stage it for the ingress.

There is no hosted build. One publish run:

  1. rebuilds the generated parts of the tree (scripts/build.sh),
  2. validates the publish directory against fab.toml,
  3. hashes a canonical tar of the tree into a CIDv1 (raw, sha2-256),
  4. stages the tree under that CID in the local site store,
  5. writes the static route manifest `fab-sites` serves from,
  6. prints the ingress route that makes the name resolvable.

`--apply` installs that route into the local Mycelium gateway. It rewrites the
gateway route file, regenerates the gateway certificate for the new names, and
restarts the frontdoor, so it is opt-in.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "fab.toml"


def load_contract() -> dict:
    import tomllib

    with CONTRACT_PATH.open("rb") as handle:
        return tomllib.load(handle)


def run(argv: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        argv, cwd=cwd, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(f"publish: {' '.join(argv)} failed ({result.returncode})")
    return result.stdout


def build(docs: bool) -> None:
    argv = [str(ROOT / "scripts/build.sh")]
    if docs:
        argv.append("--docs")
    print(f"build     {' '.join(argv)}")
    sys.stdout.flush()
    subprocess.run(argv, check=True, cwd=ROOT)


def validate(publish_dir: Path, required: list[str]) -> None:
    missing = [
        name
        for name in required
        if not (publish_dir / name).is_file() or (publish_dir / name).stat().st_size == 0
    ]
    if missing:
        raise SystemExit(
            "publish: publish directory is incomplete, missing or empty:\n  "
            + "\n  ".join(missing)
        )


def canonical_tar(publish_dir: Path) -> bytes:
    """Tar the tree with every filesystem-dependent field pinned."""
    files = sorted(path for path in publish_dir.rglob("*") if path.is_file())
    if not files:
        raise SystemExit(f"publish: nothing to publish in {publish_dir}")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for path in files:
            data = path.read_bytes()
            info = tarfile.TarInfo(path.relative_to(publish_dir).as_posix())
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.type = tarfile.REGTYPE
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def cid_for(digest: bytes) -> str:
    """CIDv1, raw codec, sha2-256 multihash."""
    multihash = b"\x12\x20" + digest
    return "b" + base64.b32encode(b"\x01\x55" + multihash).decode().lower().rstrip("=")


def site_cid(publish_dir: Path) -> tuple[str, dict]:
    archive = canonical_tar(publish_dir)
    digest = hashlib.sha256(archive).digest()
    return cid_for(digest), {
        "digest": f"sha256:{digest.hex()}",
        "bytes": len(archive),
    }


def stage(publish_dir: Path, state_dir: Path, cid: str) -> tuple[Path, bool]:
    destination = state_dir / cid
    expected, _ = site_cid(publish_dir)
    if destination.is_dir():
        if site_cid(destination)[0] == expected:
            return destination, False
        shutil.rmtree(destination)
    staging = Path(tempfile.mkdtemp(prefix=f".{cid}.", dir=state_dir))
    try:
        for source in sorted(publish_dir.rglob("*")):
            relative = source.relative_to(publish_dir)
            target = staging / relative
            if source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            target.chmod(0o644)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return destination, True


def route_manifest(contract: dict, cid: str) -> dict:
    site = contract["site"]
    cache = contract["cache"]
    hosts = [site["domain"], *site.get("aliases", []), contract["ingress"]["host"]]
    route = {
        "source": "local",
        "generation": f"cid:{cid}",
        "project": site["project"],
        "environment": site["environment"],
        "path": "/",
        "origin": {"kind": "artifact_prefix", "store": "local", "keyPrefix": cid},
        "cache": {
            "html": cache["html"],
            "assets": cache["assets"],
            "default": cache["default"],
            "assetExtensions": cache["asset_extensions"],
        },
    }
    return {
        "source": f"{site['id']}-web",
        "routes": [{**route, "domain": host} for host in hosts],
    }


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    try:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.close()
        os.replace(handle.name, path)
    except BaseException:
        handle.close()
        os.unlink(handle.name)
        raise


def ingress_route(contract: dict) -> dict:
    site = contract["site"]
    bind = contract["ingress"]["bind"]
    return {
        "name": site["id"],
        "hosts": [contract["ingress"]["host"], site["domain"], *site.get("aliases", [])],
        "upstream": [f"http://{bind}"],
        "priority": 10,
    }


def apply_ingress(route: dict) -> None:
    status = json.loads(run(["mycelium", "gateway", "status", "--json"]))
    routes_path = Path(status["routes"])
    document = json.loads(routes_path.read_text())
    routes = [entry for entry in document.get("routes", []) if entry.get("name") != route["name"]]
    routes.append(route)
    document["routes"] = routes
    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    try:
        json.dump(document, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.close()
        run(["mycelium", "gateway", "install", "--write", "--routes", handle.name])
    finally:
        os.unlink(handle.name)
    installed = json.loads(run(["mycelium", "gateway", "status", "--json"]))
    if not installed.get("listening"):
        raise SystemExit("publish: gateway is not listening after install")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-build", action="store_true", help="publish the tree as it is")
    parser.add_argument("--docs", action="store_true", help="regenerate docs HTML from docs-source/")
    parser.add_argument("--check", action="store_true", help="validate the tree and stop")
    parser.add_argument(
        "--state-dir", type=Path, default=None, help="override the staging directory"
    )
    parser.add_argument("--apply", action="store_true", help="install the ingress route")
    args = parser.parse_args()

    contract = load_contract()
    publish_dir = (ROOT / contract["site"]["publish_dir"]).resolve()
    state_dir = args.state_dir or Path(contract["publish"]["state_dir"]).expanduser()

    if not args.no_build:
        build(args.docs)
    validate(publish_dir, contract["check"]["required"])
    if args.check:
        print(f"checked   {publish_dir}")
        return 0

    state_dir.mkdir(parents=True, exist_ok=True)
    cid, metadata = site_cid(publish_dir)
    staged, created = stage(publish_dir, state_dir, cid)

    manifest_path = state_dir / "manifest.json"
    write_json(manifest_path, route_manifest(contract, cid))
    write_json(
        state_dir / f"{contract['site']['id']}-site.json",
        {
            "cid": cid,
            "domain": contract["site"]["domain"],
            "publishDir": contract["site"]["publish_dir"],
            **metadata,
        },
    )

    route = ingress_route(contract)
    action = "staged" if created else "unchanged"
    print(f"{action:<9} {staged}")
    print(f"cid       {cid}")
    print(f"manifest  {manifest_path}")
    print()
    print("serve locally:")
    print("  scripts/serve.sh")
    print()
    print("ingress route (Mycelium gateway):")
    print(json.dumps(route, indent=2))
    print()
    print("install it (regenerates the gateway certificate and restarts the frontdoor):")
    print("  scripts/publish.py --no-build --apply")

    if args.apply:
        apply_ingress(route)
        print()
        print(f"applied   https://{contract['ingress']['host']}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
