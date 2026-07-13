# 中国财务 AI 助手公开更新源

本仓库的 `updates/` 目录用于发布中国财务 AI 助手可读取的公开 HTTPS 更新资料。

## 资讯库源

资讯库 manifest：

```text
https://raw.githubusercontent.com/hafeezakthar48-maker/ycc/refs/heads/codex/information-source-publication/updates/information-manifest.json
```

manifest 当前指向 `updates/information-feeds/national-tax-2026.json`，首批内容仅包含国家税务总局及其直属税务机关公开页面的短摘要、检索关键词和官方原文链接。

安全边界：

- 不上传企业名称、账套、凭证、报表、会话令牌或本机路径。
- manifest、feed 和文章来源必须使用 HTTPS。
- 摘要只用于检索和风险提示，不能替代法规原文、主管机关口径或财税负责人复核。
- 发布物可运行 `python -m unittest tests.test_information_source_distribution -v` 进行契约校验。
