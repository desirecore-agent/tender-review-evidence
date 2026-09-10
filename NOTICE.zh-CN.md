# NOTICE — 第三方软件与许可声明

本文件列出本技能使用的第三方组件及其各自许可证。

## Python 运行时

- **Python** — PSF 许可证
  - 最低要求：>= 3.9
  - Python 许可证管辖解释器本身；本技能不重新许可 Python。

## DesireCore 平台

- **DesireCore** — DesireCore Contributors（见平台 LICENSE/NOTICE）
  - 每个已安装的 DesireCore 版本遵从其自身的 LICENSE 和 NOTICE 文件。
  - 本包根目录 LICENSE 中的 MIT 许可证仅覆盖标书审查团队的原创内容，
    不延伸至 DesireCore 平台、其运行时、模型路由或任何其他 DesireCore 组件。
  - 用户选择的模型（本地或云端）会处理发送到它的文字和图像；
    用户须拥有材料处理权利并提供相应授权。

## 直接依赖（jsonschema 4.25.1 及传递依赖）

| 包名 | 版本 | 许可证 | 来源 |
|------|------|--------|------|
| jsonschema | 4.25.1 | MIT | https://pypi.org/project/jsonschema/4.25.1/ |
| attrs | 26.1.0 | MIT | https://pypi.org/project/attrs/26.1.0/ |
| jsonschema-specifications | 2025.9.1 | MIT | https://pypi.org/project/jsonschema-specifications/2025.9.1/ |
| referencing | 0.36.2 | MIT | https://pypi.org/project/referencing/0.36.2/ |
| rpds-py | 0.27.1 | MIT | https://pypi.org/project/rpds-py/0.27.1/ |
| typing_extensions | 4.16.0 | PSF-2.0 | https://pypi.org/project/typing-extensions/4.16.0/ |

各依赖保留其各自许可证。根目录 LICENSE 中的 MIT 许可证仅覆盖标书审查团队原创内容，
不延伸至第三方包或 DesireCore 平台。

`typing_extensions` 是 `referencing` 的条件依赖（仅在 Python < 3.13 时激活）；
统一锁住是兼容超集。

## 云模型处理

用户选择的模型提供商（本地或远程）会处理发送到它的文字和图像。
用户必须拥有处理这些材料的合法权利并提供适当授权。
使用本技能不构成向任何特定服务传输材料的授权。
除非用户明确指示，本技能不会执行模型通道之外的额外 OCR、邮件或 URL 传输。

## 各包说明

- **jsonschema**：JSON Schema 校验库（通过 Draft7Validator 支持 Draft-07）。
- **attrs**：Python 类样板库（jsonschema 依赖）。
- **jsonschema-specifications**：jsonschema 的 JSON Schema 元模式（Draft-07 等）。
- **referencing**：JSON Schema 引用解析库（本技能仅使用本地 Registry）。
- **rpds-py**：持久化数据结构（Rust 后端，被 referencing 使用）。
- **typing_extensions**：向后移植的类型注解功能，兼容 Python < 3.13。
