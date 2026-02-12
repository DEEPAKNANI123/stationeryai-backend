from sqlalchemy import Column, Integer, String, Float, DateTime
from database import Base
from datetime import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String)
    price = Column(Float)
    stock = Column(Integer)


class Sales(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String)
    category = Column(String)
    quantity_sold = Column(Integer)
    price = Column(Float)
    total_amount = Column(Float)
    profit = Column(Float)
    sale_date = Column(DateTime, default=datetime.utcnow)