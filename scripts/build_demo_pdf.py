from pathlib import Path

import pymupdf


def main() -> None:
    source = Path("data/docs/after_sales_faq_source.txt")
    target = Path("data/docs/after_sales_faq.pdf")
    text = source.read_text(encoding="utf-8")

    document = pymupdf.open()
    page = document.new_page(width=595, height=842)
    page.insert_textbox(
        pymupdf.Rect(50, 50, 545, 790),
        text,
        fontname="china-s",
        fontsize=12,
        lineheight=1.5,
    )
    document.set_metadata(
        {
            "title": "SmartShop 虚构售后常见问题",
            "author": "SmartShop AI Demo",
        }
    )
    document.save(target)
    document.close()
    print(f"Generated {target}")


if __name__ == "__main__":
    main()
