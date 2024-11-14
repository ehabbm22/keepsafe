from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from zapv2 import ZAPv2
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests

app = Flask(__name__)
app.static_folder = 'static'
app.template_folder = 'templates'

# إعدادات الاتصال بقاعدة البيانات
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:123456@localhost/keepsafe'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '4f3c2d5b1e6f7a8910bc112f9c8aef3b'

db = SQLAlchemy(app)

# إعداد ZAP
zap = ZAPv2(apikey='9ddq3t7o9f97gasq9svm8e5h9f', proxies={'http': 'http://127.0.0.1:8081', 'https': 'http://127.0.0.1:8081'})

# إعداد إدارة تسجيل الدخول
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# نموذج المستخدم
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)  # المفتاح الرئيسي
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# نموذج نتائج الفحص
# class ScanResult(db.Model):
#     id = db.Column(db.Integer, primary_key=True)  # المفتاح الرئيسي
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # مفتاح خارجي للمستخدم
#     target_url = db.Column(db.String(255), nullable=False)
#     scan_id = db.Column(db.String(255), nullable=False)

class ScanResult(db.Model):
    __tablename__ = 'scan_result'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_url = db.Column(db.String(255), nullable=False)
    scan_id = db.Column(db.String(255), nullable=False)  # إذا كان معرّف الفحص هو سلسلة
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    with app.app_context():
     db.create_all()



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# الصفحة الرئيسية
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# نموذج التسجيل
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']  # تأكيد كلمة المرور
        
        # تحقق من أن كلمتي المرور متطابقتان
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة.')
            return redirect(url_for('register'))

        # تشفير كلمة المرور
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)

        # إضافة المستخدم إلى قاعدة البيانات
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('تم التسجيل بنجاح! يمكنك الآن تسجيل الدخول.')
        return redirect(url_for('login'))

    return render_template('register.html')

# نموذج تسجيل الدخول
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        # التحقق من صحة كلمة المرور
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('scann'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة.')

    return render_template('login.html')

# لوحة التحكم بعد تسجيل الدخول
@app.route('/scann')
@login_required
def scann():
    return render_template('scann.html', name=current_user.username)

# تسجيل الخروج
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# بدء الفحص
@app.route('/scan', methods=['POST'])
@login_required
def scan():
    target_url = request.form['target_url']

    # التحقق مما إذا كان الموقع موجود
    try:
        response = requests.get(target_url)
        if response.status_code != 200:
            return jsonify({'error': f"الموقع غير متاح. رمز الحالة: {response.status_code}"}), 400
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f"خطأ أثناء محاولة الوصول إلى الموقع: {e}"}), 400

    # فتح الرابط
    zap.urlopen(target_url)
    print(f"تم فتح الرابط: {target_url}")

    # بدء الفحص النشط
    scan_id = zap.ascan.scan(target_url)
    print(f"معرّف الفحص: {scan_id}")

    # تخزين نتائج الفحص في قاعدة البيانات
    new_scan_result = ScanResult(user_id=current_user.id, target_url=target_url, scan_id=scan_id)
    db.session.add(new_scan_result)
    db.session.commit()
    print(f"نتيجة الفحص تم تخزينها: {new_scan_result}")  # إضافة هذه السطر


    # إعادة معرّف الفحص للمستخدم
    return jsonify({'scan_id': scan_id})

# متابعة حالة الفحص
@app.route('/scan_status', methods=['GET'])
@login_required
def scan_status():
    scan_id = request.args.get('scan_id')
    status = zap.ascan.status(scan_id)
    return jsonify({'status': status})

# عرض النتائج
@app.route('/results', methods=['GET'])
@login_required
def results():
    # استرجاع نتائج الفحص للمستخدم الحالي
    scan_results = ScanResult.query.filter_by(user_id=current_user.id).all()
    print(f"نتائج الفحص المسترجعة: {scan_results}")  # إضافة هذه السطر

    # تجهيز بيانات التنبيهات لكل نتيجة
    all_alerts_info = []
    for scan_result in scan_results:
        alerts = zap.core.alerts(baseurl=scan_result.target_url)

        # تجهيز بيانات التنبيهات
        alerts_info = []
        for alert in alerts:
            alert_info = {
                'name': alert['alert'],
                'risk': alert['risk'],
                'description': alert['description'],
                'solution': alert['solution'],
                'scan_id': scan_result.scan_id,
                'target_url': scan_result.target_url
            }
            alerts_info.append(alert_info)
        all_alerts_info.append({'scan_id': scan_result.scan_id, 'target_url': scan_result.target_url, 'alerts': alerts_info})

    return render_template('result.html', all_alerts=all_alerts_info)


    return render_template('result.html', all_alerts=all_alerts_info)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # إنشاء الجداول إذا لم تكن موجودة
    app.run(debug=True)

