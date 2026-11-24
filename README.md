# ManuChain Predict

A local equipment-condition prediction prototype combining an adapted component from `ManuChain_vue`, Java device-event interfaces, and classification methods inspired by Dewen Wang's 2023 master's thesis. The current implementation is intended for research and simulation.

Offline mode reads CSV records for batch prediction. Online mode accepts mapped Java signal events and predicts when all 15 inputs for a device are complete and recent. Training, cross-validation and inference are separate steps. The default training and integration data are synthetic.

## Run locally

Python 3.12 and Node.js 20 or 22 are recommended. From the project directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_demo.py
cd frontend
pnpm install --ignore-scripts
pnpm run build
cd ..
.venv/bin/python serve.py
```

Open the local address printed by the service. `run_demo.py` generates demonstration data, evaluates the model using cross-validation, and fits a separate model for prediction. On macOS, `serve.py` and `run_demo.py` use the OpenMP library bundled with the scikit-learn wheel. On other systems, install OpenMP as required by LightGBM. The service listens only on `127.0.0.1`.

Experiment results are written to `artifacts/results.json`; `frontend/src/results.json` is a display copy updated by the script. Rebuild the frontend after regenerating results.

### Offline CSV

In **Prediction Settings**, select **Offline CSV** and upload a UTF-8 CSV containing `record_id,sensor_01,...,sensor_15`. Prediction does not require `remaining_days`, and that column is never used as a model input. The model must already be trained; uploading data does not retrain it. Missing values are supported, but missing columns, infinite values and duplicate IDs are rejected.

### Online Java simulation

Set a self-generated `MANUCHAIN_BRIDGE_TOKEN` of at least 16 characters before starting the service, and use the same environment variable for the Java process. Do not commit the token. In **Prediction Settings**, select **Online Java** and start reception. Follow `legacy/README.md` to compile and run `demo.BridgeDemo features 8000`. It sends 15 synthetic signals, not the original thesis sensor fields. A prediction is produced only when all 15 mapped signals for a device are valid, in order, and no more than 60 seconds old. Expired online results are removed from the display.

In **Interface Settings**, stop reception before editing the mapping from Java signal names to `sensor_01` through `sensor_15`. Changes apply to the current service process and reset to the startup configuration on restart. Alternatively, start with `serve.py --mapping config/local-mapping.json`. This mapping does not configure an OPC UA endpoint or establish the meaning, units or synchronization of real signals. Starting reception in the browser does not start the Java collector or write to a device.

`artifacts/model.joblib` is a trusted local training artifact. Because joblib uses deserialization, load only files you trust. The application does not accept uploaded models; local models and private data are excluded from version control.

## Relationship to the thesis

| Source | Implementation | Scope and limitations |
|---|---|---|
| `PanelGroup.vue` from Gitee `ManuChain_vue` | Retains the original four-card layout and styles, with local result labels | No calls to the old blockchain API |
| Thesis §5.2, PDF p. 54 | Iterative missing-value imputation using Bayesian ridge regression | Deterministic single imputation; not multiple posterior imputation and pooling |
| Thesis §5.3.2, PDF p. 56 | Positive class defined by `remaining_days < 7`, with outer ten-fold classification evaluation | The thesis does not specify the exact seven-day boundary; this implementation assigns it to the negative class |
| Thesis §5.3.3, PDF p. 60 | LightGBM, Extra Trees and Random Forest base learners with a logistic-regression stacking layer | Three inner folds provide meta-learner inputs; demonstration hyperparameters are not recovered historical settings |
| Thesis chapter 6 | Equipment status, classification probabilities and metrics | Does not claim to restore the entire original platform |

`legacy/` contains device-event interfaces and signal constants extracted from the supplied phone-production backend, plus a new local HTTP bridge. `legacy/opcua/` adds a read-only Eclipse Milo collector; it is manually started and its command-line entry point is restricted to a local simulator. A local integration test passed using 15 synthetic OPC UA nodes, the actual Milo client, the Java HTTP bridge and the trained demonstration model. It also checked preservation of the source timestamp. No physical PLC has been connected, and the mapping from real measurements to the model's 15 features remains unverified.

To repeat that test, first prepare the demo model using the commands above, then build the collector with JDK 8 or later and Maven. Install `asyncua` into the Python environment for this test only:

```sh
.venv/bin/python -m pip install asyncua
cd legacy/opcua
mvn package dependency:build-classpath -Dmdep.outputFile=/tmp/manuchain-milo-classpath
cd ../..
export MANUCHAIN_MILO_CLASSPATH="$PWD/legacy/opcua/target/classes:$(cat /tmp/manuchain-milo-classpath)"
.venv/bin/python tests/opcua_e2e.py
```

On macOS, if LightGBM cannot find OpenMP, set `DYLD_LIBRARY_PATH` as in `serve.py` before running the test. The test uses port 48591 on loopback, an anonymous unencrypted simulator and synthetic data; it does not validate production security or real equipment. See `legacy/README.md` for collector configuration and limitations.

The project does not implement blockchain nodes or smart contracts, federated edge training, or production scheduling optimization.

## Data and evaluation

`data/demo.csv` contains 240 newly generated synthetic records with 15 anonymous sensor features; it is not the thesis dataset. `remaining_days` is used only to create labels and is never an input feature. Imputation is inside each base-model pipeline to avoid fitting on outer or stacking-inner validation data.

Reported metrics are computed from pooled out-of-fold predictions across the outer ten folds. They are not the thesis's historical results or a simple average of fold metrics. Probabilities are not calibrated and do not constitute an industrial safety guarantee. Random cross-validation suits the independent demonstration records; repeated devices or time-series data require a suitable group or time split.

For a real training CSV, use `.venv/bin/python train.py --csv PATH --output artifacts_real`. Required columns are `record_id,sensor_01,...,sensor_15,remaining_days`. Verify the meaning and units of each feature before mapping real data; renaming columns alone does not reproduce the thesis. On macOS, see `run_demo.py` for the dynamic-library environment setup.

## References and provenance

The original front-end component comes from [ManuChain_vue](https://gitee.com/devenw/ManuChain_vue), commit `8b37e5f7a4ed447443769335c258c685511d20fe`. See `PROVENANCE.md` and `legacy/README.md` for source details and attribution limits.

The organization of device input, CSV entry and dashboards was informed by [OpenPMX](https://github.com/SahDhirendra/openpmx) and [Industrial Predictive Maintenance](https://github.com/BerkayGergin/industrial-predictive-maintenance). Their source code and models were not copied into this project. The Java OPC UA interface was checked against [Eclipse Milo](https://github.com/eclipse-milo/milo); the project uses its 0.6.x API.

The new training code, frontend integration and documentation were written with OpenAI Codex assistance under the applicant's direction. Individual contributions to the original repository remain to be verified; account ownership or commit history alone does not establish authorship of every file. No new license is asserted for the original code. The applicant should review and understand the implementation and verify contribution and redistribution claims before using the project in an application.
