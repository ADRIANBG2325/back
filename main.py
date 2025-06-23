from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date
import os

# Crear app Flask
app = Flask(__name__)

# Configurar CORS de manera más específica
CORS(app, 
     origins=["*"],  # Permitir todos los orígenes
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "Accept"],
     supports_credentials=True)

# Base de datos en memoria
students_db = {}
attendance_db = []

# Datos iniciales
initial_students = [
    {"matricula": "2024001", "nombre": "Ana García López", "created_at": datetime.now().isoformat()},
    {"matricula": "2024002", "nombre": "Carlos Rodríguez Martín", "created_at": datetime.now().isoformat()},
    {"matricula": "2024003", "nombre": "María Fernández Silva", "created_at": datetime.now().isoformat()},
    {"matricula": "2024004", "nombre": "José Luis Hernández", "created_at": datetime.now().isoformat()},
    {"matricula": "2024005", "nombre": "Laura Martínez Ruiz", "created_at": datetime.now().isoformat()},
]

# Inicializar datos
for student in initial_students:
    students_db[student["matricula"]] = student

# Manejar preflight requests
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "mensaje": "🎓 Sistema de Pase de Lista API",
        "version": "1.0.0",
        "status": "✅ Funcionando correctamente",
        "estudiantes_registrados": len(students_db),
        "registros_asistencia": len(attendance_db),
        "timestamp": datetime.now().isoformat(),
        "cors": "✅ CORS Configurado"
    })

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "API funcionando correctamente",
        "version": "1.0.0",
        "cors": "enabled"
    })

# ESTUDIANTES
@app.route("/students", methods=["GET"])
def get_all_students():
    return jsonify(list(students_db.values()))

@app.route("/students/<matricula>", methods=["GET"])
def get_student(matricula):
    if matricula not in students_db:
        return jsonify({"detail": "Estudiante no encontrado"}), 404
    return jsonify(students_db[matricula])

@app.route("/students", methods=["POST"])
def add_student():
    data = request.get_json()
    
    if not data or not data.get("matricula") or not data.get("nombre"):
        return jsonify({"detail": "Matrícula y nombre son requeridos"}), 400
    
    matricula = data["matricula"]
    if matricula in students_db:
        return jsonify({"detail": "La matrícula ya existe"}), 400
    
    student = {
        "matricula": matricula,
        "nombre": data["nombre"],
        "created_at": datetime.now().isoformat()
    }
    
    students_db[matricula] = student
    return jsonify(student)

@app.route("/students/<matricula>", methods=["PUT"])
def update_student(matricula):
    if matricula not in students_db:
        return jsonify({"detail": "Estudiante no encontrado"}), 404
    
    data = request.get_json()
    if data and data.get("nombre"):
        students_db[matricula]["nombre"] = data["nombre"]
    
    return jsonify(students_db[matricula])

@app.route("/students/<matricula>", methods=["DELETE"])
def delete_student(matricula):
    if matricula not in students_db:
        return jsonify({"detail": "Estudiante no encontrado"}), 404
    
    deleted_student = students_db.pop(matricula)
    
    # Eliminar registros de asistencia
    global attendance_db
    attendance_db = [record for record in attendance_db if record["matricula"] != matricula]
    
    return jsonify({
        "mensaje": f"Estudiante {deleted_student['nombre']} eliminado exitosamente",
        "estudiante": deleted_student
    })

# ASISTENCIA
@app.route("/attendance", methods=["POST"])
def mark_attendance():
    data = request.get_json()
    
    if not data or not data.get("matricula"):
        return jsonify({"detail": "Matrícula es requerida"}), 400
    
    matricula = data["matricula"]
    if matricula not in students_db:
        return jsonify({"detail": "Estudiante no encontrado"}), 404
    
    student = students_db[matricula]
    today = date.today().isoformat()
    now = datetime.now().isoformat()
    status = data.get("status", "presente")
    observaciones = data.get("observaciones")
    
    # Buscar registro existente
    existing_index = None
    for i, record in enumerate(attendance_db):
        if record["matricula"] == matricula and record["fecha"] == today:
            existing_index = i
            break
    
    record_data = {
        "matricula": matricula,
        "nombre": student["nombre"],
        "status": status,
        "fecha": today,
        "hora": now,
        "observaciones": observaciones
    }
    
    if existing_index is not None:
        attendance_db[existing_index] = record_data
    else:
        attendance_db.append(record_data)
    
    return jsonify(record_data)

@app.route("/attendance/today", methods=["GET"])
def get_today_attendance():
    today = date.today().isoformat()
    today_records = [record for record in attendance_db if record["fecha"] == today]
    return jsonify(today_records)

@app.route("/attendance/date/<fecha>", methods=["GET"])
def get_attendance_by_date(fecha):
    date_records = [record for record in attendance_db if record["fecha"] == fecha]
    return jsonify(date_records)

@app.route("/attendance/student/<matricula>", methods=["GET"])
def get_student_attendance(matricula):
    if matricula not in students_db:
        return jsonify({"detail": "Estudiante no encontrado"}), 404
    
    student_records = [record for record in attendance_db if record["matricula"] == matricula]
    return jsonify(student_records)

# REPORTES
@app.route("/reports/stats/today", methods=["GET"])
def get_today_stats():
    today = date.today().isoformat()
    today_records = [record for record in attendance_db if record["fecha"] == today]
    
    total_estudiantes = len(students_db)
    presentes = len([r for r in today_records if r["status"] == "presente"])
    ausentes = total_estudiantes - len(today_records) + len([r for r in today_records if r["status"] == "ausente"])
    tardanzas = len([r for r in today_records if r["status"] == "tardanza"])
    
    porcentaje_asistencia = (presentes / total_estudiantes * 100) if total_estudiantes > 0 else 0
    
    return jsonify({
        "total_estudiantes": total_estudiantes,
        "presentes": presentes,
        "ausentes": ausentes,
        "tardanzas": tardanzas,
        "porcentaje_asistencia": round(porcentaje_asistencia, 2)
    })

@app.route("/reports/missing-today", methods=["GET"])
def get_missing_students_today():
    today = date.today().isoformat()
    today_records = [record for record in attendance_db if record["fecha"] == today]
    attended_matriculas = {record["matricula"] for record in today_records}
    
    missing_students = [
        student for matricula, student in students_db.items()
        if matricula not in attended_matriculas
    ]
    
    return jsonify({
        "fecha": today,
        "estudiantes_faltantes": missing_students,
        "total_faltantes": len(missing_students)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Iniciando API Flask...")
    print(f"📡 Puerto: {port}")
    print("🌐 CORS configurado para todos los orígenes")
    app.run(host="0.0.0.0", port=port, debug=False)

