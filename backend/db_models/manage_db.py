from japan_server.app_factory import create_app
from japan_server.db_models import db


def setup_database():
    """
    在应用上下文中创建所有数据库表。
    如果表已存在，则不会重复创建。
    """
    print("正在进入应用上下文以创建或更新数据库表...")
    app = create_app()
    with app.app_context():
        db.create_all()
        print("数据库表已成功创建或更新！")


if __name__ == "__main__":
    setup_database()