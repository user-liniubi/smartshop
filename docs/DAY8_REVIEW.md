# Day 8 复盘｜售后知识文档

## 今日知识点

- Markdown 标题结构解析
- UTF-8 TXT 文本清洗
- PyMuPDF 提取 PDF 文本和页码
- 文件来源、标题和版本元数据
- 扫描 PDF 与空文档的错误处理

## 完成代码

- 文档解析器：`backend/app/rag/parsing.py`
- 9 份演示资料：`data/docs/`
- PDF 生成脚本：`scripts/build_demo_pdf.py`
- 客服上传接口：`POST /knowledge/upload`
- 客服文档列表：`GET /knowledge/documents`

## 演示资料

- 退换货政策
- 质保规则
- 配送 FAQ
- 耳机、键盘、显示器、笔记本、鼠标说明
- 一份带页码的 PDF 售后 FAQ

## 实际验收

- Markdown 能按标题拆成 Sections
- PDF 能提取正文、标题和第 1 页页码
- 空文件、不支持的扩展名和扫描版 PDF 有明确错误
- 仅客服角色可上传文档，消费者上传返回 403
- 通过真实上传接口成功索引 TXT 文档

## 第八天验收

- [ ] 已学习（需本人完成知识复习并确认）
- [x] 已开发
- [x] 已测试
- [x] 已提交 Git
- [x] 工程验收通过

提交信息：`feat: add persistent chat and RAG knowledge pipeline`  
提交哈希：`f150a03`
