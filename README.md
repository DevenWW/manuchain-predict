# ManuChain Predict

本地设备状态预测项目，整合 `ManuChain_vue` 的真实前端组件、原Java事件接口与王德文2023年硕士论文中的部分分类方法。当前版本用于研究和模拟联调。

离线模式读取CSV并批量预测；在线模式通过Java事件桥接收同一设备的15项已映射信号，完整且新鲜时调用同一Python模型。训练、交叉验证和预测是独立步骤。默认训练和联调数据为合成数据。

## 本地运行

在本目录执行。建议 Python 3.12 和 Node.js 20 或22。

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

浏览器访问终端给出的本机地址。`run_demo.py` 生成演示数据、计算交叉验证结果并另行拟合预测模型。`serve.py` 和 `run_demo.py` 在 macOS 上使用 scikit-learn wheel 自带的 OpenMP 库；其他环境按 LightGBM 官方安装要求安装 OpenMP。服务仅监听127.0.0.1。

`artifacts/results.json` 保存本次实验结果；`frontend/src/results.json` 是运行脚本同步的展示副本。重新运行实验后重新构建前端即可更新。

### 离线 CSV

浏览器选择“离线 CSV”，上传含 `record_id,sensor_01,...,sensor_15` 的UTF-8 CSV。预测无需 `remaining_days`，即使文件包含该列也不会作为模型输入。模型先在本机训练；新输入不会触发重新训练。支持空值，但拒绝缺列、无穷值和重复ID。

### 在线 Java 模拟联调

在启动服务的终端设置一个自己生成的至少16字符的 `MANUCHAIN_BRIDGE_TOKEN`，Java进程使用相同环境变量；不要将token写入仓库。打开页面的“在线 Java”，点击启动，再按 `legacy/README.md` 编译和运行 `demo.BridgeDemo features 8000`。示例发送15个合成信号；它们并非论文真实传感器字段。服务器按设备分别累计信号，同一设备15个信号都在60秒内、数值合法且时间顺序有效才预测；过期结果从在线视图移除。停止后不再接收。

在“接口设置”页面可更改Java信号名与 `sensor_01` 至 `sensor_15` 的映射：先停止在线接收，修改并保存，保存后立即对本次服务进程生效；重启后恢复启动配置。也可用 `serve.py --mapping config/local-mapping.json` 在启动时加载映射。此设置只对应桥接信号名，不配置 OPC UA 地址或节点，也不能证实单位、时间同步或数据含义；真实字段需按设备记录和模型训练数据逐项核实。页面的“启动接收”不会自动启动Java采集程序，也不会写入设备。

`artifacts/model.joblib` 为本机可信训练产物，使用joblib反序列化，仅可加载自己信任的本地文件，不能接收外部上传的模型；真实训练数据和本机模型已列入忽略规则。

## 代码与论文的对应关系

| 来源 | 本项目实现 | 边界 |
|---|---|---|
| Gitee `ManuChain_vue` 的 PanelGroup.vue | 保留原四卡片组件的布局和样式，改为记录数、风险数、验证折数和基学习器数 | 新写入本地结果，不再请求旧区块链API |
| 硕论5.2节，PDF54页 | 贝叶斯岭回归的迭代缺失值填补 | 当前为确定性单次填补，不声称实现多次后验抽样及合并 |
| 硕论5.3.2节，PDF56页 | `remaining_days < 7` 为正类，外层十折分类评估 | 论文未明确等于7天的边界；新项目明确归为负类 |
| 硕论5.3.3节，PDF60页 | LightGBM、Extra Trees、Random Forest及逻辑回归二层集成 | 内层三折生成元学习器训练输入；当前超参数为演示选择，不是找回的历史参数 |
| 硕论第六章 | 设备状态查看、分类概率和指标展示 | 没有声称恢复原平台全部功能 |

没有接入真实设备、联盟链节点或智能合约，也没有实现分布式边缘训练或生产排程优化。这些不属于当前已经验证的功能。

`legacy/` 包含从手机产线后端提取的原设备事件接口和信号常量，以及新写的本地HTTP桥；桥和Python已用模拟信号联调。`legacy/opcua/` 另外提供使用 Eclipse Milo 的只读 OPC UA 采集器，真实依赖编译和单元测试已通过，但完整 OPC UA 模拟服务器联调尚未通过。命令行采集器目前仅允许连接本机模拟服务，不会由网页自动启动。真实字段到模型15个特征的对应关系尚未核实，实际PLC服务没有接入。运行与验证细节见 `legacy/README.md`。

## 同类项目参考

参考 [OpenPMX](https://github.com/SahDhirendra/openpmx) 的设备接入、CSV入口和仪表板分工，以及 [Industrial Predictive Maintenance](https://github.com/BerkayGergin/industrial-predictive-maintenance) 的 OPC UA 采集、时间快照和展示分层；本项目独立实现界面与数据桥，未复制这两个项目的源码，也未引入其模型。参考 [Eclipse Milo 官方示例](https://github.com/eclipse-milo/milo) 核对 Java OPC UA 接口；不同版本的接口有差异，具体依赖和验证范围见 `legacy/README.md`。

## 数据与评价

`data/demo.csv` 是新生成的240条合成独立记录、15个匿名传感特征，不是论文原数据。`remaining_days` 仅用于生成标签，绝不输入模型。缺失值填补器置于每一个基础模型的Pipeline内，避免外层及stacking内层的验证数据参与填补器拟合。

实验指标来自外层十折的折外预测合并计算，不是各折指标的简单平均，也不是论文表格中的原始实验结果。概率未经校准，不能解释为工业安全保证。随机交叉验证只适合当前独立演示记录；真实重复设备或时序数据需要另行设计设备分组或时间切分。

真实CSV入口为 `.venv/bin/python train.py --csv 路径 --output artifacts_real`，字段为 `record_id,sensor_01,...,sensor_15,remaining_days`。匿名特征须先与真实字段逐项映射；不能仅改列名后默认得到论文复现。macOS可参照 `run_demo.py` 的动态库环境设置运行。

## 来源与个人贡献

旧组件来自 `https://gitee.com/devenw/ManuChain_vue`，固定提交 `8b37e5f7a4ed447443769335c258c685511d20fe`。原仓库副本保留在上级 `source_repositories/ManuChain_vue`，未改写历史或推送远端。

新增训练代码、前端整合及本文档由OpenAI Codex根据用户授权辅助编写。原始仓库中的个人模块贡献仍待用户逐项确认；账号和提交记录不能单独证明每个文件均为本人独立创作。当前没有增加对原代码的开源许可声明。

提交申请前，应由申请人阅读、运行并理解新增代码，确认自己的实际贡献表述，以及原组件和第三方依赖的署名和再分发条件。这里不把新实现倒写成2023年已完成的代码。
