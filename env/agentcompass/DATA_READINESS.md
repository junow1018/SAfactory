# AgentCompass 共享数据准备与运行支持状态

固定原生版本 `d2c3e148902e948db3270fa34b2198fb1b10beb7`，共 28 个 benchmark。四类状态分别统计，
任一项完成不代替其他项：

- **数据**：完整原生数据树已发布到共享挂载，`.published/<id>.json` 逐文件校验通过（内容、缺失、
  未记录文件均检查），原生 loader 生成的目录在 `manifests/v2/`。
- **adapter**：runner 能为该组合构造原生命令并把原生结果转换为 SAfactory reward。
- **依赖**：宿主侧依赖在 host-extras 镜像就绪（原生 `dependency_spec` 通过）；sandbox、外部
  服务、凭据另列。
- **真实验收**：在当前 v2 基线上以标准 Launcher 跑通最小真实任务，并回查原生结果、Landing
  轨迹与 reward。

“需搜索凭据”指原生推荐 harness `naive_search_agent`/`researchharness` 所需的 Serper/Jina
（/MinerU）密钥；“需 sandbox”指原生只支持 docker/daytona/modal，或其完整官方组合需要它们。
当前部署没有可复用的 sandbox，这些组合均为运行依赖阻塞。

## 状态表

| Benchmark | 数据 | 原生任务数（catalog） | adapter | 运行依赖 | 真实验收（v2） |
| --- | --- | --- | --- | --- | --- |
| scicode | 完整 | validation 15 / test 65 | ✅ scicode_tool_use naive | 就绪（host-extras 含 matplotlib） | ✅ validation 1、19 |
| special_pattern_check | 需部署方提供原生数据（`--source`） | — | ✅ | 就绪 | ❌（仅旧基线单条） |
| sealqa | 完整（HF `267b8197`） | seal_0 111 / seal_hard 254 / longseal 254 | ✅ | longseal+openai_chat 就绪；seal_0/hard 需搜索凭据 | ❌ |
| browsecomp | 完整 | 1266 | ✅ | 需搜索凭据 | ❌ |
| browsecomp_zh | 完整 | 289 | ✅ | 需搜索凭据 | ❌ |
| deepsearchqa | 完整 | 900 | ✅ | 需搜索凭据 | ❌ |
| frontierscience | 完整 | 160 | ✅ | 需搜索凭据 | ❌ |
| sgi_deep_research | 完整 | 318 | ✅ | 需搜索凭据 | ❌ |
| hle | 完整（含图片） | llm 500 / multimodal 2500 | ✅ 仅 llm | 需搜索凭据；multimodal 需 VL judge | ❌ |
| gaia | 完整（含附件） | llm 103 / multimodal 165 | ✅ 仅 llm | 需搜索凭据 | ❌ |
| hle_verified | 完整（HF `0bc83643` 获取时快照） | llm 2158 / multimodal 2500 | 仅结果转换；runner 未接数据路径 | 需搜索凭据 | ❌ |
| xbench_deepsearch | 完整（GitHub `17c56219`） | 2505 100 / 2510 100 | 仅结果转换；runner 未接数据路径 | 需搜索凭据 | ❌ |
| deepresearch_bench | 完整（GitHub `main` 获取时 commit） | 100 | ❌ | 需搜索凭据；FACT 需 Jina | ❌ |
| screenspot | 完整（含图片） | 1272 | ❌ | 需 VL 策略模型 | ❌ |
| swebench_verified | 完整 | 500 | 仅结果转换 | 需 sandbox 或宿主 conda | ❌ |
| swebench_multilingual | 完整（HF 获取时快照） | 300 | ❌ | 需 sandbox | ❌ |
| swebench_pro | 完整（HF 快照 + run_scripts commit） | 642 | ❌ | 需 sandbox | ❌ |
| deepswe | 完整（固定 SHA） | 113 | ❌ | 需 sandbox | ❌ |
| terminal_bench_2 | 完整（git 获取时 commit） | 89 | ❌ | 需 sandbox | ❌ |
| terminal_bench_2_1 | 完整（原生 harbor download） | 89 | ❌ | 需 sandbox | ❌ |
| terminal_bench_2_verified | 完整（HF git+LFS） | 89 | ❌ | 需 sandbox | ❌ |
| skillsbench | 需部署方提供原生数据（`--source`） | — | ❌ | 需 Docker | ❌ |
| wildclawbench | 完整（MD5 固定，15.4 GB） | 60 | ❌ | 需 Docker、BRAVE 密钥 | ❌ |
| pinchbench | 完整（tag v1.1.0） | 23 | ❌ | 需 sandbox | ❌ |
| gdpval_ac | 完整（HF 获取时快照 + baseline） | 220 | ❌ | 需 sandbox、judge harness | ❌ |
| researchclawbench | 完整（GitHub `main` 获取时 commit） | 40 | ❌ | 需搜索/MinerU 凭据、多模态 judge | ❌ |
| frontier_engineering | 完整（固定 SHA + 外部资产） | v1 48 / non_gpu 44 / filtered 38 / lite 10 | ❌ | openevolve 就绪；部分任务需 GPU/Docker | ❌ |
| taubench | 完整（MD5 固定） | 375 | ❌ | tau2 就绪；需用户模拟器/judge/embedding 路由 | ❌ |

合计：数据完整 26、需部署方提供数据 2；adapter 可端到端运行 10、仅结果转换 3（hle_verified、xbench_deepsearch、swebench_verified）、未接入 15；
v2 真实验收 1（SciCode）。

## 资产说明

- `.published/<id>.json` 记录来源、实际获取版本（模块未固定版本时为本次获取的 HF sha /
  git commit）、归档 SHA256 和逐文件 SHA256。datasets/HF 运行锁文件（`*.lock`）不计入资产；
  GDPVal 早期记录误收的 3 个锁文件条目已通过 `--reconcile` 删除并在 `amendments` 留痕。
- SciCode、SealQA 为既有文件接管：SciCode 按固定 HDF5 大小/SHA256 与固定包内定义逐项比对，
  SealQA 按固定 HF revision 的逐文件 LFS SHA256 比对，均未重新下载。旧 `manifests/*.jsonl`
  保留，新目录在 `manifests/v2/`。
- 任务镜像不放入 GPFS：固定 recipe 引用的 12 个镜像在 Docker Hub 可用并已记录 digest，尚未
  镜像到内部 registry；按任务变化的镜像（swebench `sweb.eval.*`、sweap、terminal-bench、
  deepswe、skillsbench）需从已发布数据枚举。
