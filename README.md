# fungOS website

Static website for `fungos.dev`. The tree is built locally, addressed by CID, and
served by `fab-sites` behind the Mycelium gateway. There is no hosted build and no
Netlify configuration; `fab.toml` is the site contract.

## Build, publish, serve

```sh
scripts/publish.py            # build, validate, CID, stage, write the route manifest
scripts/serve.sh              # serve the staged tree on 127.0.0.1:7790
scripts/publish.py --apply    # also install the ingress route (opt-in)
```

`scripts/publish.py` rebuilds the generated parts of the tree, validates `dist/`
against `fab.toml`, hashes a canonical tar of the tree into a CIDv1, stages the tree
under `~/.local/share/fungos/sites/<cid>/`, and writes the static route manifest
`fab-sites` serves from. Publishing the same tree twice produces the same CID and
leaves the staged directory alone; the CID is the artifact identity and the staged
directory is the deployment. Nothing is uploaded to a third party.

`fab-sites` is the shared Fab static artifact proxy. `scripts/serve.sh` runs it
locally against the staged tree, so what is previewed is the same code path that
serves promoted Fab sites. The Mycelium gateway is the ingress: it terminates TLS
for the ingress name and forwards to `fab-sites`.

```sh
curl -sS -H 'Host: fungos.dev' http://127.0.0.1:7790/ | head
curl -sSI https://fungos.myc/          # after --apply
```

`scripts/publish.py --apply` merges the route into the gateway configuration. That
regenerates the gateway certificate for the new names and restarts the frontdoor,
which is why it is opt-in; the route it would install is printed on every run.

`scripts/build.sh` accepts `--docs` to regenerate documentation HTML as well. It
needs the code checkouts listed in `docs.tsv`, so it is separate from the default
publish path.

## Theme and layout

Shared layout and the project switcher are generated from
`ajmwagar/fpl-project-theme`. `dist/theme/REVISION` pins the exact source revision.
`dist/distro.css` imports that bundle and contains only fungOS-specific styles.
No theme server, package install or private Git clone is needed at deploy time.

`scripts/build.sh` finds the theme checkout via `FPL_THEME_DIR`, a sibling
`../fpl-project-theme` checkout, or `$HOME/src/fpl-project-theme`, then reinstall
the bundle:

```sh
cargo run -- --site ../fungos-web/dist --project fungos
cargo run -- --site ../fungos-web/dist --project fungos --check
```

The source website snapshot is also produced by the distribution tooling.
After replacing `dist/` from that source, run the shared theme installer again
before committing/publishing; otherwise the shared component can be lost.

Theme CSS is AGPL-3.0-or-later; its full license ships at `dist/theme/LICENSE`.
This does not relicense site content or upstream artwork. Asset terms are in
`ASSET-NOTICES.md` and `dist/theme/ASSET-NOTICES.md`.

UMIE and Unibus overview content lives in `dist/projects/`. The shared installer
recognizes these registered paths and applies each project's theme and current
menu selection. Update content here; regenerate logos and navigation from the
theme repository. Unibus is grouped with protocols, while UMIE is an application.

## Installer endpoint

`sh.fungos.dev/install.sh` is a Cloudflare Worker in `sh-install/` that proxies the
canonical installer from `fungOS-linux/mycelium`. There is no bucket or uploaded
copy to keep in sync; the Worker caches the upstream response for five minutes.
The website links to that endpoint directly, so serving the site does not need a
redirect rule.

Deploy it with an authenticated `wrangler`:

```sh
wrangler deploy --config sh-install/wrangler.toml
```

The route is a Worker custom domain, so Cloudflare owns the DNS record and
certificate for `sh.fungos.dev`.

## Documentation publication

`docs-source/` owns canonical site Markdown; `docs.tsv` lists its published pages
and explicit code owners. HTML and sibling `.md` exports are generated artifacts.
Each page shows the latest commit affecting its Markdown, plus the independent
reviewed code revision and watched paths. Regeneration does not bless code changes.

From the shared theme checkout, with the code checkouts named in the manifest:

```sh
cargo run --bin docs -- --manifest ../fungos-web/docs.tsv
cargo run -- --site ../fungos-web/dist --project fungos
cargo run --bin docs -- --manifest ../fungos-web/docs.tsv --check --fail-on-stale
cargo run -- --site ../fungos-web/dist --project fungos --check
```

Commit canonical Markdown before generation. If a freshness check fails, inspect
the listed changes and verify the guide before updating `source_commit`. An older
review may be published with its explicit warning; omit `--fail-on-stale` only
when that warning is intended. Missing source paths and invalid baselines fail.

UMIE owns the recipe inventory and historical runtime evidence. From its checkout:

```sh
scripts/catalog-models --site-source ../../fungos-web/docs-source/umie.md
scripts/catalog-models --site-source ../../fungos-web/docs-source/umie.md --check
```

Review the changed catalog and commit the canonical page, then regenerate the
site. The command updates only the marked matrix block. It does not advance the
review baseline. The matrix separates schema validation from historical runtime
records; this publication process does not execute models on hardware.

Copy for LLM copies the exact exported Markdown, including tables and metadata.
Clipboard access requires a supported secure context; the download is always
available. Check rendered links and the HTTP Markdown exports before publishing.
The publish run validates static artifacts and needs no private code checkout.
