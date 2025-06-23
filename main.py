
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, date
from enum import Enum
import os

# Modelos de datos
class Student(BaseModel):
    matricula: str = Field(..., description="Matrícula del estudiante")
    nombre: str = Field(..., description="Nombre completo del estudiante")
    created_at: datetime = Field(default_factory=datetime.now)

class StudentUpdate(BaseModel):
    nombre: Optional[str] = Field(None, description="Nuevo nombre del estudiante")

class AttendanceStatus(str, Enum):
    PRESENTE = "presente"
    AUSENTE = "ausente"
    TARDANZA = "tardanza"

class AttendanceRecord(BaseModel):
    matricula: str
    nombre: str
    status: AttendanceStatus
    fecha: date
    hora: datetime
    observaciones: Optional[str] = None

class AttendanceRequest(BaseModel):
    matricula: str
    status: AttendanceStatus = AttendanceStatus.PRESENTE
    observaciones: Optional[str] = None

class AttendanceStats(BaseModel):
    total_estudiantes: int
    presentes: int
    ausentes: int
    tardanzas: int
    porcentaje_asistencia: float

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Pase de Lista API",
    description="API para gestionar estudiantes y control de asistencia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Configuración para producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica dominios exactos
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Base de datos en memoria
students_db: Dict[str, Student] = {}
attendance_db: List[AttendanceRecord] = []

# Datos de ejemplo
example_students = [
    {"matricula": "2024001", "nombre": "Ana García López"},
    {"matricula": "2024002", "nombre": "Carlos Rodríguez Martín"},
    {"matricula": "2024003", "nombre": "María Fernández Silva"},
    {"matricula": "2024004", "nombre": "José Luis Hernández"},
    {"matricula": "2024005", "nombre": "Laura Martínez Ruiz"},
    {"matricula": "2024006", "nombre": "Pedro Sánchez Morales"},
    {"matricula": "2024007", "nombre": "Carmen Jiménez Torres"},
    {"matricula": "2024008", "nombre": "Miguel Ángel Ruiz"},
    {"matricula": "2024009", "nombre": "Isabel Moreno Castro"},
    {"matricula": "2024010", "nombre": "Francisco Javier López"},
]

# Inicializar con datos de ejemplo
for student_data in example_students:
    student = Student(**student_data)
    students_db[student.matricula] = student

@app.get("/", tags=["General"])
async def root():
    """Endpoint de bienvenida"""
    return {
        "mensaje": "🎓 Sistema de Pase de Lista API",
        "version": "1.0.0",
        "status": "✅ Funcionando correctamente",
        "estudiantes_registrados": len(students_db),
        "registros_asistencia": len(attendance_db),
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "estudiantes": "/students",
            "asistencia": "/attendance",
            "reportes": "/reports",
            "documentacion": "/docs",
            "salud": "/health"
        }
    }

# ENDPOINTS DE ESTUDIANTES
@app.get("/students", response_model=List[Student], tags=["Estudiantes"])
async def get_all_students():
    """Obtener todos los estudiantes registrados"""
    return list(students_db.values())

@app.get("/students/{matricula}", response_model=Student, tags=["Estudiantes"])
async def get_student(matricula: str):
    """Obtener un estudiante por matrícula"""
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    return students_db[matricula]

@app.post("/students", response_model=Student, tags=["Estudiantes"])
async def add_student(student: Student):
    """Agregar un nuevo estudiante"""
    if student.matricula in students_db:
        raise HTTPException(status_code=400, detail="La matrícula ya existe")
    
    students_db[student.matricula] = student
    return student

@app.put("/students/{matricula}", response_model=Student, tags=["Estudiantes"])
async def update_student(matricula: str, student_update: StudentUpdate):
    """Actualizar información de un estudiante"""
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    student = students_db[matricula]
    if student_update.nombre:
        student.nombre = student_update.nombre
    
    return student

@app.delete("/students/{matricula}", tags=["Estudiantes"])
async def delete_student(matricula: str):
    """Eliminar un estudiante"""
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    deleted_student = students_db.pop(matricula)
    
    # Eliminar registros de asistencia del estudiante
    global attendance_db
    attendance_db = [record for record in attendance_db if record.matricula != matricula]
    
    return {
        "mensaje": f"Estudiante {deleted_student.nombre} eliminado exitosamente",
        "estudiante": deleted_student
    }

# ENDPOINTS DE ASISTENCIA
@app.post("/attendance", response_model=AttendanceRecord, tags=["Asistencia"])
async def mark_attendance(attendance: AttendanceRequest):
    """Marcar asistencia de un estudiante"""
    if attendance.matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    student = students_db[attendance.matricula]
    today = date.today()
    
    # Verificar si ya se marcó asistencia hoy
    existing_record = next(
        (record for record in attendance_db 
         if record.matricula == attendance.matricula and record.fecha == today),
        None
    )
    
    if existing_record:
        # Actualizar registro existente
        existing_record.status = attendance.status
        existing_record.hora = datetime.now()
        existing_record.observaciones = attendance.observaciones
        return existing_record
    
    # Crear nuevo registro
    record = AttendanceRecord(
        matricula=attendance.matricula,
        nombre=student.nombre,
        status=attendance.status,
        fecha=today,
        hora=datetime.now(),
        observaciones=attendance.observaciones
    )
    
    attendance_db.append(record)
    return record

@app.get("/attendance/today", response_model=List[AttendanceRecord], tags=["Asistencia"])
async def get_today_attendance():
    """Obtener asistencia del día actual"""
    today = date.today()
    today_records = [record for record in attendance_db if record.fecha == today]
    return today_records

@app.get("/attendance/date/{fecha}", response_model=List[AttendanceRecord], tags=["Asistencia"])
async def get_attendance_by_date(fecha: date):
    """Obtener asistencia por fecha específica"""
    date_records = [record for record in attendance_db if record.fecha == fecha]
    return date_records

@app.get("/attendance/student/{matricula}", response_model=List[AttendanceRecord], tags=["Asistencia"])
async def get_student_attendance(matricula: str):
    """Obtener historial de asistencia de un estudiante"""
    if matricula not in students_db:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    student_records = [record for record in attendance_db if record.matricula == matricula]
    return student_records

# ENDPOINTS DE REPORTES
@app.get("/reports/stats/today", response_model=AttendanceStats, tags=["Reportes"])
async def get_today_stats():
    """Obtener estadísticas de asistencia del día actual"""
    today = date.today()
    today_records = [record for record in attendance_db if record.fecha == today]
    
    total_estudiantes = len(students_db)
    presentes = len([r for r in today_records if r.status == AttendanceStatus.PRESENTE])
    ausentes = total_estudiantes - len(today_records) + len([r for r in today_records if r.status == AttendanceStatus.AUSENTE])
    tardanzas = len([r for r in today_records if r.status == AttendanceStatus.TARDANZA])
    
    porcentaje_asistencia = (presentes / total_estudiantes * 100) if total_estudiantes > 0 else 0
    
    return AttendanceStats(
        total_estudiantes=total_estudiantes,
        presentes=presentes,
        ausentes=ausentes,
        tardanzas=tardanzas,
        porcentaje_asistencia=round(porcentaje_asistencia, 2)
    )

@app.get("/reports/missing-today", tags=["Reportes"])
async def get_missing_students_today():
    """Obtener estudiantes que no han marcado asistencia hoy"""
    today = date.today()
    today_records = [record for record in attendance_db if record.fecha == today]
    attended_matriculas = {record.matricula for record in today_records}
    
    missing_students = [
        student for matricula, student in students_db.items()
        if matricula not in attended_matriculas
    ]
    
    return {
        "fecha": today,
        "estudiantes_faltantes": missing_students,
        "total_faltantes": len(missing_students)
    }

@app.get("/reports/summary", tags=["Reportes"])
async def get_general_summary():
    """Obtener resumen general del sistema"""
    today = date.today()
    today_records = [record for record in attendance_db if record.fecha == today]
    
    return {
        "sistema": {
            "total_estudiantes": len(students_db),
            "total_registros_asistencia": len(attendance_db),
            "fecha_actual": today
        },
        "hoy": {
            "registros": len(today_records),
            "presentes": len([r for r in today_records if r.status == AttendanceStatus.PRESENTE]),
            "ausentes": len([r for r in today_records if r.status == AttendanceStatus.AUSENTE]),
            "tardanzas": len([r for r in today_records if r.status == AttendanceStatus.TARDANZA])
        }
    }

@app.get("/health", tags=["General"])
async def health_check():
    """Verificar que la API esté funcionando"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "API funcionando correctamente",
        "environment": "production" if os.getenv("RENDER") else "development",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Iniciando Sistema de Pase de Lista API...")
    print(f"📡 Puerto: {port}")
    print("📚 Documentación: /docs")
    print("🏥 Health Check: /health")
    uvicorn.run(app, host="0.0.0.0", port=port)
