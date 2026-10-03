# Media Pipeline

一个由 RabbitMQ 和 PostgreSQL 驱动的长任务媒体流水线。系统依次完成频道元数据抓取、文案翻译、视频下载和目标平台上传，并将每个阶段拆成可独立运行的进程。

> 本项目仅用于处理已获得授权的媒体内容。使用者需要自行遵守来源平台、目标平台以及内容版权方的规则。

## 架构

```text
InfoFetcher
    │ video_to_translate
    ▼
Translator
    │ video_to_download
    ▼
Downloader
    │ video_to_upload
    ▼
Uploader

RabbitMQ：任务缓冲与阶段解耦
PostgreSQL：视频元数据与处理状态
Shared Volume：视频、封面等大文件
```

PlantUML 时序图见 [`docs/overall_flowchart.puml`](docs/overall_flowchart.puml)。

## 为什么这样设计

### 为什么用消息队列拆成四个阶段，而不是一个脚本跑到底

四个阶段分别依赖媒体来源、OpenAI API、本地文件系统和目标发布平台，耗时、限流规则及失败模式都不同。若使用一个脚本从头执行到尾，任意一步失败都会中断整条任务，恢复时也容易重复翻译、重复下载或重复上传。

RabbitMQ 将阶段边界变成持久化任务队列，PostgreSQL 保存完整业务状态，消息只携带视频 ID 和处理所需的少量信息。这样可以隔离外部依赖、缓冲上下游速度差异，并让失败任务从对应阶段恢复，而不是重跑整个流程。

### 为什么阶段内串行而不是并发

系统采用“阶段间流水、阶段内串行”的模式。消费者设置 `prefetch_count=1`，单个 worker 在确认当前消息前不会继续预取任务。翻译、下载和上传都受外部服务限流、账号风控、网络带宽及磁盘 I/O 约束；在当前任务规模下，稳定性和可预测性比峰值吞吐量更重要。

下载任务还设置了请求间隔和带宽上限，翻译与上传成功后也会主动等待，以减少对上游服务和本地资源的瞬时压力。

> 上传失败策略将在下一步改造为“首次失败进入人工确认队列”。上传具有外部副作用，而当前系统尚无可靠的远端幂等确认，因此不能把自动重试描述成已经完成的能力。

## 单镜像多角色

`Dockerfile` 只构建一个应用镜像，`entrypoint.sh` 根据 `PROCESS_TYPE` 启动 translator、downloader 或 uploader。三个角色共享依赖和基础代码，因此单镜像可以减少重复构建、镜像体积差异和版本漂移；Kubernetes Deployment 仍可对不同角色分别配置环境变量、资源和副本数。

元数据抓取目前是按频道触发的批处理入口，尚未纳入 `PROCESS_TYPE`。

## 配置与密钥

应用不在代码中保存真实凭证。OpenAI、PostgreSQL 和 RabbitMQ 凭证均通过环境变量提供，示例见 [`.env.example`](.env.example)。本地 `.env` 已被 Git 忽略。

Kubernetes 使用名为 `media-pipeline-secrets` 的 Secret。创建方式：

```bash
cp k8s/secrets.example.yaml k8s/secrets.yaml
# 只在本地编辑 k8s/secrets.yaml，禁止提交该文件
kubectl apply -f k8s/secrets.yaml
```

目标平台 Cookie 应通过只读文件或 Kubernetes Secret 挂载，并使用 `BILIUP_COOKIES_PATH` 指定路径；不要把 Cookie 文件复制进镜像或提交到 Git。

## 运行角色

```bash
PROCESS_TYPE=translator  ./entrypoint.sh
PROCESS_TYPE=downloader  ./entrypoint.sh
PROCESS_TYPE=uploader    ./entrypoint.sh
```

主要环境变量：

| 变量 | 用途 |
| --- | --- |
| `OPENAI_API_KEY` | 翻译阶段访问 OpenAI API |
| `POSTGRES_*` | PostgreSQL 连接配置 |
| `MQ_*` | RabbitMQ 连接配置 |
| `MEDIA_BASE_DIR` | 共享媒体目录 |
| `BILIUP_COOKIES_PATH` | 目标平台 Cookie 文件路径 |

## 当前改造计划

- 修复重试计数没有写回消息的问题。
- 下载与翻译失败时重新发布带新计数的消息，再确认原消息。
- 上传首次失败即进入人工确认队列，并保留本地文件。
- 保存目标平台视频 ID，为人工恢复和后续幂等检查提供依据。
- 增加按阶段耗时、结果和 `video_id` 关联的结构化日志。
