# Python 编码规范

## 类型注解

### 使用场景
- 函数参数和返回值
- 类属性
- 模块级变量

### 示例
```python
def process_data(data: dict[str, Any], config: Config) -> Result:
    ...

class UserService:
    users: dict[str, User]
```

### 不强制要求
简单的内部函数和临时变量可以省略类型注解。

## 数据类

### 使用 dataclass
当类主要用于存储数据时，使用 `@dataclass` 装饰器：

```python
from dataclasses import dataclass

@dataclass
class EntitySpec:
    name: str
    type: str
    properties: dict[str, Any]
```

## 导入顺序

1. 标准库
2. 第三方库
3. 本地模块

```python
from dataclasses import dataclass
from typing import Any, Optional

import agentscope

from models import EntitySpec
from services import StorageService
```

## 函数设计

### 单一职责
每个函数只做一件事，保持简洁。

### 返回值
- 成功返回结果，失败抛出异常或返回 None/False
- 不要混用返回模式

### 错误处理
```python
try:
    result = service.fetch_data(endpoint)
except NetworkError as e:
    logger.error(f"Network error: {e}")
    return None
```

## 类设计

### 命名
- 类名：`PascalCase`（如 `EntitySpec`, `StorageService`）
- 实例变量：`snake_case`（如 `self.storage_service`）
- 常量：`UPPER_SNAKE_CASE`

### 私有属性
- 使用单下划线前缀标记私有成员：`_cache`
- 不使用双下划线（避免名称改编复杂性）

## 模块设计

### `__init__.py`
- 明确导出公共接口
- 使用 `__all__` 定义导出列表

### docstring
```python
def load_ontology(ontology_id: str) -> OntologySpec:
    """Load ontology specification by ID.

    Args:
        ontology_id: Unique identifier for the ontology.

    Returns:
        OntologySpec instance if found, None otherwise.
    """
```

## 类型使用建议

### Any vs object
- 使用 `Any` 当类型完全未知
- 使用 `object` 当值可以是任意类型

### Optional
```python
def find_by_id(items: list[dict], id: str) -> Optional[dict]:
    ...
```

### Union
```python
def parse_value(value: str | int | float) -> float:
    return float(value)
```

## 异步代码

### async/await
如使用异步，保持一致的异步风格：

```python
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

## 日志

### 日志级别
- `DEBUG` - 开发调试
- `INFO` - 一般信息
- `WARNING` - 警告
- `ERROR` - 错误

### 格式
```python
logger = logging.getLogger(__name__)

logger.info(f"Loading ontology: {ontology_id}")
logger.warning(f"Ontology not found: {ontology_id}")
```
