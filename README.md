# Media Pipeline

基于 RabbitMQ 与 PostgreSQL 的长任务媒体处理流水线。系统将频道元数据抓取、文案翻译、视频下载与平台上传拆分为四个可独立运行的阶段进程，通过持久化队列传递任务、通过数据库维护处理状态。

**技术栈**：Python · RabbitMQ · PostgreSQL · Docker · Kubernetes · OpenAI API

> 本项目仅用于处理已获得授权的媒体内容。使用者需自行遵守来源平台、目标平台及内容版权方的规则。

---

## 架构

```text
                ┌──────────────┐
                │ InfoFetcher  │  频道元数据抓取（批处理入口）
                └──────┬───────┘
                       │ video_to_translate
                ┌──────▼───────┐
                │  Translator  │  调用 LLM 完成文案翻译
                └──────┬───────┘
                       │ video_to_download
                ┌──────▼───────┐
                │  Downloader  │  媒体与封面下载
                └──────┬───────┘
                       │ video_to_upload
                ┌──────▼───────┐
                │   Uploader   │  目标平台发布
                └──────────────┘

RabbitMQ      阶段间任务缓冲与解耦
PostgreSQL    视频元数据与处理状态（fetched / translated / downloaded / uploaded）
Shared Volume 媒体与封面等大文件
```

PlantUML 时序图见 [`docs/overall_flowchart.puml`](docs/overall_flowchart.puml)。

### 组件职责

| 组件 | 职责 | 外部依赖 |
|---|---|---|
| `infofetcher` | 按频道抓取视频元数据并落库，投递翻译任务 | 媒体来源平台 |
| `translator` | 调用 LLM 翻译标题与简介，投递下载任务 | OpenAI API |
| `downloader` | 下载媒体与封面至共享卷，投递上传任务 | 媒体来源平台、文件系统 |
| `uploader` | 向目标平台发布视频与封面 | 目标发布平台 |
| `adapter/` | MQ、数据库、系统调用的统一封装 | — |
| `project/template_mq_consumer` | 消费者基类：连接管理、QoS、ack/nack、重试控制 | — |

---

## 设计说明

### 阶段拆分与解耦

四个阶段分别依赖媒体来源、LLM API、本地文件系统与目标发布平台，其耗时特征、限流规则与失败模式各不相同。单进程串行执行时，任一步失败将中断整条任务；恢复时需额外判断前序步骤的完成情况，易产生重复翻译、重复下载或重复发布。

流水线因此以持久化队列作为阶段边界，以数据库作为业务状态的唯一来源。消息仅携带视频 ID 及少量处理参数，消费者从数据库读取完整上下文。该设计带来四项性质：

- **故障隔离**：外部依赖的异常被限制在单个阶段内
- **速率解耦**：队列缓冲上下游处理速度差异
- **断点恢复**：失败任务自对应阶段重新开始，无需重跑全流程
- **进度可观测**：数据库状态字段构成可查询的处理进度

### 并发策略

系统采用**阶段间流水、阶段内串行**的模式。消费者配置 `prefetch_count=1` 与手动 ack，单个 worker 在确认当前消息前不预取后续任务。

该选择源于外部约束而非实现限制：翻译受 API 速率与配额限制，下载受来源平台限速与出口带宽约束，上传受目标平台风控与本地磁盘 I/O 约束。在当前任务规模下，稳定性与可预测性的价值高于峰值吞吐。

下载阶段另设请求间隔与带宽上限；翻译与上传成功后进行节流等待，以降低对上游服务与本地资源的瞬时压力。

### 失败处理

消息持久化（`durable` + `persistent`）确保 broker 重启后任务不丢失。消费失败的消息重新入队等待重试。

翻译与下载属于可重复执行的操作：重复翻译至多产生新的文本结果，下载支持断点续传。**上传则具有外部副作用**——命令返回失败不等同于平台未接收，视频可能已发布成功而仅在返回前发生网络中断。当前系统不具备以下幂等保障：

- 未向目标平台传递业务幂等键
- 未持久化平台返回的视频 ID
- 重试前未查询平台确认同一视频是否已存在
- 本地状态写入与平台发布操作不在同一事务内

在缺乏上述保障的前提下，对有副作用操作执行自动重试的风险高于任务失败本身。相关改造见[已知限制](#已知限制与改进计划)。

### 连接保活

下载与上传为长耗时阻塞操作，期间主线程不处理 I/O 事件，broker 将判定连接超时并断开（`StreamLostError`）。消费者基类启动独立守护线程，每 30 秒调用 `process_data_events()` 维持连接活性。

---

## 部署

### 单镜像多角色

`Dockerfile` 构建单一应用镜像，`entrypoint.sh` 依据 `PROCESS_TYPE` 启动对应角色进程。三个消费者共享依赖与基础代码，单镜像可避免重复构建、镜像体积差异与版本漂移；Kubernetes Deployment 仍可按角色分别配置环境变量、资源限额与副本数。

元数据抓取当前为按频道触发的批处理入口，尚未纳入 `PROCESS_TYPE`。

### Kubernetes 清单

```text
k8s/pv.yaml / pvc.yaml               共享媒体卷
k8s/postgres-deployment.yaml + service
k8s/rabbitmq-deployment.yaml + service
k8s/translator-deployment.yaml       应用角色示例
k8s/secrets.example.yaml             Secret 模板
```

### 配置与密钥

应用不在代码中保存凭证。OpenAI、PostgreSQL、RabbitMQ 凭证均经环境变量注入，示例见 [`.env.example`](.env.example)；本地 `.env` 已被 Git 忽略。

Kubernetes 侧使用名为 `media-pipeline-secrets` 的 Secret：

```bash
cp k8s/secrets.example.yaml k8s/secrets.yaml
# 仅在本地编辑，禁止提交
kubectl apply -f k8s/secrets.yaml
```

目标平台 Cookie 经只读文件或 Secret 挂载，路径由 `BILIUP_COOKIES_PATH` 指定。Cookie 文件不得复制进镜像或提交至版本库。

### 运行

```bash
PROCESS_TYPE=translator  ./entrypoint.sh
PROCESS_TYPE=downloader  ./entrypoint.sh
PROCESS_TYPE=uploader    ./entrypoint.sh
```

| 环境变量 | 用途 |
|---|---|
| `OPENAI_API_KEY` | 翻译阶段访问 LLM API |
| `POSTGRES_*` | PostgreSQL 连接配置 |
| `MQ_*` | RabbitMQ 连接配置 |
| `MEDIA_BASE_DIR` | 共享媒体目录 |
| `BILIUP_COOKIES_PATH` | 目标平台 Cookie 文件路径 |

---

## 已知限制与改进计划

当前实现存在以下缺陷，均已定位到具体代码位置：

| # | 问题 | 影响 |
|---|---|---|
| 1 | 重试计数写入解析后的内存对象，而 `basic_nack(requeue=True)` 重投的是原始消息体 | 计数始终为初始值，死信队列不可达，形成无限重试 |
| 2 | `uploader` 未覆盖基类失败策略，走默认自动重投 | 与本文档「失败处理」一节描述的设计意图不符 |
| 3 | 未持久化目标平台返回的视频 ID | 缺少人工恢复与幂等校验的依据 |
| 4 | 日志为非结构化文本，无阶段耗时与任务关联 | 难以按 `video_id` 追踪全链路 |

改进顺序：

1. 失败时重新发布携带 `retries + 1` 的新消息并确认原消息，使计数真正生效
2. `uploader` 覆盖失败策略：首次失败即投递人工确认队列并保留本地文件
3. 持久化平台返回的视频 ID，作为后续幂等检查的依据
4. 引入结构化日志，按阶段记录耗时、结果与 `video_id`
