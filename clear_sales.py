from database import SessionLocal
from models import Sales

db = SessionLocal()

db.query(Sales).delete()
db.commit()
db.close()

print("✅ All sales deleted successfully!")
