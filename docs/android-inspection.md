# Android app inspection

Inspected 2026-10-07, using the user-supplied `Sanutal+Air+ventilation_26.8.18_APKPure.xapk`.

## Input and method

- Package: `be.sanutal.airventilation`.
- XAPK metadata version: `26.8.18`, version code `2608181`.
- XAPK SHA-256: `50d987d65e93f6d65ec1e5eb2e9e01a2982d7951c190bf375e9d767645ed4194`.
- Contains the base APK and ARM64, English, French, and display-density splits.
- The application uses .NET MAUI. Its application logic is managed C#, rather than primarily Android Java bytecode.
- Extracted `lib/arm64-v8a/libassembly-store.so` from the ARM64 split. Parsed its XABA assembly store, decoded XALZ/LZ4 payloads, and recovered 133 managed assemblies. The application assembly is `Sanutal.AirVentilationApp.dll` (166,912 bytes).
- Decompiled that assembly with ILSpyCmd `11.1.0.9782`, using the extracted dependency assemblies as references. Decompilation completed without reported errors. The app was not executed and no device commands were sent.

The local working directory for this investigation is `/tmp/sanutal-apk-an8ulhtb/`; recovered C# is in its `decompiled/` directory. This temporary directory is not a durable artifact. Vendor binaries and recovered source are excluded from repository changes. Package provenance/signature authenticity was not independently verified; findings apply to the supplied package.

Assembly format reference: [official .NET Android documentation](https://github.com/dotnet/android/blob/main/Documentation/project-docs/AssemblyStores.md).

## Findings

The app is a device address book plus a WebView loading the device-hosted interface.

| Decompiled location | Observed behavior | Integration consequence |
| --- | --- | --- |
| `Sanutal.AirVentilationApp.ViewModels/Main_ViewModel.cs`, `OnClickConnectDevice` | Passes the selected device's stored address to the WebView page | The app connects to an explicitly stored address |
| `Sanutal.AirVentilationApp.Pages/Device_WebViewPage.cs`, `WebSource` setter | Prepends `http://` if neither HTTP nor HTTPS is supplied, then assigns the address to the WebView source | Normal operation loads the same device web interface already inspected |
| `Sanutal.AirVentilationApp.Models/DeviceTable.cs` | Stores an auto-increment database ID, name, address, sort order, and active-device flag | Its ID is local bookkeeping, not a hardware identity |
| `Sanutal.AirVentilationApp.ViewModels/Device_DetailViewModel.cs` | Creates, edits, and deletes saved devices through SQLite | Device setup does not establish a hardware identifier |
| `Sanutal.AirVentilationApp/MauiProgram.cs` | Registers services and adjusts WebView zoom/viewport settings | Device controls remain in the device-hosted page |

Inspection of the application assembly found no dedicated HTTP API client, JSON state endpoint, speed parser, command implementation, injected control JavaScript, or mDNS/SSDP/network-scanning implementation. The positive WebView navigation path explains how controls work: the page served by the ventilation unit supplies them. This is a static finding for this version, not proof that no other firmware API or older app protocol exists.

## Effect on the integration plan

1. Keep `GET /` with narrowly parsed state scripts and `POST /upload/BN` with body `BN`; the app offers no alternative API to adopt.
2. Keep automatic Zeroconf discovery based on the actual device advertisement, plus manual address entry. Discovery is a capability observed on the device, even though this app does not implement it.
3. Do not use the app's SQLite device ID as a unique identifier. Stable hardware identity remains unresolved.
4. Retain parser fixtures and firmware compatibility checks: the server supplies the control interface, so behavior can vary independently of the app version.
5. Live write/readback verification remains outstanding; decompilation does not replace that test.
