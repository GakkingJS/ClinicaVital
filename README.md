# ClinicaVital

# Sistema de Gestión de Ficha Clínica Electrónica — *ClinicaVital*

## Descripción general
El presente proyecto tiene como objetivo desarrollar un **Sistema de Gestión de Ficha Clínica Electrónica** para un consultorio médico.  
Su propósito principal es **modernizar y optimizar la gestión de la información de los pacientes**, agilizando los procesos de **agendamiento de citas, registro de consultas y acceso al historial clínico**.

El sistema busca centralizar toda la información en una **plataforma digital segura, intuitiva y eficiente**, reemplazando los registros manuales en papel.  
Esto permitirá:
- Mejorar la calidad de atención al paciente mediante el acceso rápido y estructurado a los datos.
- Aumentar la seguridad y confidencialidad de la información sensible.
- Cumplir con los estándares modernos de la práctica médica.

---

## Características principales
- **Módulo de autenticación:** Inicio de sesión para pacientes, médicos, secretarias y administrador.
- **Gestión de citas:** Creación, consulta y administración de citas médicas.
- **Historias clínicas:** Registro y visualización de antecedentes médicos por paciente.
- **Recetas médicas:** Creación de recetas electrónicas asociadas a cada consulta.
- **Paneles personalizados:** Interfaz independiente según el rol del usuario.

## Roles del sistema

- **Administrador:** supervisa y gestiona usuarios del sistema.

- **Médico:** crea y consulta historias clínicas y recetas.

- **Secretaria:** agenda y administra citas médicas.

- **Paciente:** consulta su historial y recetas.

---

## 📂 Estructura del proyecto
ProyectoClinica/
├── app.py
├── templates/
│ ├── index.html
│ ├── login.html
│ ├── dashboard.html
│ ├── doctor/
│ │ ├── dashboard.html
│ │ ├── historias_clinicas.html
│ │ ├── crear_historia.html
│ │ └── crear_receta.html
│ ├── paciente/
│ │ ├── dashboard.html
│ │ ├── mi_historia.html
│ │ └── mis_recetas.html
│ ├── secretaria/
│ │ ├── dashboard.html
│ │ └── crear_cita.html
│ └── admin/
│ └── dashboard.html
└── static/
├── css/
│ └── style.css
└── js/
└── main.js


---

## ⚙️ Tecnologías utilizadas
- **Python (Flask)**
- **HTML5, CSS3, JavaScript** 
- **XAMPP / MySQL** 
- **Visual Studio Code**
