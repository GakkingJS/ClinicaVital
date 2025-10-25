from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_super_segura_aqui_2024'  # Cambia esto por algo más seguro

# Configuración de la conexión MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'clinica_vital'

mysql = MySQL(app)

# =====================================
# DECORADORES DE PERMISOS
# =====================================

def login_required(f):
    """Requiere que el usuario esté autenticado"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Debes iniciar sesión primero', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Requiere que el usuario tenga uno de los roles especificados"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'rol' not in session:
                flash('No tienes permisos para acceder', 'danger')
                return redirect(url_for('index'))
            
            if session['rol'] not in roles:
                flash('No tienes permisos para esta acción', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(modulo, accion):
    """
    Verifica si el usuario tiene permiso para realizar una acción específica
    accion puede ser: 'ver', 'crear', 'editar', 'eliminar'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session or 'rol_id' not in session:
                flash('Debes iniciar sesión', 'warning')
                return redirect(url_for('login'))
            
            cursor = mysql.connection.cursor()
            query = """
                SELECT puede_ver, puede_crear, puede_editar, puede_eliminar
                FROM permisos
                WHERE rol_id = %s AND modulo = %s
            """
            cursor.execute(query, (session['rol_id'], modulo))
            permiso = cursor.fetchone()
            cursor.close()
            
            if not permiso:
                flash('No tienes permisos para este módulo', 'danger')
                return redirect(url_for('dashboard'))
            
            # Mapear acción a índice de columna
            acciones_map = {
                'ver': permiso[0],      # puede_ver
                'crear': permiso[1],    # puede_crear
                'editar': permiso[2],   # puede_editar
                'eliminar': permiso[3]  # puede_eliminar
            }
            
            if not acciones_map.get(accion, False):
                flash(f'No tienes permiso para {accion} en este módulo', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =====================================
# FUNCIONES DE AYUDA
# =====================================

def registrar_auditoria(usuario_id, accion, modulo, registro_id=None, detalles=None):
    """Registra acciones en la tabla de auditoría"""
    cursor = mysql.connection.cursor()
    ip = request.remote_addr
    
    query = """
        INSERT INTO auditoria (usuario_id, accion, modulo, registro_id, detalles, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (usuario_id, accion, modulo, registro_id, detalles, ip))
    mysql.connection.commit()
    cursor.close()

# =====================================
# RUTAS PÚBLICAS
# =====================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        query = """
            SELECT u.id, u.username, u.password, u.rol_id, u.nombre_completo, r.nombre as rol
            FROM usuarios u
            JOIN roles r ON u.rol_id = r.id
            WHERE u.username = %s AND u.activo = TRUE
        """
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user[2], password):  # user[2] es password
            session['usuario_id'] = user[0]
            session['username'] = user[1]
            session['rol_id'] = user[3]
            session['nombre_completo'] = user[4]
            session['rol'] = user[5]
            
            # Registrar login en auditoría
            registrar_auditoria(user[0], 'login', 'sistema')
            
            flash(f'¡Bienvenido {user[4]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    
    # Por defecto, los usuarios registrados son pacientes (rol_id = 4)
    nombre_completo = request.form.get('nombre_completo', username)
    rol_id = 4  # Paciente
    
    # Hash de la contraseña
    password_hash = generate_password_hash(password)

    cursor = mysql.connection.cursor()
    
    # Verificar si el usuario ya existe
    cursor.execute("SELECT id FROM usuarios WHERE username = %s OR email = %s", (username, email))
    if cursor.fetchone():
        cursor.close()
        flash('El usuario o email ya existe', 'warning')
        return redirect(url_for('login'))
    
    # Insertar usuario
    query = """
        INSERT INTO usuarios (username, email, password, rol_id, nombre_completo)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (username, email, password_hash, rol_id, nombre_completo))
    mysql.connection.commit()
    usuario_id = cursor.lastrowid
    
    # Crear registro en tabla pacientes
    cursor.execute("INSERT INTO pacientes (usuario_id) VALUES (%s)", (usuario_id,))
    mysql.connection.commit()
    cursor.close()

    flash('Registro exitoso. Por favor inicia sesión', 'success')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    registrar_auditoria(session['usuario_id'], 'logout', 'sistema')
    session.clear()
    flash('Has cerrado sesión exitosamente', 'info')
    return redirect(url_for('index'))

# =====================================
# DASHBOARD GENERAL
# =====================================

@app.route('/dashboard')
@login_required
def dashboard():
    rol = session.get('rol')
    
    # Redirigir al dashboard específico según el rol
    if rol == 'doctor':
        return redirect(url_for('dashboard_doctor'))
    elif rol == 'paciente':
        return redirect(url_for('dashboard_paciente'))
    elif rol == 'secretaria':
        return redirect(url_for('dashboard_secretaria'))
    elif rol == 'admin':
        return redirect(url_for('dashboard_admin'))
    else:
        return render_template('dashboard.html')

# =====================================
# DASHBOARD DOCTOR
# =====================================

@app.route('/doctor/dashboard')
@login_required
@role_required('doctor')
def dashboard_doctor():
    cursor = mysql.connection.cursor()
    
    # Obtener doctor_id
    cursor.execute("SELECT id FROM doctores WHERE usuario_id = %s", (session['usuario_id'],))
    doctor = cursor.fetchone()
    doctor_id = doctor[0] if doctor else None
    
    # Obtener citas de hoy
    query = """
        SELECT c.*, u.nombre_completo as paciente_nombre
        FROM citas c
        JOIN pacientes p ON c.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE c.doctor_id = %s AND DATE(c.fecha_hora) = CURDATE()
        ORDER BY c.fecha_hora
    """
    cursor.execute(query, (doctor_id,))
    citas_hoy = cursor.fetchall()
    
    cursor.close()
    
    return render_template('doctor/dashboard.html', citas=citas_hoy)

@app.route('/doctor/historias-clinicas')
@login_required
@role_required('doctor')
@permission_required('historias_clinicas', 'ver')
def historias_clinicas():
    cursor = mysql.connection.cursor()
    
    # Obtener doctor_id
    cursor.execute("SELECT id FROM doctores WHERE usuario_id = %s", (session['usuario_id'],))
    doctor = cursor.fetchone()
    doctor_id = doctor[0] if doctor else None
    
    # Obtener historias clínicas del doctor
    query = """
        SELECT hc.*, u.nombre_completo as paciente_nombre
        FROM historias_clinicas hc
        JOIN pacientes p ON hc.paciente_id = p.id
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE hc.doctor_id = %s
        ORDER BY hc.fecha_consulta DESC
        LIMIT 50
    """
    cursor.execute(query, (doctor_id,))
    historias = cursor.fetchall()
    cursor.close()
    
    return render_template('doctor/historias_clinicas.html', historias=historias)

@app.route('/doctor/historia-clinica/crear/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
@permission_required('historias_clinicas', 'crear')
def crear_historia_clinica(paciente_id):
    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        
        # Obtener doctor_id
        cursor.execute("SELECT id FROM doctores WHERE usuario_id = %s", (session['usuario_id'],))
        doctor = cursor.fetchone()
        doctor_id = doctor[0]
        
        # Insertar historia clínica
        query = """
            INSERT INTO historias_clinicas 
            (paciente_id, doctor_id, motivo_consulta, sintomas, diagnostico, observaciones,
             presion_arterial, temperatura, peso, altura)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            paciente_id, doctor_id,
            request.form.get('motivo'), request.form.get('sintomas'),
            request.form.get('diagnostico'), request.form.get('observaciones'),
            request.form.get('presion'), request.form.get('temperatura'),
            request.form.get('peso'), request.form.get('altura')
        ))
        mysql.connection.commit()
        historia_id = cursor.lastrowid
        cursor.close()
        
        registrar_auditoria(session['usuario_id'], 'crear', 'historias_clinicas', historia_id)
        flash('Historia clínica creada exitosamente', 'success')
        return redirect(url_for('historias_clinicas'))
    
    # GET - Obtener datos del paciente
    cursor = mysql.connection.cursor()
    query = """
        SELECT u.nombre_completo, u.fecha_nacimiento, p.tipo_sangre, p.alergias
        FROM pacientes p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
    """
    cursor.execute(query, (paciente_id,))
    paciente = cursor.fetchone()
    cursor.close()
    
    return render_template('doctor/crear_historia.html', paciente=paciente, paciente_id=paciente_id)

@app.route('/doctor/receta/crear/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
@role_required('doctor')
@permission_required('recetas', 'crear')
def crear_receta(paciente_id):
    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        
        # Obtener doctor_id
        cursor.execute("SELECT id FROM doctores WHERE usuario_id = %s", (session['usuario_id'],))
        doctor = cursor.fetchone()
        doctor_id = doctor[0]
        
        # Crear receta (sin historia_clinica_id si es receta independiente)
        query = """
            INSERT INTO recetas 
            (historia_clinica_id, paciente_id, doctor_id, instrucciones_generales, fecha_vencimiento)
            VALUES (%s, %s, %s, %s, %s)
        """
        historia_id = request.form.get('historia_id') if request.form.get('historia_id') else None
        cursor.execute(query, (
            historia_id, paciente_id, doctor_id,
            request.form.get('instrucciones'), request.form.get('fecha_vencimiento')
        ))
        receta_id = cursor.lastrowid
        
        # Agregar medicamentos
        medicamentos = request.form.getlist('medicamento[]')
        dosis = request.form.getlist('dosis[]')
        frecuencias = request.form.getlist('frecuencia[]')
        duraciones = request.form.getlist('duracion[]')
        
        for i in range(len(medicamentos)):
            if medicamentos[i]:  # Solo si hay medicamento
                query_med = """
                    INSERT INTO medicamentos_receta 
                    (receta_id, nombre_medicamento, dosis, frecuencia, duracion)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query_med, (receta_id, medicamentos[i], dosis[i], frecuencias[i], duraciones[i]))
        
        mysql.connection.commit()
        cursor.close()
        
        registrar_auditoria(session['usuario_id'], 'crear', 'recetas', receta_id)
        flash('Receta creada exitosamente', 'success')
        return redirect(url_for('dashboard_doctor'))
    
    return render_template('doctor/crear_receta.html', paciente_id=paciente_id)

# =====================================
# DASHBOARD PACIENTE
# =====================================

@app.route('/paciente/dashboard')
@login_required
@role_required('paciente')
def dashboard_paciente():
    cursor = mysql.connection.cursor()
    
    # Obtener paciente_id
    cursor.execute("SELECT id FROM pacientes WHERE usuario_id = %s", (session['usuario_id'],))
    paciente = cursor.fetchone()
    paciente_id = paciente[0] if paciente else None
    
    # Obtener próximas citas
    query = """
        SELECT c.*, u.nombre_completo as doctor_nombre, e.nombre as especialidad
        FROM citas c
        JOIN doctores d ON c.doctor_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        JOIN especialidades e ON d.especialidad_id = e.id
        WHERE c.paciente_id = %s AND c.fecha_hora >= NOW()
        ORDER BY c.fecha_hora
        LIMIT 5
    """
    cursor.execute(query, (paciente_id,))
    citas = cursor.fetchall()
    
    cursor.close()
    
    return render_template('paciente/dashboard.html', citas=citas)

@app.route('/paciente/mi-historia')
@login_required
@role_required('paciente')
@permission_required('mi_historia_clinica', 'ver')
def mi_historia_clinica():
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT id FROM pacientes WHERE usuario_id = %s", (session['usuario_id'],))
    paciente = cursor.fetchone()
    paciente_id = paciente[0]
    
    query = """
        SELECT hc.*, u.nombre_completo as doctor_nombre, e.nombre as especialidad
        FROM historias_clinicas hc
        JOIN doctores d ON hc.doctor_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        JOIN especialidades e ON d.especialidad_id = e.id
        WHERE hc.paciente_id = %s
        ORDER BY hc.fecha_consulta DESC
    """
    cursor.execute(query, (paciente_id,))
    historias = cursor.fetchall()
    cursor.close()
    
    return render_template('paciente/mi_historia.html', historias=historias)

@app.route('/paciente/mis-recetas')
@login_required
@role_required('paciente')
@permission_required('mis_recetas', 'ver')
def mis_recetas():
    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT id FROM pacientes WHERE usuario_id = %s", (session['usuario_id'],))
    paciente = cursor.fetchone()
    paciente_id = paciente[0]
    
    query = """
        SELECT r.*, u.nombre_completo as doctor_nombre
        FROM recetas r
        JOIN doctores d ON r.doctor_id = d.id
        JOIN usuarios u ON d.usuario_id = u.id
        WHERE r.paciente_id = %s AND r.activa = TRUE
        ORDER BY r.fecha_emision DESC
    """
    cursor.execute(query, (paciente_id,))
    recetas = cursor.fetchall()
    cursor.close()
    
    return render_template('paciente/mis_recetas.html', recetas=recetas)

# =====================================
# DASHBOARD SECRETARIA
# =====================================

@app.route('/secretaria/dashboard')
@login_required
@role_required('secretaria')
def dashboard_secretaria():
    cursor = mysql.connection.cursor()
    
    # Obtener citas de hoy
    query = """
        SELECT c.*, 
               up.nombre_completo as paciente_nombre,
               ud.nombre_completo as doctor_nombre,
               e.nombre as especialidad
        FROM citas c
        JOIN pacientes p ON c.paciente_id = p.id
        JOIN usuarios up ON p.usuario_id = up.id
        JOIN doctores d ON c.doctor_id = d.id
        JOIN usuarios ud ON d.usuario_id = ud.id
        JOIN especialidades e ON d.especialidad_id = e.id
        WHERE DATE(c.fecha_hora) = CURDATE()
        ORDER BY c.fecha_hora
    """
    cursor.execute(query)
    citas_hoy = cursor.fetchall()
    cursor.close()
    
    return render_template('secretaria/dashboard.html', citas=citas_hoy)

@app.route('/secretaria/cita/crear', methods=['GET', 'POST'])
@login_required
@role_required('secretaria')
@permission_required('citas', 'crear')
def crear_cita():
    if request.method == 'POST':
        cursor = mysql.connection.cursor()
        
        query = """
            INSERT INTO citas 
            (paciente_id, doctor_id, fecha_hora, motivo, creada_por)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            request.form['paciente_id'], request.form['doctor_id'],
            request.form['fecha_hora'], request.form.get('motivo', ''),
            session['usuario_id']
        ))
        cita_id = cursor.lastrowid
        mysql.connection.commit()
        cursor.close()
        
        registrar_auditoria(session['usuario_id'], 'crear', 'citas', cita_id)
        flash('Cita agendada exitosamente', 'success')
        return redirect(url_for('dashboard_secretaria'))
    
    # GET - Obtener doctores y pacientes
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT d.id, u.nombre_completo, e.nombre as especialidad 
        FROM doctores d 
        JOIN usuarios u ON d.usuario_id = u.id 
        JOIN especialidades e ON d.especialidad_id = e.id
        WHERE u.activo = TRUE
    """)
    doctores = cursor.fetchall()
    
    cursor.execute("""
        SELECT p.id, u.nombre_completo 
        FROM pacientes p 
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE u.activo = TRUE
    """)
    pacientes = cursor.fetchall()
    cursor.close()
    
    return render_template('secretaria/crear_cita.html', doctores=doctores, pacientes=pacientes)

# =====================================
# DASHBOARD ADMIN
# =====================================

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def dashboard_admin():
    cursor = mysql.connection.cursor()
    
    # Estadísticas generales
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE activo = TRUE")
    total_usuarios = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM citas WHERE DATE(fecha_hora) = CURDATE()")
    citas_hoy = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM historias_clinicas WHERE DATE(fecha_consulta) = CURDATE()")
    consultas_hoy = cursor.fetchone()[0]
    
    cursor.close()
    
    return render_template('admin/dashboard.html', 
                         total_usuarios=total_usuarios,
                         citas_hoy=citas_hoy,
                         consultas_hoy=consultas_hoy)

if __name__ == '__main__':
    app.run(debug=True)