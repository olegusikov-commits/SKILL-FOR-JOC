# C++ standard

Detect the language standard (`/std:c++17`, `-std=c++20`, `CMAKE_CXX_STANDARD`) and the
toolchain (MSVC on Windows is likely). Use modern C++ within that standard.

## Resource and memory safety
- **RAII for everything**: memory, handles, locks, DB connections, files.
- No raw `new`/`delete` in application code: `std::make_unique`, `std::make_shared` (shared only
  when ownership is really shared), containers.
- Raw pointers/references are **non-owning** only. Express ownership in types.
- Rule of zero; if you must manage a resource, rule of five.
- Avoid undefined behavior: bounds (`at()` or checked access in non-hot paths), uninitialized
  variables, signed overflow, dangling references/`string_view`, iterator invalidation.

## Code
- `const` correctness everywhere; `constexpr` where possible; `enum class`; `[[nodiscard]]` on
  functions whose result must be checked.
- `std::string_view` / `std::span` for non-owning parameters; pass small types by value, large
  by `const&`.
- No macros for constants or functions (`constexpr`, templates, inline functions instead).
- Headers: include what you use, forward-declare when possible, `#pragma once` or guards per project.
- Error handling per project policy: exceptions **or** error codes / `std::optional` /
  `std::expected` (C++23) — do not mix styles within a module. Never ignore a returned error.
- Concurrency: `std::scoped_lock`, `std::atomic`, no data races; document thread-safety of
  every class used across threads.

## Windows / DLL boundaries
- Do not pass STL types or allocate/free across DLL boundaries built with different runtimes;
  use C-style or stable ABI interfaces at module boundaries.
- Wide/narrow strings: be explicit (UTF-8 vs UTF-16 `wchar_t`) — especially for Hebrew text.

## Build hygiene
Warnings high (`/W4` or `-Wall -Wextra`), warnings as errors for new code if the project allows;
static analysis (MSVC /analyze, clang-tidy) per project; sanitizers in test builds where possible.

## Tests
GoogleTest / Catch2 / project framework; test public behavior; inject dependencies via
interfaces or templates for testability.
