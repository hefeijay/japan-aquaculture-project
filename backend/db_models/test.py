
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

# 创建对象的基类:
Base = declarative_base()

# 定义User对象:
class User(Base):
    # 表的名字:
    __tablename__ = 'usertst'

    # 表的结构:
    id = Column(String(20), primary_key=True)
    user_name = Column(String(20))

print("1")
# 初始化数据库连接:
engine = create_engine('mysql+mysqlconnector://root:Root155017@rm-0iwx9y9q368yc877wbo.mysql.japan.rds.aliyuncs.com:3306/cognitive')
# 创建DBSession类型:
DBSession = sessionmaker(bind=engine)

print("2")
Base.metadata.create_all(engine)

print("3")