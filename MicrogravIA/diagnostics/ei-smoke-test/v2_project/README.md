# DetectaIA2.0 isolated PlatformIO project

This diagnostic project compiles the second Edge Impulse export without
exposing it to the original project-level library resolver.

- Environment: `ei-smoke-test-v2`
- Local v2 library: `lib/Micropulsionador_inferencing/`
- Original v1 library remains at the main project
  `lib/Micropulsionador_inferencing/`.

Both exports use the same library name, main header and generated symbols.
They must not be linked into the same firmware image. Selection is made by
running PlatformIO with this directory as the project directory:

```text
pio run -d diagnostics/ei-smoke-test/v2_project -e ei-smoke-test-v2
```

On Windows, the vendored CMSIS source tree exceeds the legacy path-length
limit when addressed through the full project path. Build and upload commands
therefore map this directory to an unused temporary drive letter and remove
the mapping immediately afterward. No source file is moved or rewritten.

The v2 export declares `EI_CLASSIFIER_RESIZE_FIT_LONGEST`. For a 1600x1200
source and a 160x160 input this means resizing to 160x120 and adding 20 black
rows above and below. It is not the center-crop `FIT_SHORTEST` pipeline used by
the v1 export.
