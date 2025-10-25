from werkzeug.security import generate_password_hash
import mysql.connector
from mysql.connector import Error # Importar la clase Error

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''  # Reemplaza con tu contraseña real
DB_DATABASE = 'clinica_vital'
# ----------------------------------------

conn = None
cursor = None

try:
    # Conectar a la base de datos
    print("Attempting connection to the database...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_DATABASE
    )
    
    if conn.is_connected():
        cursor = conn.cursor()
        print("✅ Connection successful.")
        
        print("🚀 Creando usuarios de prueba...\n")

        # 1. CREAR ADMIN
        print("👤 Creando Administrador...")
        password_admin = generate_password_hash('admin123')
        cursor.execute("""
            INSERT INTO usuarios (username, email, password, rol_id, nombre_completo, activo)
            VALUES ('admin', 'admin@clinica.com', %s, 1, 'Administrador del Sistema', TRUE)
        """, (password_admin,))
        admin_id = cursor.lastrowid
        print(f"✅ Admin creado - Usuario: admin | Contraseña: admin123")

        # 2. CREAR DOCTOR
        print("\n👨‍⚕️ Creando Doctor...")
        password_doctor = generate_password_hash('doctor123')
        cursor.execute("""
            INSERT INTO usuarios (username, email, password, rol_id, nombre_completo, activo)
            VALUES ('doctor', 'doctor@clinica.com', %s, 2, 'Dr. Juan García', TRUE)
        """, (password_doctor,))
        doctor_user_id = cursor.lastrowid

        # Crear registro en tabla doctores
        cursor.execute("""
            INSERT INTO doctores (usuario_id, especialidad_id, numero_licencia, anos_experiencia)
            VALUES (%s, 1, 'LIC-12345', 10)
        """, (doctor_user_id,))
        print(f"✅ Doctor creado - Usuario: doctor | Contraseña: doctor123")

        # 3. CREAR SECRETARIA
        print("\n👩‍💼 Creando Secretaria...")
        password_secretaria = generate_password_hash('secretaria123')
        cursor.execute("""
            INSERT INTO usuarios (username, email, password, rol_id, nombre_completo, activo)
            VALUES ('secretaria', 'secretaria@clinica.com', %s, 3, 'María López', TRUE)
        """, (password_secretaria,))
        print(f"✅ Secretaria creada - Usuario: secretaria | Contraseña: secretaria123")

        # 4. CREAR PACIENTE
        print("\n🧑‍🦱 Creando Paciente...")
        password_paciente = generate_password_hash('paciente123')
        cursor.execute("""
            INSERT INTO usuarios (username, email, password, rol_id, nombre_completo, fecha_nacimiento, activo)
            VALUES ('paciente', 'paciente@clinica.com', %s, 4, 'Carlos Rodríguez', '1990-05-15', TRUE)
        """, (password_paciente,))
        paciente_user_id = cursor.lastrowid

        # Crear registro en tabla pacientes
        cursor.execute("""
            INSERT INTO pacientes (usuario_id, tipo_sangre, contacto_emergencia, telefono_emergencia)
            VALUES (%s, 'O+', 'Ana Rodríguez', '555-1234')
        """, (paciente_user_id,))
        print(f"✅ Paciente creado - Usuario: paciente | Contraseña: paciente123")

        # 5. CREAR CITA DE PRUEBA
        print("\n📅 Creando cita de prueba...")
        # Obtener el ID del doctor en la tabla doctores
        cursor.execute("SELECT id FROM doctores WHERE usuario_id = %s", (doctor_user_id,))
        doctor_id = cursor.fetchone()[0]

        # Obtener el ID del paciente en la tabla pacientes
        cursor.execute("SELECT id FROM pacientes WHERE usuario_id = %s", (paciente_user_id,))
        paciente_id = cursor.fetchone()[0]

        # Insertar la cita
        cursor.execute("""
            INSERT INTO citas (paciente_id, doctor_id, fecha_hora, motivo, estado, creada_por)
            VALUES (%s, %s, NOW() + INTERVAL 2 HOUR, 'Consulta general', 'programada', %s)
        """, (paciente_id, doctor_id, admin_id))
        print(f"✅ Cita creada para hoy")

        # Confirmar todos los cambios
        conn.commit()
        
        # Resumen final
        print("\n" + "="*50)
        print("✨ ¡USUARIOS CREADOS EXITOSAMENTE! ✨")
        print("="*50)
        print("\n📋 CREDENCIALES DE ACCESO:\n")
        print("👤 ADMINISTRADOR:\n   Usuario: admin\n   Contraseña: admin123\n")
        print("👨‍⚕️ DOCTOR:\n   Usuario: doctor\n   Contraseña: doctor123\n")
        print("👩‍💼 SECRETARIA:\n   Usuario: secretaria\n   Contraseña: secretaria123\n")
        print("🧑‍🦱 PACIENTE:\n   Usuario: paciente\n   Contraseña: paciente123\n")
        print("="*50)
        print("🌐 Accede a: http://localhost:5000/login")
        print("="*50)

    else:
        print("❌ Failed to connect to MySQL database.")

except Error as e:
    # Rollback en caso de error para no dejar la base de datos a medias
    if conn and conn.is_connected():
        conn.rollback() 
    print(f"\n❌ OCURRIÓ UN ERROR: {e}")
    print("⚠️ ¡Se realizó un rollback! Ningún cambio fue guardado.")

finally:
    # Cerrar el cursor y la conexión
    if cursor is not None:
        cursor.close()
    if conn is not None and conn.is_connected():
        conn.close()
        print("\nDatabase connection closed.")