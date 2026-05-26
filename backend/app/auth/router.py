from flask import Flask, request, jsonify
from database import db, Doctor
from patient import add_patient as create_patient

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///handoc.db'
db.init_app(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    license_number = data.get('license_number')
    name = data.get('name')

    if not license_number or not license_number.isdigit() or len(license_number) != 8:
        return jsonify({'error': '올바른 면허번호를 입력해주세요 (8자리 숫자)'}), 400

    existing = Doctor.query.filter_by(license_number=license_number).first()
    if existing:
        return jsonify({'error': '이미 등록된 면허번호입니다'}), 400

    doctor = Doctor(license_number=license_number, name=name, is_verified=True)
    db.session.add(doctor)
    db.session.commit()
    return jsonify({'message': f'{name} 선생님, 인증이 완료됐습니다!'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    license_number = data.get('license_number')

    doctor = Doctor.query.filter_by(license_number=license_number).first()
    if not doctor:
        return jsonify({'error': '등록되지 않은 면허번호입니다'}), 401
    return jsonify({'message': f'{doctor.name} 선생님, 환영합니다!'}), 200

@app.route('/patients', methods=['POST'])
def add_patient():
    data = request.json
    name = data.get('name')
    age = data.get('age')
    gender = data.get('gender')
    doctor_id = data.get('doctor_id')

    if not name or not age or not gender or not doctor_id:
        return jsonify({'error': '모든 필수 정보를 입력해주세요'}), 400

    patient = create_patient(name=name, age=age, gender=gender, doctor_id=doctor_id)
    return jsonify({'message': '환자 정보가 추가되었습니다', 'patient': {'id': patient.id, 'name': patient.name}}), 201

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)