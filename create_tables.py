from app import app, db  # استيراد التطبيق وقاعدة البيانات من ملف app.py

with app.app_context():
    db.create_all()  # إنشاء الجداول
