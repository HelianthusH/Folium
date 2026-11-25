# Third-party notices for Folium v0.1.0

The accompanying `licenses/` directory contains the license texts referenced below. Package metadata and upstream project notices remain authoritative for each component. This inventory covers the bundled UF2 firmware, Windows portable application, and bilingual offline model. The original Folium material is licensed separately in `LICENSE.md`.

## Firmware image

The UF2 is built with Zephyr 4.2.0 and its board and driver modules. Zephyr's project license is Apache-2.0. Zephyr can include separately licensed components; its source tree and SPDX file headers are the source of the per-file notices. The build also uses Mbed TLS, available under Apache-2.0 or GPL-2.0-or-later; this distribution selects Apache-2.0. Sources: <https://github.com/zephyrproject-rtos/zephyr/tree/v4.2.0>, <https://github.com/Mbed-TLS/mbedtls>. See `licenses/Apache-2.0.txt`.

## Windows portable application

| Component | Version | License | Source |
| --- | --- | --- | --- |
| Python runtime | bundled by PyInstaller | PSF-2.0 and bundled standard-library notices | <https://www.python.org/psf/license/> |
| PyInstaller bootloader | bundled | GPL-2.0-or-later with its bootloader exception | <https://pyinstaller.org/en/stable/license.html> |
| pyserial | 3.5 | BSD-3-Clause | <https://github.com/pyserial/pyserial> |
| bleak | 1.1.1 | MIT | <https://github.com/hbldh/bleak> |
| sherpa-onnx and sherpa-onnx-core | 1.12.30 | Apache-2.0 | <https://github.com/k2-fsa/sherpa-onnx> |
| NumPy | 1.26.4 | BSD-3-Clause, with bundled third-party notices | <https://github.com/numpy/numpy> |
| pywin32 | 311 | PSF-2.0 | <https://github.com/mhammond/pywin32> |
| uiautomation | 2.0.29 | Apache-2.0 | <https://github.com/yinkaisheng/Python-UIAutomation-for-Windows> |
| comtypes | 1.4.11 | MIT | <https://github.com/enthought/comtypes> |
| psutil | 7.0.0 | BSD-3-Clause | <https://github.com/giampaolo/psutil> |
| pywinpty | 2.0.15 | MIT | <https://github.com/andfoy/pywinpty> |
| pystray | 0.19.5 | LGPL-3.0-only | <https://github.com/moses-palmer/pystray> |
| Pillow | 11.3.0 | MIT-CMU | <https://github.com/python-pillow/Pillow> |
| WinRT Python bindings | transitive dependencies of bleak | MIT | <https://github.com/pywinrt/pywinrt> |
| Tcl/Tk | bundled with Python | Tcl/Tk license | <https://www.tcl.tk/software/tcltk/license.html> |

`pystray` is shipped unmodified as a Python module in the application bundle. Its source is available from the upstream link above and its LGPL-3.0 text is supplied. Third-party files under `_internal/` retain their original notices, including `_tk_data/license.terms` and package `dist-info` licenses. The portable application's executable is a packaging of the original MIT application with these independent components.

## Offline speech model

The included `decoder-epoch-99-avg-1.int8.onnx`, `encoder-epoch-99-avg-1.int8.onnx`, `joiner-epoch-99-avg-1.int8.onnx`, `tokens.txt`, and test audio derive from `csukuangfj/k2fsa-zipformer-bilingual-zh-en-t`, model revision `e2382758de9a0219b4efe682b95af30b399db3b8`. Its model card declares `license: apache-2.0`, and identifies `pfluo/k2fsa-zipformer-chinese-english-mixed` as its original source; that model card also declares Apache-2.0. Sources: <https://huggingface.co/csukuangfj/k2fsa-zipformer-bilingual-zh-en-t/tree/e2382758de9a0219b4efe682b95af30b399db3b8> and <https://huggingface.co/pfluo/k2fsa-zipformer-chinese-english-mixed>. License text: `licenses/Apache-2.0.txt`. Folium does not claim ownership of the model or training data.

## License text provenance

The SPDX license texts in `licenses/` were retrieved from <https://github.com/spdx/license-list-data/tree/main/text>. The PyInstaller exception and Tcl/Tk license are provided separately in the portable app's `licenses/` directory. Upstream component names, versions and links above let recipients locate source and report corrections.
