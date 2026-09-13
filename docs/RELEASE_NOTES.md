# Rhythia Map Studio 0.1.0

Initial community release for Windows x64. Generate, preview, edit and export
Rhythia Steam maps, with English and Spanish interfaces.

## Downloads

- Download the `windows-x64.zip` application package and extract it to a writable folder.
- Open `Launch Map Studio.cmd`. Keep `bin` and its `_internal` contents together.
- For optional vocal/instrument separation, extract `separator-cpu-windows-x64.zip`
  into the **same folder**, merging folders when prompted. The `separation` folder
  must sit beside `bin` and `Launch Map Studio.cmd`.
- The separator download includes the model and uses the CPU; no Python installation
  or NVIDIA GPU is required. Generation is offline after downloading the packages.
- The `source.zip` download is for contributors and contains no executable or model.
- `SHA256SUMS.txt` lists download checksums; compare with PowerShell's `Get-FileHash`.

## Known limitations

Tempo and section estimates need musical review. Variable tempo is experimental,
and structural analysis assumes a provisional 4/4 grid. Source separation can leak
between tracks. The app never launches Rhythia automatically.

Only the current project format is supported. Existing development builds do not
have a guaranteed project compatibility path. Binaries are not code-signed.

See the bundled README for usage and the third-party notices for dependency details.
