from flask import request, jsonify
from database import db
from datetime import datetime

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.now)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

def add_patient(name, age, gender, doctor_id):
    patient = Patient(name=name, age=age, gender=gender, doctor_id=doctor_id)
    db.session.add(patient)
    db.session.commit()
    return patient

def add_record(patient_id, symptoms, diagnosis, prescription):
    record = Record(
        patient_id=patient_id,
        symptoms=symptoms,
        diagnosis=diagnosis,
        prescription=prescription
    )
    db.session.add(record)
    db.session.commit()
    return record

def get_patient_records(patient_id):
    return Record.query.filter_by(patient_id=patient_id).all()