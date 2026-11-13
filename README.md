# fungOS website

Published static website in `dist/`; hosting uses `netlify.toml`.

Shared layout and the project switcher are generated from
`ajmwagar/fpl-project-theme`. `dist/theme/REVISION` pins the exact source revision.
`dist/distro.css` imports that bundle and contains only fungOS-specific styles.
No theme server, package install or private Git clone is needed at deploy time.

To refresh from the theme checkout:

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
The hosting build validates static artifacts and needs no private code checkout.
