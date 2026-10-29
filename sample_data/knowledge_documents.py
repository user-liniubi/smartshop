from dataclasses import dataclass


@dataclass(frozen=True)
class DemoKnowledgeDocument:
    filename: str
    product_name: str | None = None


DEMO_KNOWLEDGE_DOCUMENTS = (
    DemoKnowledgeDocument("return_policy.md"),
    DemoKnowledgeDocument("warranty_policy.md"),
    DemoKnowledgeDocument("shipping_faq.md"),
    DemoKnowledgeDocument("after_sales_faq.pdf"),
    DemoKnowledgeDocument("headphones_manual.md", "SmartShop 降噪耳机 Pro"),
    DemoKnowledgeDocument("keyboard_manual.md", "SmartShop 机械键盘 K87"),
    DemoKnowledgeDocument("monitor_manual.md", "SmartShop 27 英寸显示器"),
    DemoKnowledgeDocument("laptop_manual.md", "SmartShop 14 英寸笔记本"),
    DemoKnowledgeDocument("mouse_manual.md", "SmartShop 无线鼠标 M2"),
)
