from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date
import os
import json

# Modelos básicos
class Student(BaseModel):
    matricula: str
    nombre: str
    created_at: str = ""
    
    def __init__(self, **data):
        if not data.get('created_at'):
            data['created_at'] = datetime.now().isoformat()
        super().__init__(**data)

class StudentUpdate(BaseModel):
    nombre: Optional[str] = None

class AttendanceRequest(BaseModel):
    matricula: str
    status: str = "presente"
    observaciones: Optional[str] = None

# App FastAPI
app = FastAPI(title="Sistema de Pase de Lista API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de datos en memoria
students_db = {}
attendance_db = []

# Datos iniciales
initial_students = [
    {"matricula": "2024001", "nombre": "Ana García López"},
    {"matricula": "2024002", "nombre": "Carlos Rodríguez Martín"},
    {"matricula": "2024003", "nombre": "María Fernández Silva"},
    {"matricula": "2024004", "nombre": "José Luis Hernández"},
    {"matricula": "2024005", "nombre": "Laura Martínez Ruiz"},
]

# Inicializar datos
for student_data in initial_students:
    student = Student(**student_data)
    students_db[student.matricula] = student.dict()

@app.get("/")
def root():
    return {
        "mensaje": "🎓 Sistema de Pase de Lista API",
        "version": "1.0.0",
        "status": "✅ Funcionando correctamente",
        "estudiantes_registrados": len(students_db),
        "registros_asistencia": len(attendance_db),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "API funcionando correctamente",
        "version": "1.0.0"
    }

# ESTUDIANTES
@app.get("/students")
def get_all_students():
    return list(students_db.values())

@app.get("/students/{matricula}")
def get_student(matricula: str):
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return students_db[matricula]

@app.post("/students")
def add_student(student: Student):
    if student.matricula in students_db:
        raise HTTPException(status_code=400, detail="La matrícula ya existe")
    
    students_db[student.matricula] = student.dict()
    return student.dict()

@app.put("/students/{matricula}")
def update_student(matricula: str, student_update: StudentUpdate):
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    if student_update.nombre:
        students_db[matricula]["nombre"] = student_update.nombre
    
    return students_db[matricula]

@app.delete("/students/{matricula}")
def delete_student(matricula: str):
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    deleted_student = students_db.pop(matricula)
    
    # Eliminar registros de asistencia
    global attendance_db
    attendance_db = [record for record in attendance_db if record["matricula"] != matricula]
    
    return {
        "mensaje": f"Estudiante {deleted_student['nombre']} eliminado exitosamente",
        "estudiante": deleted_student
    }

# ASISTENCIA
@app.post("/attendance")
def mark_attendance(attendance: AttendanceRequest):
    if attendance.matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    student = students_db[attendance.matricula]
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    
    # Buscar registro existente
    existing_record = None
    for i, record in enumerate(attendance_db):
        if record["matricula"] == attendance.matricula and record["fecha"] == today:
            existing_record = i
            break
    
    record_data = {
        "matricula": attendance.matricula,
        "nombre": student["nombre"],
        "status": attendance.status,
        "fecha": today,
        "hora": now,
        "observaciones": attendance.observaciones
    }
    
    if existing_record is not None:
        attendance_db[existing_record] = record_data
    else:
        attendance_db.append(record_data)
    
    return record_data

@app.get("/attendance/today")
def get_today_attendance():
    today = date.today().isoformat()
    return [record for record in attendance_db if record["fecha"] == today]

@app.get("/attendance/date/{fecha}")
def get_attendance_by_date(fecha: str):
    return [record for record in attendance_db if record["fecha"] == fecha]

@app.get("/attendance/student/{matricula}")
def get_student_attendance(matricula: str):
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    return [record for record in attendance_db if record["matricula"] == matricula]

# REPORTES
@app.get("/reports/stats/today")
def get_today_stats():
    today = date.today().isoformat()
    today_records = [record for record in attendance_db if record["fecha"] == today]
    
    total_estudiantes = len(students_db)
    presentes = len([r for r in today_records if r["status"] == "presente"])
    ausentes = total_estudiantes - len(today_records) + len([r for r in today_records if r["status"] == "ausente"])
    tardanzas = len([r for r in today_records if r["status"] == "tardanza"])
    
    porcentaje_asistencia = (presentes / total_estudiantes * 100) if total_estudiantes > 0 else 0
    
    return {
        "total_estudiantes": total_estudiantes,
        "presentes": presentes,
        "ausentes": ausentes,
        "tardanzas": tardanzas,
        "porcentaje_asistencia": round(porcentaje_asistencia, 2)
    }

@app.get("/reports/missing-today")
def get_missing_students_today():
    today = date.today().isoformat()
    today_records = [record for record in attendance_db if record["fecha"] == today]
    attended_matriculas = {record["matricula"] for record in today_records}
    
    missing_students = [
        student for matricula, student in students_db.items()
        if matricula not in attended_matriculas
    ]
    
    return {
        "fecha": today,
        "estudiantes_faltantes": missing_students,
        "total_faltantes": len(missing_students)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Iniciando API...")
    print(f"📡 Puerto: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
