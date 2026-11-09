---
title: Canvas and Spore rendering
---
# Canvas and Spore rendering

Canvas owns the window, workspace, focus, input lifecycle and pixels. A Spore
owns application state and describes what it wants drawn. It never receives a
framebuffer, texture, path, socket or window handle. A Spore is a signed wasm
component whose imports are exactly the capabilities its manifest grants; a
view is not a Spore and has no authority of its own.

Rust and Lua reach that boundary through the same versioned `soil-scene`
document. The host validates the document against a budget, binds input to an
owner generation, and draws it with the renderer it already uses for every
other surface. The document is the payload; Canvas remains the only presenter.

## What each layer owns

| Layer | Owns | Does not own |
| --- | --- | --- |
| Canvas | Window and workspace composition, focus, input lifecycle, theme, rasterizer and frame pacing | Spore state, application semantics or chart calculations |
| `soil-scene` | The schema-1 scene vocabulary, semantic inks and validation ceilings | Device handles, host policy or a rasterizer |
| `soil-sdk-canvas` | The Rust guest builder and the `present` calls | Host extent, validation or pixels |
| `soil-canvas-host` | Per-invocation budget, validation, generation and presenter transport | UI behaviour or a second renderer |
| Lua UI libraries | Portable tree, one-pass layout, semantic tokens and document construction | Host measurement, retained state or pixels |
| `soil-runtime` | The legacy core-Wasm `present()` host used by the S22 reference surface | A second contract or renderer |
| Canvas renderer | Rasterization and composition of the granted surface | Application data or layout policy |

`soil-runtime` and `soil-canvas-host` implement the same WIT contract. Component
Spores use `soil-canvas-host`; the core-Wasm adapter remains for the older S22
surface. New guest work should use the component path.

## The rendering path

```text
Rust: soil_sdk::canvas::Surface::present_scene
Lua:  ui.present(tree, theme) or ui.capture(...)
                         |
                         v
              soil-scene document
          { kind: "scene", schema: 1 }
                         |
                         v
       host validation, budget, generation
                         |
                         v
      Canvas presenter -> ui.sock -> renderer
```

The guest gets one granted surface. `soil:canvas` is an explicit host-shell
capability, not a generic application permission. It may present one document
per invocation and deliver one normalized input event. There is no frame callback, no shared
scene graph and no guest-owned swapchain. A rejected document keeps the last
good frame visible; a stale generation cannot move the owner backwards.

## One document, two SDKs

| Step | Rust | Lua |
| --- | --- | --- |
| Build a document | `soil_scene::Scene` or `soil_scene::Present` | `ui.document(tree, theme)` or `ui.capture(...)` |
| Present a prepared document | `Surface::present` | `ui.present_document(document)` |
| Build and present | `Surface::present_scene` | `ui.present(...)` |
| Present pixels | `Surface::present_rgba` | Not a tree path |
| Present a GPU lease | `Surface::present_lease` | Placement not exposed to the tree |

The Rust SDK is re-exported as `soil_sdk::canvas` behind the `canvas` feature.
The Lua libraries emit the same `soil-scene` document and call the host's
`canvas.present`, or `soil.canvas.present` on a non-Canvas host. Neither path
links a Rust renderer into Lua, and neither path gives the view a device handle.

```rust
use soil_sdk::canvas::Surface;
use soil_scene::{Content, Node, Rect, Scene, Transform};

let scene = Scene::new(vec![Node {
    id: "panel".into(),
    parent: None,
    transform: Transform {
        scale: [4.0, 2.0, 1.0],
        ..Transform::default()
    },
    content: Content::Rect(Rect::default()),
    transition_ms: None,
}]);

let state = Surface::present_scene(&scene)?;
```

```lua
local tree = ui.column {
  children = {
    ui.text("Throughput", { style = "title" }),
    ui.stat { label = "Requests", value = 42, unit = "%" },
  },
}

-- Pure artifact: inspect or test it without a compositor.
local document = ui.document(tree, module.theme)

-- Same document, presented through the granted host capability.
ui.present_document(document)
```

In a Canvas Lua module the library is available as `ui`. The painter-style
`fungos.ui` adapter exposes the same path through `ui.capture(...)` and
`ui.present(width, height, theme, paint)`.

## The wire document

A scene document is JSON with flat nodes. Positions are already resolved by the
guest's layout pass; the host does not re-interpret a widget tree.

```json
{
  "kind": "scene",
  "schema": 1,
  "nodes": [
    {
      "id": "panel",
      "transform": {
        "translation": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "scale": [4.0, 2.0, 1.0]
      },
      "type": "rect",
      "ink": "surface",
      "opacity": 1.0,
      "radius": 8.0
    }
  ]
}
```

- `kind` selects `scene`, `rgba` or `gpu_lease`. `scene` is the portable path;
  the other two carry pixels or a lease.
- `schema` is `1`. A host refuses a version it does not implement.
- Nodes are flat. A node's `parent` must name an earlier node in the same
  document.
- Canvas presents scene coordinates centred and aspect-free: x and y span -4
  to 4, and z controls depth. Scale is in eighths of the surface span, so
  `[4.0, 2.0, 1.0]` is half the width and a quarter of the height.
- Inks are semantic: `text`, `muted`, `surface`, `background`, `primary`,
  `success`, `warning`, `danger` and `info`. The theme owns their values. An
  optional literal `rgb` is for identity colours, not for ordinary UI.
- The document carries no paths, sockets, textures, raw keycodes or window
  handles.

The schema ceiling is 4,096 nodes and 32 MiB per payload. A host may enforce a
smaller budget: a Canvas Lua module defaults to 1,024 nodes and 256 KiB of
source. Rust guests can read `Surface::budget()` instead of hard-coding a host
budget.

## Layout, state and controls

There are two layout paths, and they answer different questions.

- `canvas.layout` is the native host path. It solves a flex tree through
  `soil-layout` (Taffy) with measured text; `unibus` uses it for its inbox.
- The portable Lua path in `sdk/ui/ui.lua` lays out a tree in one pass with no
  host measurement. The same tree can be previewed and tested without a
  compositor.

Both paths end at the same scene vocabulary. A view returns a tree; the library
places it; the host draws it. A view holds no state and receives no callbacks.
`ui.action("save")` emits an intent, and the Spore decides what it means. State
stays in the Spore because Canvas runs a fresh sandbox per render.

Buttons and host surfaces remain host-owned controls. They are hit regions, not
scene nodes. `widget.hit` registers a view's hit targets with the host; the host
keeps focus, pointer routing and the button's actual appearance. `ui.host_surface`
reserves layout space and calls `canvas.host_resource`; it never touches pixels
or receives a texture handle.

Dense time series are bounded before they become nodes. `ui.lttb` keeps the
endpoints and the dominant point in each bucket, and `ui.chart` applies it to
series that exceed the chart's mark count. A million-point series stays a
host-side GPU resource, not a million-node Lua tree.

## Compatibility and rendering coverage

`ui.render` uses the legacy `canvas.rect` and `canvas.text` primitives. It is the
compatibility path for a host that predates the scene document. `ui.present`
falls back to it when the host does not grant `canvas.present`, so an older
Canvas keeps drawing instead of going blank. The fallback uses the same layout
and tokens; it is not a second renderer.

Canvas refuses a module that mixes `canvas.present` with `canvas.rect` or
`canvas.text` in one render. A module chooses a document path or a primitive
path, not both.

The Canvas bridge currently draws `Rect` and `Text`. The schema accepts
`Polyline`, `Area`, `Band`, `Points`, `Heatmap`, `Candles`, `Shader`,
`GpuDense` and `GpuPoints3D`, but the bridge maps those nodes to groups so a
newer producer's scene survives an older host. This is compatibility, not a
chart renderer: a Spore that needs the full vocabulary should use a presenter
backed by the native `soil-scene-gpu` renderer.

## GPU surfaces

A Lua tree can reserve a place for a GPU surface; it cannot become one. The
native GraphGPU dashboard, the 20k-point cloud and the dense time-series
renderer keep their data, decimation and wgpu draw in a native host.

- A native producer renders into a shared frame buffer and publishes a
  monotonic revision.
- `Present::GpuLease` presents a lease for the granted surface; Canvas owns its
  extent and composition.
- `ui.host_surface` is the Lua placement point. It reserves a rect and calls
  the host resource API; a renderable `GpuLease` resource kind is not implemented
  yet. It does not receive pixels or a GPU handle.

A 1200x840 RGBA frame is about 4 MB, or about 242 MB/s at 60 Hz. Shared memory
avoids base64, but it is still a frame copy; a true texture lease is not
implemented. The Lua tree cannot reproduce the native 60 Hz path by emitting one
node per point, and the compositor should not grow a second chart renderer to
pretend otherwise.

## Status

| Capability | State |
| --- | --- |
| Schema-1 scene document | Contract |
| Rust guest SDK and host adapter | Implemented |
| Lua document construction and presentation | Implemented |
| `canvas.present` in the Canvas module host | Implemented |
| Legacy primitive fallback | Implemented |
| `Rect` and `Text` through the Canvas bridge | Implemented |
| Chart and point primitives through the Canvas bridge | Accepted by the schema; rendered as empty groups |
| GPU lease placement inside a Lua tree | Not implemented |
| Full Soil vocabulary in the Canvas renderer | Pending |

The schema is the stable part. Renderer coverage and host-resource placement can
improve without changing the document a view produces.

## Try it

From a Soil checkout:

```sh
cargo test -p soil-scene -p soil-sdk-canvas -p soil-canvas-host
cargo check -p soil-sdk-canvas --target wasm32-wasip2
```

From a Spores checkout, the Lua document fixture runs without a compositor:

```sh
cd spores/gallery
lua tests/soil_fixture.lua
```

## Where it fits

Canvas is a compositor and workspace owner, not an application framework. Soil
owns the guest contract and host adapter; Spores own the Lua UI library and
component catalog; applications own their state and their decisions. This keeps
one renderer, one input lifecycle and one place where pixels live.

- [Soil Canvas contract](https://github.com/fungOS-linux/soil/blob/main/docs/soil-canvas.md)
- [Soil SDK](https://github.com/fungOS-linux/soil/blob/main/docs/soil-sdk.md)
- [Spore UI model](https://github.com/fungOS-linux/spores/blob/main/docs/ui-model.md)
- [GPU surfaces in the Lua UI](https://github.com/fungOS-linux/spores/blob/main/docs/gpu-surfaces-in-lua-ui.md)
- [Component ownership and interfaces](https://fungos.dev/docs/ecosystem.html)
