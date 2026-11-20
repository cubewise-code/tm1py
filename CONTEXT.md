# TM1py — Context & Glossary

Domain language for TM1py, the Python client for IBM TM1 / Planning Analytics.
This file captures terms meaningful to TM1/PA practitioners.

## Blob data transfer (#1515)

Moving cube data through the file store with TI, so cells never pass through
Python.

- **Blob** — a file in an instance's file store (`}Externals` on v11, the
  file API on v12) that holds exported cells: one line per cell, one column per
  cube dimension in cube order, then the value; UTF-8, comma separated, quoted.
  v11 adds a UTF-8 BOM; `FileService.transfer_from` drops it.

- **Lean TI** — the generated export/load process style that does only the data
  work (`BlobProcessBuilder` lean mode): no view left on the server (the view is
  built in the prolog as a temporary object), no logging scaffolding. Contrasts
  with the **legacy** mode used by the existing `use_blob` read paths.

- **Slice** — a part of a query covering a contiguous group of one dimension's
  elements, produced by `CellService.split_mdx`. Slices together select the same
  cells as the original query, each cell once, so they can run in parallel.

- **Atomic function** — one of the single-purpose building blocks:
  `export_to_blob` (cells → blob), `FileService.transfer_from` (blob → other
  instance), `load_from_blob` (blob → cube or developer process). None calls
  another; each leaves the server clean on failure (export removes its partial
  file; load keeps the file for inspection).

- **Orchestrator** — caller code that chains atomic functions: single stream
  (export → transfer → load) or parallel slices. TM1py ships the functions, not
  the orchestrator; slice count is tuned per server (a 4 GB v12 instance failed
  under 8 parallel loads).

- **Developer process** — a user-written TI process passed to
  `load_from_blob(process_name=...)`; receives the file name in `pFileName`
  (`file_parameter`), reads UTF-8 and skips the header line if the export
  wrote one. The generated load takes no header.
