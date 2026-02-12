from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from schemas import ProductCreate, ProductOut
from fastapi.middleware.cors import CORSMiddleware
from models import Product, Sales
from sqlalchemy import func
from datetime import datetime
import razorpay
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StationeryAI Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Razorpay Client
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schemas for payment
class OrderRequest(BaseModel):
    amount: int   # amount in rupees


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class RecommendRequest(BaseModel):
    purpose: str
    budget: int

class SalesRequest(BaseModel):
    product_name: str
    category: str
    quantity_sold: int
    price: float
    total_amount: float
    profit: float


class StockUpdateRequest(BaseModel):
    product_id: int
    quantity: int


@app.get("/")
def home():
    return {"message": "StationeryAI Backend Running Successfully"}


@app.post("/products", response_model=ProductOut)
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(
        name=product.name,
        category=product.category,
        price=product.price,
        stock=product.stock
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@app.get("/products", response_model=list[ProductOut])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


# ---------------- RAZORPAY PAYMENT APIs ---------------- #

@app.post("/create-order")
def create_order(order: OrderRequest):
    try:
        amount_in_paise = order.amount * 100

        razorpay_order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            "payment_capture": 1
        })

        return {
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key": RAZORPAY_KEY_ID
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify-payment")
def verify_payment(data: VerifyPaymentRequest):
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": data.razorpay_order_id,
            "razorpay_payment_id": data.razorpay_payment_id,
            "razorpay_signature": data.razorpay_signature
        })

        return {"status": "success", "message": "Payment Verified Successfully"}

    except Exception:
        raise HTTPException(status_code=400, detail="Payment Verification Failed")


@app.post("/recommend")
def recommend_products(data: RecommendRequest, db: Session = Depends(get_db)):
    purpose = data.purpose.lower()
    budget = data.budget

    products = db.query(Product).all()

    recommendations = []

    for p in products:
        # Simple AI Logic (rule based + budget filter)
        if p.price <= budget:
            if purpose in p.category.lower() or purpose in p.name.lower():
                recommendations.append(p)

    # If no match, just suggest cheapest items under budget
    if len(recommendations) == 0:
        recommendations = sorted(products, key=lambda x: x.price)[:5]

    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "price": p.price,
            "stock": p.stock
        }
        for p in recommendations
    ]

from sqlalchemy import Column, Integer, String, Float


@app.post("/sales")
def add_sales(data: SalesRequest, db: Session = Depends(get_db)):
    new_sale = Sales(
        product_name=data.product_name,
        category=data.category,
        quantity_sold=data.quantity_sold,
        price=data.price
    )
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    return {"message": "Sales record added successfully"}


@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    sales = db.query(Sales).all()
    return sales

from collections import defaultdict

@app.get("/predict-demand")
def predict_demand(db: Session = Depends(get_db)):
    sales_data = db.query(Sales).all()

    if len(sales_data) == 0:
        return {"message": "No sales data found. Add sales first."}

    demand = defaultdict(int)

    # total quantity sold per product
    for sale in sales_data:
        demand[sale.product_name] += sale.quantity_sold

    # sort products by demand
    predicted = sorted(demand.items(), key=lambda x: x[1], reverse=True)

    result = []
    for product, qty in predicted:
        result.append({
            "product_name": product,
            "predicted_demand": qty + 5  # simple prediction logic
        })

    return result

@app.get("/monthly-report")
def monthly_report(db: Session = Depends(get_db)):
    report = db.query(
        func.strftime("%Y-%m", Sales.sale_date).label("month"),
        func.sum(Sales.total_amount).label("total_sales"),
        func.sum(Sales.profit).label("total_profit"),
        func.sum(Sales.quantity_sold).label("total_items_sold")
    ).group_by("month").all()

    if len(report) == 0:
        return {"message": "No sales data available. Reports will appear after purchases."}

    result = []
    for r in report:
        result.append({
            "month": r.month,
            "total_sales": round(r.total_sales, 2),
            "total_profit": round(r.total_profit, 2),
            "total_items_sold": int(r.total_items_sold)
        })

    return result

@app.get("/stock-report")
def stock_report(db: Session = Depends(get_db)):
    products = db.query(Product).all()

    sales_count = db.query(Sales).count()
    if sales_count == 0:
        return {"message": "No sales data available. Stock report will appear after purchases."}

    result = []

    for p in products:
        sold_qty = db.query(func.sum(Sales.quantity_sold)).filter(
            Sales.product_name == p.name
        ).scalar()

        sold_qty = sold_qty if sold_qty else 0
        remaining = p.stock - sold_qty

        result.append({
            "product_name": p.name,
            "category": p.category,
            "initial_stock": p.stock,
            "sold_quantity": sold_qty,
            "remaining_stock": remaining
        })

    return result

@app.get("/stock-alert")
def stock_alert(db: Session = Depends(get_db)):
    sales_count = db.query(Sales).count()
    if sales_count == 0:
        return {"message": "No purchases yet. Alerts will appear after sales."}

    products = db.query(Product).all()
    alerts = []

    for p in products:
        sold_qty = db.query(func.sum(Sales.quantity_sold)).filter(
            Sales.product_name == p.name
        ).scalar()

        sold_qty = sold_qty if sold_qty else 0
        remaining = p.stock - sold_qty

        if remaining < 500:
            alerts.append({
                "product_name": p.name,
                "remaining_stock": remaining,
                "message": "⚠️ Low Stock - Order More!"
            })

    return alerts

@app.put("/update-stock")
def update_stock(data: StockUpdateRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == data.product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < data.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    product.stock -= data.quantity
    db.commit()

    return {"message": "Stock updated successfully", "remaining_stock": product.stock}



@app.post("/add-sales")
def add_sales(data: SalesRequest, db: Session = Depends(get_db)):
    sale = Sales(
        product_name=data.product_name,
        category=data.category,
        quantity_sold=data.quantity_sold,
        price=data.price,
        total_amount=data.total_amount,
        profit=data.profit,
        sale_date=datetime.utcnow()
    )

    db.add(sale)
    db.commit()
    db.refresh(sale)

    return {"message": "Sales added successfully"}


import random
from database import SessionLocal, engine, Base
from models import Product

Base.metadata.create_all(bind=engine)
db = SessionLocal()

products_list = [
    ("Trimax Pen", "Pen", 10),
    ("Reynolds Pen", "Pen", 20),
    ("Cello Gripper", "Pen", 15),
    ("Parker Pen", "Pen", 250),
    ("Pilot V7", "Pen", 120),
    ("Classmate Notebook 200 Pages", "Notebook", 120),
    ("Classmate Notebook 400 Pages", "Notebook", 220),
    ("Navneet Notebook", "Notebook", 90),
    ("Spiral Notebook", "Notebook", 180),
    ("Drawing Notebook", "Notebook", 160),
    ("Apsara Pencil Pack", "Pencil", 60),
    ("Nataraj Pencil Pack", "Pencil", 55),
    ("Camel Sketch Pen Set", "Art", 250),
    ("Camel Water Colors", "Art", 180),
    ("Oil Pastels", "Art", 150),
    ("Color Pencils Set", "Art", 220),
    ("Crayons Pack", "Art", 100),
    ("Fevicol Glue", "Office", 45),
    ("Glue Stick", "Office", 40),
    ("Stapler Small", "Office", 120),
    ("Stapler Big", "Office", 250),
    ("Staple Pins", "Office", 35),
    ("Punching Machine", "Office", 150),
    ("Paper Clips", "Office", 30),
    ("Binder Clips", "Office", 40),
    ("Sticky Notes", "Office", 60),
    ("Post-it Notes", "Office", 100),
    ("White Board Marker", "Marker", 35),
    ("Permanent Marker", "Marker", 50),
    ("Highlighter Yellow", "Marker", 60),
    ("Highlighter Set", "Marker", 150),
    ("Geometry Box", "Exam", 200),
    ("Compass Box", "Exam", 150),
    ("Scientific Calculator", "Exam", 850),
    ("Casio Calculator", "Exam", 1200),
    ("Eraser Pack", "Eraser", 30),
    ("Doms Eraser", "Eraser", 20),
    ("Sharpener", "Sharpener", 10),
    ("Sharpener Box", "Sharpener", 40),
    ("Scale 15cm", "Scale", 10),
    ("Scale 30cm", "Scale", 20),
    ("Plastic Folder", "File", 40),
    ("Office File", "File", 80),
    ("Ring Binder File", "File", 150),
    ("Document Folder", "File", 120),
    ("Chart Paper", "Paper", 25),
    ("A4 Sheets Bundle", "Paper", 200),
    ("A3 Sheets Bundle", "Paper", 350),
    ("Notebook Cover Pack", "Accessories", 60),
    ("Book Labels", "Accessories", 30),
    ("Diary", "Diary", 180),
    ("Planner Book", "Diary", 250),
    ("Graph Book", "Notebook", 100),
    ("Record Book", "Notebook", 150),
    ("White Board", "Office", 450),
    ("Drawing Board", "Art", 350),
    ("Sketch Book A4", "Art", 180),
    ("Sketch Book A3", "Art", 250),
    ("Pen Stand", "Accessories", 90),
    ("Desk Organizer", "Accessories", 300),
    ("School Bag", "Accessories", 900),
    ("Lunch Box", "Accessories", 350),
    ("Water Bottle", "Accessories", 250),
    ("School ID Card Holder", "Accessories", 80),
    ("Tape Roll", "Office", 30),
    ("Cello Tape", "Office", 40),
    ("Scissors", "Office", 70),
    ("Cutter Knife", "Office", 60),
    ("Correction Pen", "Office", 35),
    ("Correction Tape", "Office", 80),
    ("Whitener", "Office", 25),
    ("Drawing Compass", "Exam", 120),
    ("Protractor", "Exam", 20),
    ("Set Square", "Exam", 40),
    ("Math Box", "Exam", 220),
    ("School Kit Combo", "Kit", 500),
    ("Office Kit Combo", "Kit", 800),
    ("Art Kit Combo", "Kit", 700),
]

# add more random products
for i in range(1, 51):
    products_list.append((f"Custom Notebook {i}", "Notebook", random.randint(50, 300)))
    products_list.append((f"Custom Pen {i}", "Pen", random.randint(10, 200)))

# delete existing products and reinsert
db.query(Product).delete()
db.commit()

for name, cat, price in products_list:
    p = Product(name=name, category=cat, price=price, stock=20000)
    db.add(p)

db.commit()
db.close()

print("✅ Products inserted successfully!")
