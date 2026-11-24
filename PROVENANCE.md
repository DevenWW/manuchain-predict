# Source provenance

Original repository: https://gitee.com/devenw/ManuChain_vue

Snapshot: 8b37e5f7a4ed447443769335c258c685511d20fe, master, downloaded 23 November 2026.

Adapted source file: src/views/blockchain/BlockChain_static/admin/components/PanelGroup.vue.

Retained: Vue 2 component layout, panel structure, styles and count-to display pattern.

Changed: four labels, local result properties, removal of obsolete API calls and click handlers; original author attribution retained here and in the component comment. Vue and related dependencies remain third-party software with their respective licenses.

The original repository has four commits attributed to DevenW in July and October 2020. It exposes no root LICENSE file. The underlying administration template's original attribution and the applicant's module-level contributions are not yet verified. No blanket claim of independent authorship or new license is made.

Method source: Dewen Wang's 2023 master's thesis, supplied locally. PDF pages54,56,60 describe Bayesian ridge imputation, the binary tooling-life classification, and LR-stacking. The PDF and its historical results have not been republished in this project.

New AI-assisted code: train.py, model_runtime.py, online_bridge.py, server.py, run_demo.py, serve.py, frontend/src/App.vue, frontend/src/main.js, build configuration, tests and documentation. These are new implementations written with OpenAI Codex for the current project; no historical Python source was recovered. The synthetic data generator and all generated metrics are new and illustrative.

The `legacy/` directory includes Java event and PLC signal files extracted from the user-provided `phone（manuchain）.rar` backend, alongside a new AI-assisted conversion and local HTTP event bridge. The bridge has been tested with synthetic events, not with live PLC hardware. See `legacy/README.md` for precise provenance. The `deadline.7z` archive contains Java, Solidity and device examples but no recovered thesis model-training code; its asset contract is an asset-transfer example, not the thesis voting contract.

The AI-assisted `legacy/opcua/` module uses the Eclipse Milo SDK to read OPC UA values. Its read and connection patterns were checked against the archived Milo sources and the project's public examples. The interface and dashboard organization also draw on the public descriptions of OpenPMX and Industrial Predictive Maintenance, linked in the README; no source code was copied from those projects. This addition is not evidence of historical authorship or validation against a physical PLC. See `legacy/README.md` for the exact test scope.

Excluded from the assembled project: legacy login/authentication modules, camera integrations, old service endpoints, unnecessary maps/assets and application configuration. The original local clone remains unchanged.

Not implemented: original data reconstruction, multiple posterior imputation, blockchain consensus, smart-contract deployment, edge federation, hardware integration and real-time scheduling optimization.
