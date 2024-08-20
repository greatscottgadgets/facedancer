# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## [Unreleased]
-->

## [3.0.2] - 2024-08-20
### Changed
* Added support for Cynthion on Windows.
* Update docs to reflect current status of GreatFET support on Windows.

## [3.0.1] - 2024-08-19
### Changed
* USBProxy now auto-detaches kernel drivers for the device being proxied.
* Updated documentation with current status of Facedancer support on Windows.

### Fixed
* Clarify the explanatory text for endpoint numbers in the app template. (tx @salcho!)
* Shutting down Facedancer proxy devices could result in a `LIBUSB_ERROR_BUSY` (tx @mipek!)
* Facedancer devices would be incorrectly identified as `goodfet` when `/dev/ttyUSB0` exists on the host device.
* Fixed ambiguous documentation terminology to always use one of "Target Host", "Control Host".


## [3.0.0] - 2024-06-18
### Added
- Facedancer documentation has been updated and can be found at: [https://facedancer.readthedocs.io](https://facedancer.readthedocs.io)
- A new backend has been added for the Great Scott Gadgets Cynthion.
- Emulations can now set USB device speed on supported boards.

### Changed
- The Facedancer core API has been rewritten. See the Facedancer documentation for details.
- Some legacy applets have been replaced with new examples based on the modern Facedancer core:
  - `facedancer-ftdi.py` => `ftdi-echo.py`
  - `facedancer-keyboard.py` => `rubber-ducky.py`
  - `facedancer-umass.py`    => `mass-storage.py`

### Fixed
- 64bit LBA support has been added to the `mass-storage.py` example. (Tx @shutingrz!)

### Removed
- The legacy Facedancer core has been removed. If you're using scripts or training materials that depend on features or APIs removed in `v3.0.x` please use `v2.9.x`.
- All legacy applets not ported to the modern Facedancer core have been removed.


## [2.9.0] - 2024-02-09

This release is intended as a reference point for anyone who has scripts, training materials etc. that are based on Facedancer `v2.x` features or API's that have been deprecated from `v3` onwards.

Any future bug-fixes or backports to Facedancer `2.9.x` should use the [`v2.9.x branch`](https://github.com/greatscottgadgets/facedancer/tree/v2.9.x) as the starting point for forks or PR's.

### Deprecated
- The current Facedancer core will be supersed by the implementation in `future/` with the `v3.0` release.


[Unreleased]: https://github.com/greatscottgadgets/facedancer/compare/3.0.2...HEAD
[3.0.2]: https://github.com/greatscottgadgets/facedancer/compare/3.0.1...3.0.2
[3.0.1]: https://github.com/greatscottgadgets/facedancer/compare/3.0.0...3.0.1
[3.0.0]: https://github.com/greatscottgadgets/facedancer/compare/2.9.0...3.0.0
[2.9.0]: https://github.com/greatscottgadgets/facedancer/releases/tag/2.9.0
