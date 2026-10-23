# AgentCompass 共享数据准备状态

核对日期：2026-10-23。原生版本固定为 `d2c3e148902e948db3270fa34b2198fb1b10beb7`，
运行镜像 digest 为 `61e6f2b7c3e92d51981bcfd48b159964c5a40519c5d0c6b06166a2897ed324f2`。
这里只盘点当前 adapter 有结果归一化实现的 10 个 benchmark；registry 中其他 ID 不算已接入。

## 原始数据、评分资产与依赖

表中的相对路径以原生 `data_dir` 为根；“未发现”限定于本次检查的 GPFS AgentCompass 数据
目录和用户数据缓存，不代表集群其他所有者的存储也不存在。镜像已实际检查，具有
`datasets`、`pyarrow`、`openai`、`httpx`、`minisweagent`、`swebench`、`h5py`、`numpy`、
`scipy`、`sympy` 和 Docker Python SDK；**没有 matplotlib**。SDK 存在不等于 Docker daemon
或远程 sandbox 已配置。

| Benchmark | 原始数据 / 固定版本获取方式 | 评分资产及运行依赖 | 当前状态 |
| --- | --- | --- | --- |
| `special_pattern_check` | `dataset_dir/<version>.jsonl`；仓库提供单条 `gate4.jsonl` | 镜像内 analyzer；`openai_chat`，不需要 judge | diagnostic 数据齐备，部署方已验收 GLM/Landing/reward；不代表真实大集合 |
| `scicode` | `scicode/problems_dev.jsonl`、`problems_test.jsonl`、官方 `test_data.h5`；固定源码与官方 SciCode ZIP | 固定版本提示模板及 3 个预填代码文件；h5py/numpy/scipy/sympy；sample 80 另需 matplotlib | **全量原始/评分数据已发布**；validation 15 条原生目录已生成；本轮验收 naive/host_process，sample 80 的镜像依赖未齐备 |
| `sgi_deep_research` | `sgi_deep_research/test.jsonl`；官方同名 ZIP | 内置 LLM judge 提示；显式独立 judge 配置；搜索 harness 还需相应外部检索服务 | GPFS 已有 318 行，字段与固定 loader 相符；来源版本、judge 路由与共享发布未验收，不列为可直接运行 |
| `browsecomp` | `browsecomp/browse_comp_test_set.jsonl`；官方 browsecomp ZIP | ground truth + 内置 LLM judge；搜索 harness/检索服务；显式 judge 模型 | 本次目录未发现原始数据，judge/搜索配置未验收 |
| `deepsearchqa` | `deepsearchqa/deepsearchqa.jsonl`；官方 deepsearchqa ZIP | 原始答案及 DeepSearchQA scorer；显式 judge；搜索服务 | 本次目录未发现数据，评分模型/工具链未验收 |
| `frontierscience` | `frontierscience/test.jsonl`；官方 frontierscience ZIP | olympiad 答案或 research rubric；对应 judge 配置 | 本次目录未发现数据；两种评分分支只有 schema 归一化测试 |
| `hle` | `hle/test_text_only_500.jsonl`（llm）或 `test.jsonl`（vlm）；官方 hle ZIP；VLM 还需图像内容 | 内置 LLM judge、ground truth；显式 judge 与所选 harness 依赖 | 本次目录未发现数据；多模态与 judge 未验收 |
| `hle_verified` | HF `skylenage-ai/HLE-Verified` 的 `train`，缓存于 `hle_verified/` | datasets/pyarrow、ground truth、内置 LLM judge | 本次未发现缓存；原生 loader 未固定 HF revision，发布前还需记录 snapshot；judge 未验收 |
| `sealqa` | HF `vtllms/sealqa`，revision `267b8197ae75680ee0db180c4c2e96bd4e1001b4`；可用 `dataset_path` 指向本地 Parquet | 官方 A/B/C judge；LongSeal 还需记录中的文档集合；datasets/pyarrow | 本次未发现数据，judge/文档集合未验收 |
| `swebench_verified` | `swe_bench_verified/` 的官方 ZIP，或 HF `SWE-bench/SWE-bench_Verified` test | 每实例仓库/base commit、test patch、SWE-bench setup/install/eval；独立 inference/evaluation 环境或 prebaked 镜像 | 镜像 Python extras 已安装；原始数据、实例环境未准备。默认 host_process 白名单不等于已提供隔离 SWE-bench 运行能力 |

官方 ZIP 基址来自该 revision 的 benchmark 源码，而非最新接口。上述 judge 型 benchmark
并不会自动继承主模型的 session URL；必须单独核对其 `judge_model` 路由及轨迹归属后才能
标为 ready。本次 SciCode naive 没有独立 judge/辅助模型，子步骤共用主模型的 session Gateway。

## SciCode 发布凭据

部署目录为 GPFS 上独立的 `agentcompass-data/d2c3e148`，与旧私有目录和 results 分离。
旧 HDF5 原件保持不变；发布副本经过以下检查：

- 官方归档 ETag：`0D38CB6A4743BA553AF3D9A406A826D9-38`。通过 HTTP Range 读取 ZIP
  central directory，未重复下载整个 391,145,703 字节归档。
- HDF5 大小 `1,049,345,865` 字节，完整文件 CRC32 `9fe0ae53`，与官方 ZIP 条目一致。
- HDF5 SHA256：`48b0272a88b17dbd29777c217e1b4fb2b019b92e11cc2add847409db9541b890`。
- 与固定问题定义逐项核对：338 个评分子题组、1,082 个测试组；3 个官方预填子题不计入评分组。
- dev/test 问题定义的大小和 CRC32 与官方 ZIP 一致。部分模板/预填代码在 ZIP 与固定源码间
  有差异，因此发布时采用**固定 revision 的包内文件**，并在元数据记录各文件 SHA256。
- 固定镜像 RJob 内完成验证与原生 loader 调用，生成 15 个 validation ID；没有使用 fixture。
- 共享目录 `0755`、数据与清单 `0644`；访问者仍需由平台授予对应 GPFS fileset 访问权限。

`manifests/scicode-validation.metadata.json` 保存 native revision、源文件/资产哈希、原生 ID、
任务清单哈希及 HDF5 结构统计。部署者重复运行 `--prepare` 会复核并复用完整数据；已有文件
与固定版本不一致时报错，不覆盖现有目录。需要更新版本时发布到新目录。

本轮已实际执行首次准备和再次复核两个固定镜像 RJob，均成功；第二次返回
`reused_complete_data=true`，两次清单 SHA256 均为
`1bba7fd1de545bdb55e4ca9a35951bdfe9c1799f473fb2b2f348922e249db5c0`。
无现有 HDF5 时的整包下载分支未在本轮执行；本轮使用经官方归档核验的 GPFS 现有原件。

日常使用者通过 `--catalog` 选择任务，只读取小型共享清单及其元数据，使用标准 Python 即可；
不读取全部 HDF5、不下载、不安装原生依赖、不创建数据库或模型 session。真实评分始终由
固定镜像读取共享 HDF5，生成代码和 evaluator workspace 均写入各 session 的 results。

## 验收边界

SciCode validation `1`、`19` 已在 v2 基线上用共享数据真实通过，逐条比对见 README 的验收记录。
该结论只覆盖这两个 sample 和 naive/host_process 组合，不是全量成绩，也不代表其他
benchmark、独立 judge 或 test sample 80 的依赖已就绪。
