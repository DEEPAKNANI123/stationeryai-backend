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
from collections import defaultdict

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="StationeryAI Backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # for deployment allow all
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


# ------------------- Schemas -------------------

class OrderRequest(BaseModel):
    amount: int   # rupees


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


# ------------------- APIs -------------------

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


# ---------------- AI Recommend ---------------- #

@app.post("/recommend")
def recommend_products(data: RecommendRequest, db: Session = Depends(get_db)):
    purpose = data.purpose.lower()
    budget = data.budget

    products = db.query(Product).all()
    recommendations = []

    for p in products:
        if p.price <= budget:
            if purpose in p.category.lower() or purpose in p.name.lower():
                recommendations.append(p)

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


# ---------------- SALES APIs ---------------- #

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


@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    return db.query(Sales).all()


# ---------------- Demand Prediction ---------------- #

@app.get("/predict-demand")
def predict_demand(db: Session = Depends(get_db)):
    sales_data = db.query(Sales).all()

    if len(sales_data) == 0:
        return {"message": "No sales data found. Add sales first."}

    demand = defaultdict(int)

    for sale in sales_data:
        demand[sale.product_name] += sale.quantity_sold

    predicted = sorted(demand.items(), key=lambda x: x[1], reverse=True)

    result = []
    for product, qty in predicted:
        result.append({
            "product_name": product,
            "predicted_demand": qty + 5
        })

    return result


# ---------------- Monthly Report (Postgres Fixed) ---------------- #

@app.get("/monthly-report")
def monthly_report(db: Session = Depends(get_db)):

    report = db.query(
        func.to_char(Sales.sale_date, "YYYY-MM").label("month"),
        func.sum(Sales.total_amount).label("total_sales"),
        func.sum(Sales.profit).label("total_profit"),
        func.sum(Sales.quantity_sold).label("total_items_sold")
    ).group_by("month").order_by("month").all()

    if len(report) == 0:
        return {"message": "No sales data available. Reports will appear after purchases."}

    result = []
    for r in report:
        result.append({
            "month": r.month,
            "total_sales": round(r.total_sales or 0, 2),
            "total_profit": round(r.total_profit or 0, 2),
            "total_items_sold": int(r.total_items_sold or 0)
        })

    return result


# ---------------- Stock Report ---------------- #

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


# ---------------- Update Stock ---------------- #

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
