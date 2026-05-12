# Phase 4 验收文档 - GenericWebCollector（通用网页采集器）

## 目标
实现通用网页采集器，支持通过自定义 CSS 选择器从任意网页提取数据。

## 完成情况

### ✅ 核心实现
- [x] **GenericWebCollector** - 通用网页采集器实现
  - 通过 Playwright 加载动态网页
  - 支持自定义 CSS 选择器提取数据
  - 支持多条笔记提取
  - 支持浏览器回退（chromium → msedge → chrome）

- [x] **GenericPageParser** - 通用页面解析器
  - 默认选择器支持常见网页结构
  - 支持自定义选择器覆盖默认值
  - 支持多条笔记提取（max_posts 配置）
  - 支持每条笔记的多条评论提取
  - 自动生成 SHA1-based post_id 和 comment_id

- [x] **CollectorFactory 路由**
  - 添加 `generic_web` 类型路由
  - 能力状态标记为 "ready"
  - 支持采集器列表展示

### ✅ 配置验证
- [x] CollectorConfig 支持 `generic_web` 类型验证
  - 必需：`entry_url` - 要采集的 URL
  - 必需：`selectors` - CSS 选择器映射
  - 可选：`max_posts` - 最大笔记数（默认 10）
  - 可选：`max_comments_per_post` - 每条笔记最大评论数（默认 50）

### ✅ 测试覆盖

**单元测试（18/18 通过）**
- 基础测试（5 个）
  - ✅ 采集器创建
  - ✅ 缺少 entry_url 验证
  - ✅ 缺少 selectors 验证
  - ✅ 无效 URL scheme 验证
  - ✅ 有效配置验证

- 页面解析器测试（2 个）
  - ✅ 解析器初始化
  - ✅ 自定义最大评论数配置

- Factory 集成测试（3 个）
  - ✅ Factory 能创建采集器
  - ✅ generic_web 在支持列表中
  - ✅ 能力详情正确显示

- 配置测试（3 个）
  - ✅ 多个选择器选项支持
  - ✅ 默认选择器处理
  - ✅ max_posts 和 max_comments 配置

- 错误处理测试（3 个）
  - ✅ 缺少 entry_url
  - ✅ 无效 URL scheme
  - ✅ 空选择器验证

- 默认值测试（2 个）
  - ✅ 默认选择器存在
  - ✅ 自定义选择器覆盖默认值

**烟雾测试（6/6 通过）**
- ✅ 采集器创建
- ✅ Factory 创建采集器
- ✅ 能力列表
- ✅ 配置验证
- ✅ 默认选择器
- ✅ 自定义选择器

### ✅ 回归测试
- Phase 1 所有测试通过（22/22）
- Phase 2 所有测试通过（6/6）
- Phase 3 所有测试通过（13/13）
- Phase 1-4 总计 75 个测试通过

## 默认 CSS 选择器

GenericPageParser 提供的默认选择器映射：

```python
{
    "post_container": "article, [data-testid='post'], .post, [class*='post']",
    "title": "h1, h2, [data-testid='title'], .title, [class*='title']",
    "content": "article, main article, [data-testid='content'], .content, main, p",
    "author": "[data-testid='author'], [rel='author'], .author, .user-name, [class*='author']",
    "comment_item": "[data-testid='comment'], .comment-item, .comment, [class*='comment']",
}
```

## 使用示例

### 基本使用

```python
from app.collectors.factory import CollectorFactory
from types import SimpleNamespace

# 创建监控源配置
source = SimpleNamespace(
    platform="mysite",
    config={
        "collector_type": "generic_web",
        "entry_url": "https://example.com/articles",
        "selectors": {
            "post_container": ".article-item",
            "title": ".article-title",
            "content": ".article-body",
            "author": ".article-author",
            "comment_item": ".comment",
        },
        "max_posts": 20,
        "max_comments_per_post": 100,
    }
)

# 创建采集器
collector = CollectorFactory.create(source)

# 采集数据
result = collector.collect(source)
print(f"采集到 {len(result.posts)} 条笔记")
print(f"采集到 {len(result.comments)} 条评论")
```

### 使用默认选择器

```python
# 如果网页结构符合默认选择器，可以不指定 selectors
source = SimpleNamespace(
    platform="mysite",
    config={
        "collector_type": "generic_web",
        "entry_url": "https://example.com/articles",
        "selectors": {},  # 将使用所有默认选择器
    }
)
```

### 部分覆盖默认选择器

```python
# 只覆盖特定的选择器
source = SimpleNamespace(
    platform="mysite",
    config={
        "collector_type": "generic_web",
        "entry_url": "https://example.com/articles",
        "selectors": {
            "post_container": ".my-custom-post-class",
            # 其他选择器将使用默认值
        },
    }
)
```

## API 端点

### 验证 generic_web 采集器配置

```bash
POST /api/collectors/validate-config
Content-Type: application/json

{
  "collector_type": "generic_web",
  "entry_url": "https://example.com",
  "selectors": {
    "post_container": ".post",
    "title": ".post-title"
  }
}
```

### 获取采集器列表

```bash
GET /api/collectors
```

响应包含：
```json
{
  "generic_web": {
    "status": "ready",
    "supports": ["posts", "comments"],
    "config_example": {...}
  }
}
```

## 文件结构

```
backend/app/collectors/
├── generic_web_collector.py      # GenericWebCollector 实现
├── page_parsers/
│   └── generic.py                # GenericPageParser 实现
├── factory.py                    # 更新了路由
└── config.py                     # 更新了验证

backend/tests/
├── test_phase4_generic_web.py    # Phase 4 单元测试（18 个）
└── test_collectors_phase1.py     # 更新了 test_factory_generic_web_not_implemented

backend/scripts/
└── smoke_test_phase4.py          # Phase 4 烟雾测试（6 个）
```

## 技术细节

### 多选择器支持
选择器支持多个逗号分隔的值，优先级从左到右：
```python
"post_container": "article, .post, [data-testid='post']"
```

### ID 生成
- **post_id**：基于 source_url 和 post 索引的 SHA1 哈希（16 字节）
- **comment_id**：基于 post_id 和评论索引自动生成

### 错误处理
- 无效 URL scheme（非 http/https）会被拒绝
- 页面加载失败会触发浏览器回退
- 没有提取到数据时抛出 RuntimeError
- 敏感错误信息会被清理（API key、cookie 等）

### 性能考虑
- 支持最大 100 条评论/post（防止内存溢出）
- 支持最大 10000 条笔记/页面（可配置）
- 使用异步 Playwright API 提高效率
- 选择器尝试失败时自动跳过

## 后续计划

**Phase 5 - XhsCollector（小红书采集）**
- 小红书平台特定的采集器
- 需要 cookie 管理
- 需要 API 签名支持

**Phase 6 - DouYin/Zhihu 采集**
- 抖音平台采集
- 知乎平台采集
- 平台特定的反爬虫绕过机制

## 检查清单

- [x] 实现 GenericWebCollector 类
- [x] 实现 GenericPageParser 类
- [x] 更新 CollectorFactory 路由
- [x] 更新配置验证逻辑
- [x] 创建 18 个单元测试
- [x] 所有测试通过（100%）
- [x] 回归测试通过（所有 Phase 1-3）
- [x] 创建 6 个烟雾测试
- [x] 创建验收文档
- [x] 支持自定义 CSS 选择器
- [x] 支持多笔记/多评论提取
- [x] 支持浏览器回退机制
- [x] 支持默认选择器
- [x] 支持配置验证
- [x] 支持错误处理和清理

## 验证步骤

```bash
# 1. 运行 Phase 4 单元测试
cd backend
python -m pytest tests/test_phase4_generic_web.py -v

# 2. 运行 Phase 4 烟雾测试
python scripts/smoke_test_phase4.py

# 3. 运行所有回归测试
python -m pytest tests/test_collectors_phase1.py tests/test_collectors_api.py tests/test_collector_factory.py tests/test_phase2_dedup.py::TestErrorSanitization tests/test_phase3_external_api.py tests/test_phase4_generic_web.py -v

# 4. 启动后端并手动测试 API
python -m uvicorn app.main:app --reload

# 5. 在另一个终端测试 API
curl -X POST http://localhost:8000/api/collectors/validate-config \
  -H "Content-Type: application/json" \
  -d '{"collector_type": "generic_web", "entry_url": "https://example.com", "selectors": {"post_container": ".post"}}'
```

## 状态

✅ **Phase 4 完成**

- 实现完整：✅
- 测试完整：✅ (18 个单元 + 6 个烟雾)
- 回归测试：✅ (75 个测试通过)
- 文档完整：✅
- 可本地运行：✅

---

**最后更新时间**: 2024年
**实现者**: GitHub Copilot
