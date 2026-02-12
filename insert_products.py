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
