from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import hash_password
from backend.app.db.session import Database
from backend.app.models import Order, OrderStatus, Product, User, UserRole

DEMO_PASSWORD = "Demo123!"
AGENT_PASSWORD = "Agent123!"


@dataclass(frozen=True)
class DemoUser:
    username: str
    password: str
    role: UserRole


DEMO_USERS = (
    DemoUser("consumer_demo", DEMO_PASSWORD, UserRole.CONSUMER),
    DemoUser("consumer_other", DEMO_PASSWORD, UserRole.CONSUMER),
    DemoUser("agent_demo", AGENT_PASSWORD, UserRole.AGENT),
)

DEMO_PRODUCTS = (
    ("SmartShop 降噪耳机 Pro", "头戴式无线降噪耳机，演示商品"),
    ("SmartShop 机械键盘 K87", "87 键热插拔机械键盘，演示商品"),
    ("SmartShop 27 英寸显示器", "2K 分辨率办公显示器，演示商品"),
    ("SmartShop 14 英寸笔记本", "面向 Python 开发的轻薄笔记本，演示商品"),
    ("SmartShop 无线鼠标 M2", "轻量无线办公鼠标，演示商品"),
)

DEMO_ORDERS = (
    ("A10086", "consumer_demo", "SmartShop 降噪耳机 Pro", OrderStatus.DELIVERED),
    ("A10087", "consumer_demo", "SmartShop 机械键盘 K87", OrderStatus.SHIPPED),
    ("A10088", "consumer_other", "SmartShop 27 英寸显示器", OrderStatus.DELIVERED),
    ("A10089", "consumer_demo", "SmartShop 14 英寸笔记本", OrderStatus.CANCELLED),
    ("A10090", "consumer_other", "SmartShop 无线鼠标 M2", OrderStatus.DELIVERED),
)


def seed_demo_data(session: Session) -> dict[str, int]:
    """Insert or reuse demo records and return current table counts."""

    users: dict[str, User] = {}
    for spec in DEMO_USERS:
        user = session.scalar(select(User).where(User.username == spec.username))
        if user is None:
            user = User(
                username=spec.username,
                password_hash=hash_password(spec.password),
                role=spec.role.value,
            )
            session.add(user)
            session.flush()
        users[spec.username] = user

    products: dict[str, Product] = {}
    for name, description in DEMO_PRODUCTS:
        product = session.scalar(select(Product).where(Product.name == name))
        if product is None:
            product = Product(name=name, description=description)
            session.add(product)
            session.flush()
        products[name] = product

    for order_no, username, product_name, status in DEMO_ORDERS:
        order = session.scalar(select(Order).where(Order.order_no == order_no))
        if order is None:
            session.add(
                Order(
                    order_no=order_no,
                    user_id=users[username].id,
                    product_id=products[product_name].id,
                    status=status.value,
                )
            )

    session.commit()
    return {
        "users": session.scalar(select(func.count()).select_from(User)) or 0,
        "products": session.scalar(select(func.count()).select_from(Product)) or 0,
        "orders": session.scalar(select(func.count()).select_from(Order)) or 0,
    }


def main() -> None:
    settings = get_settings()
    development_database = Database(
        settings.database_url,
        echo=settings.database_echo,
    )
    try:
        with development_database.session_factory() as session:
            counts = seed_demo_data(session)
    finally:
        development_database.dispose()

    print(
        "Demo data ready: "
        f"users={counts['users']}, "
        f"products={counts['products']}, "
        f"orders={counts['orders']}"
    )


if __name__ == "__main__":
    main()
