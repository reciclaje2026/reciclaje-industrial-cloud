# app_streamlit.py - Versión con sincronización Google Drive
import streamlit as st
import pandas as pd
import json
import os
import shutil
from datetime import datetime
from collections import defaultdict
import base64
from io import BytesIO
import qrcode
from PIL import Image
import tempfile
import webbrowser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import threading

# Importar módulo de sincronización
try:
    from drive_sync import drive_sync
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    st.warning("⚠️ Módulo drive_sync no encontrado. Sincronización con Drive deshabilitada.")

# ============================================================
# CONFIGURACIÓN
# ============================================================

DATA_FILE = "reciclaje_data.json"
BACKUP_FOLDER = "backups"
MAX_BACKUPS = 5
CAJA_FILE = "caja_diaria.json"

# ============================================================
# PORCENTAJES DE GANANCIA
# ============================================================

PORCENTAJES_POR_CATEGORIA = {
    "cobres": 0.03,
    "bronces": 0.045,
    "aluminios": 0.04,
    "plomos": 0.04,
    "baterias": 0.04,
    "aceros": 0.035,
    "chatarra": 0.09,
    "plasticos": 0.10,
    "papel": 0.10,
    "electronicos": 0.05,
    "por_pieza": 0.05,
    "pos_venta": 0.0
}

PORCENTAJES_ESPECIALES = {
    "cobre 1a": 0.031,
    "cobre 2a": 0.035,
    "tubo candy": 0.034,
    "cable forrado de cobre": 0.035,
    "radiador de cobre": 0.04,
    "bronce amarillo": 0.046,
    "bronce rojo": 0.036,
    "rebaba de bronce": 0.054,
    "aluminio cable": 0.031,
    "aluminio macizo": 0.048,
    "aluminio perfil sin pintura": 0.035,
    "aluminio perfil con pintura": 0.04,
    "aluminio bote": 0.053,
    "aluminio blando": 0.059,
    "chatarra": 0.087,
    "fierro colado": 0.09,
    "lata de fierro": 0.10,
    "pet cristal": 0.05,
    "pet verde": 0.06,
    "electrolit": 0.07,
    "carton": 0.125,
    "archivo blanco": 0.10,
    "periodico": 0.08,
    "motor": 0.06,
    "bomba": 0.055,
    "compresor": 0.05,
    "transformador": 0.045,
    "alternador": 0.05,
}

EMPRESAS_DISPONIBLES = [
    "Centro de Acopio Tláhuac",
    "Grupo Imperio Steel",
    "JRG Comercial S.A. de C.V.",
    "La Batería Verde",
    "Green Power Tezoyuca",
    "Recicladora Reforma",
    "Chinos",
    "Otro"
]

EMPRESAS_POS_VENTA = [
    "Grupo Imperio Steel",
    "Recicladora Reforma",
    "Centro de Acopio Tláhuac",
    "Chinos",
    "La Batería Verde",
    "Green Power Tezoyuca",
    "JRG Comercial S.A. de C.V.",
    "Otro"
]

# ============================================================
# FUNCIONES DE UTILIDAD
# ============================================================

def obtener_porcentaje_ganancia(material):
    material_lower = material.lower().strip()
    if material_lower in PORCENTAJES_ESPECIALES:
        return PORCENTAJES_ESPECIALES[material_lower]
    for categoria, porcentaje in PORCENTAJES_POR_CATEGORIA.items():
        if categoria in material_lower:
            return porcentaje
    return 0.05

def calcular_precio_cliente(material, precio_venta):
    ganancia = obtener_porcentaje_ganancia(material)
    return round(precio_venta * (1 - ganancia), 2)

def calcular_ganancia(material, precio_venta):
    ganancia = obtener_porcentaje_ganancia(material)
    return round(precio_venta * ganancia, 2)

def redondear(valor, decimales=2):
    return round(valor, decimales)

def inicializar_datos_por_defecto():
    return {
        'clientes': [],
        'materiales': {
            "ferrosos": [
                {"nombre": "cobre 1a", "precio_venta": 225.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "cobre 2a", "precio_venta": 202.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "tubo candy", "precio_venta": 212.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "bronce amarillo", "precio_venta": 150.50, "empresa": "La Batería Verde"},
                {"nombre": "bronce rojo", "precio_venta": 204.00, "empresa": "La Batería Verde"},
                {"nombre": "chatarra", "precio_venta": 4.60, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "fierro colado", "precio_venta": 7.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "plomo blando", "precio_venta": 42.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "plomo duro", "precio_venta": 25.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "acero 304", "precio_venta": 19.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "bateria automotriz", "precio_venta": 14.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "aluminio macizo", "precio_venta": 48.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "aluminio blando", "precio_venta": 38.00, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "plasticos": [
                {"nombre": "pet cristal", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "pet verde", "precio_venta": 8.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "electrolit", "precio_venta": 6.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "plastico duro", "precio_venta": 5.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cd", "precio_venta": 5.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "radiografia", "precio_venta": 92.00, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "electronicos": [
                {"nombre": "primera", "precio_venta": 200, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "segunda", "precio_venta": 180, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "tercera", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cpu", "precio_venta": 180, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "laptop", "precio_venta": 400, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "tv", "precio_venta": 200, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "fuente", "precio_venta": 120, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "papel": [
                {"nombre": "carton", "precio_venta": 0.80, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "archivo blanco", "precio_venta": 2.40, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "periodico", "precio_venta": 2.00, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "por_pieza": [
                {"nombre": "motor", "precio_venta": 15.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "bomba", "precio_venta": 12.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "compresor", "precio_venta": 18.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "transformador", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "alternador", "precio_venta": 14.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cigueñal", "precio_venta": 11.00, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "pos_venta": [
                {"nombre": "cobre 1a", "precio_venta": 225.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "cobre 2a", "precio_venta": 202.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "aluminio macizo", "precio_venta": 48.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "bronce amarillo", "precio_venta": 150.50, "empresa": "La Batería Verde"},
                {"nombre": "chatarra", "precio_venta": 4.60, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "pet cristal", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "carton", "precio_venta": 0.80, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "bateria automotriz", "precio_venta": 14.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "acero 304", "precio_venta": 19.50, "empresa": "Green Power Tezoyuca"},
            ]
        },
        'compras': [],
        'gastos': [],
        'compras_mayoreo': [],
        'ventas': [],
        'ventas_simuladas': [],
        'inversion_inicial': 10000,
        'fondo_salarios': 0,
        'caja_general': 10000,
        'inventario': {},
        'remisiones_generadas': [],
        'ventas_agrupadas': [],
        'visitas_clientes': {},
        'frecuencia_clientes': {},
        'caja_diaria': {}
    }

# ============================================================
# FUNCIONES DE SINCRONIZACIÓN CON DRIVE
# ============================================================

def sincronizar_con_drive():
    if not DRIVE_AVAILABLE:
        st.warning("⚠️ Módulo de sincronización no disponible")
        return False
    
    try:
        if 'data' in st.session_state:
            if drive_sync.sync_data(st.session_state.data):
                st.session_state.last_sync = datetime.now()
                return True
        return False
    except Exception as e:
        st.warning(f"⚠️ Error al sincronizar: {e}")
        return False

def cargar_desde_drive():
    if not DRIVE_AVAILABLE:
        return None
    
    try:
        data = drive_sync.sync_data()
        if data:
            return data
        return None
    except Exception as e:
        st.warning(f"⚠️ Error al cargar desde Drive: {e}")
        return None

# ============================================================
# FUNCIONES DE CARGA Y GUARDADO
# ============================================================

def cargar_datos():
    if 'data' not in st.session_state:
        if DRIVE_AVAILABLE and drive_sync.connected:
            with st.spinner("Cargando datos desde Google Drive..."):
                datos_drive = cargar_desde_drive()
                if datos_drive:
                    st.session_state.data = datos_drive
                    st.session_state.data_loaded = True
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Datos cargados desde Google Drive")
                    return st.session_state.data
        
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.session_state.data = data
                st.session_state.data_loaded = True
                return data
            except:
                pass
        
        st.session_state.data = inicializar_datos_por_defecto()
        st.session_state.data_loaded = True
        guardar_datos()
    
    return st.session_state.data

def guardar_datos():
    if 'data' in st.session_state:
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.data, f, indent=2, ensure_ascii=False)
            
            if DRIVE_AVAILABLE and drive_sync.connected:
                threading.Thread(target=sincronizar_con_drive, daemon=True).start()
            
            return True
        except Exception as e:
            st.error(f"❌ Error al guardar: {e}")
            return False
    return False

def guardar_caja_diaria():
    if 'data' in st.session_state:
        try:
            caja_file = "caja_diaria.json"
            caja_data = st.session_state.data.get('caja_diaria', {})
            with open(caja_file, 'w', encoding='utf-8') as f:
                json.dump(caja_data, f, indent=2, ensure_ascii=False)
            
            if DRIVE_AVAILABLE and drive_sync.connected:
                drive_sync.sync_caja(caja_data)
        except:
            pass

# ============================================================
# FUNCIONES DE NEGOCIO
# ============================================================

def get_clientes():
    return st.session_state.data.get('clientes', [])

def get_materiales():
    return st.session_state.data.get('materiales', {})

def get_inventario():
    return st.session_state.data.get('inventario', {})

def get_compras():
    return st.session_state.data.get('compras', [])

def get_compras_mayoreo():
    return st.session_state.data.get('compras_mayoreo', [])

def get_ventas():
    return st.session_state.data.get('ventas', [])

def get_ventas_simuladas():
    return st.session_state.data.get('ventas_simuladas', [])

def get_gastos():
    return st.session_state.data.get('gastos', [])

def get_remisiones():
    return st.session_state.data.get('remisiones_generadas', [])

def get_caja_diaria():
    return st.session_state.data.get('caja_diaria', {})

def get_caja_general():
    return st.session_state.data.get('caja_general', 10000)

def get_fondo_salarios():
    return st.session_state.data.get('fondo_salarios', 0)

# ============================================================
# FUNCIONES DE QR
# ============================================================

def generar_qr_remision(remision):
    qr_data = {
        "remision_id": remision.get('id'),
        "cliente": remision.get('cliente'),
        "fecha": remision.get('fecha'),
        "total": remision.get('total'),
        "tipo": remision.get('tipo', 'remision')
    }
    
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    return img_base64

# ============================================================
# INTERFAZ STREAMLIT
# ============================================================

def mostrar_login():
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <h1 style="color: #2c3e50;">♻️ RECICLAJE INDUSTRIAL</h1>
        <p style="color: #7f8c8d;">Sistemas Computerionales de México</p>
    """, unsafe_allow_html=True)
    
    if DRIVE_AVAILABLE and drive_sync.connected:
        st.markdown("""
        <p style="color: #27ae60; font-size: 14px; margin-top: 10px;">
            ✅ Sincronizado con Google Drive
        </p>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <p style="color: #e74c3c; font-size: 14px; margin-top: 10px;">
            ⚠️ Sin conexión a Google Drive
        </p>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario", placeholder="admin")
        password = st.text_input("Contraseña", type="password", placeholder="•••••••")
        submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submitted:
            if usuario == "admin" and password == "admin123":
                st.session_state.logged_in = True
                st.session_state.usuario = usuario
                st.session_state.rol = "administrador"
                st.rerun()
            elif usuario == "usuario" and password == "usuario123":
                st.session_state.logged_in = True
                st.session_state.usuario = usuario
                st.session_state.rol = "usuario"
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

def mostrar_sidebar():
    with st.sidebar:
        # ============================================
        # ENCABEZADO CON USUARIO
        # ============================================
        st.markdown(f"### 👤 {st.session_state.usuario} ({st.session_state.rol})")
        
        st.markdown("---")
        
        # ============================================
        # ESTADO DE SINCRONIZACIÓN
        # ============================================
        if DRIVE_AVAILABLE and drive_sync.connected:
            st.success("✅ Google Drive conectado")
            if hasattr(st.session_state, 'last_sync'):
                st.caption(f"Última sincronización: {st.session_state.last_sync.strftime('%H:%M:%S')}")
        else:
            st.warning("⚠️ Google Drive no conectado")
            if DRIVE_AVAILABLE:
                if st.button("🔄 Conectar Drive", use_container_width=True):
                    if drive_sync.connect():
                        st.rerun()
            else:
                st.caption("📌 Coloca credentials.json en la carpeta")
        
        st.markdown("---")
        
        # ============================================
        # BOTÓN DE SINCRONIZACIÓN - ¡AQUÍ ESTÁ!
        # ============================================
        # Este es el botón que debe aparecer en tu app
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("☁️ SINCRONIZAR AHORA", use_container_width=True, type="primary"):
                if DRIVE_AVAILABLE and drive_sync.connected:
                    with st.spinner("🔄 Sincronizando con Google Drive..."):
                        if sincronizar_con_drive():
                            st.success("✅ Sincronizado correctamente")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Error al sincronizar")
                else:
                    st.error("❌ Google Drive no disponible")
                    st.info("💡 Verifica que el archivo credentials.json esté en la carpeta")
        
        st.markdown("---")
        
        # ============================================
        # MENÚ DE NAVEGACIÓN
        # ============================================
        pages = {
            "inventario": "📊 Inventario",
            "caja": "💰 Caja Diaria",
            "clientes": "👥 Clientes",
            "materiales": "📦 Materiales",
            "ventas": "🛒 Ventas",
            "posventa": "📊 Pos Venta",
            "remisiones": "📋 Remisiones",
            "historial": "📜 Historial",
            "gastos": "💰 Gastos",
            "metricas": "📈 Métricas",
            "frecuencia": "📊 Frecuencia Clientes"
        }
        
        for page_id, page_name in pages.items():
            if st.button(page_name, use_container_width=True):
                st.session_state.page = page_id
                st.rerun()
        
        st.markdown("---")
        
        # ============================================
        # CERRAR SESIÓN
        # ============================================
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.caption(f"Versión Cloud - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
# PÁGINAS (simplificadas pero funcionales)
# ============================================================

def pagina_inventario():
    st.title("📊 Inventario")
    st.caption("Gestión de stock y materiales - Sincronizado con Google Drive")
    
    inventario = get_inventario()
    
    col1, col2, col3, col4 = st.columns(4)
    total_stock = sum(d.get("stock", 0) for d in inventario.values())
    total_valor = sum(redondear(d.get("stock", 0) * d.get("precio_venta", 0)) for d in inventario.values())
    total_materiales = len(inventario)
    total_inversion = sum(d.get("inversion_total", 0) for d in inventario.values())
    
    with col1:
        st.metric("📦 Total Stock", f"{total_stock:.2f} kg")
    with col2:
        st.metric("💎 Valor Inventario", f"${total_valor:.2f}")
    with col3:
        st.metric("📊 Materiales", total_materiales)
    with col4:
        st.metric("💰 Inversión Total", f"${total_inversion:.2f}")
    
    st.divider()
    
    if inventario:
        data = []
        for material, datos in sorted(inventario.items()):
            stock = datos.get("stock", 0)
            precio = datos.get("precio_venta", 0)
            seccion = datos.get("seccion", "inventario")
            precio_cliente = calcular_precio_cliente(material, precio)
            ganancia_kg = calcular_ganancia(material, precio)
            valor = redondear(stock * precio)
            inversion = datos.get("inversion_total", 0)
            total_comprado = datos.get("total_comprado", 0)
            ganancia_potencial = redondear(stock * ganancia_kg) if stock > 0 else 0
            
            data.append({
                "Material": material,
                "Sección": seccion.capitalize(),
                "Stock (kg)": stock,
                "Precio Venta": f"${precio:.2f}",
                "Precio Cliente": f"${precio_cliente:.2f}",
                "Ganancia/kg": f"${ganancia_kg:.2f}",
                "Inversión": f"${inversion:.2f}",
                "Total Comprado": f"{total_comprado:.2f}",
                "Valor Total": f"${valor:.2f}",
                "Ganancia Potencial": f"${ganancia_potencial:.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=400)
    else:
        st.info("No hay materiales en el inventario")

def pagina_caja():
    st.title("💰 Caja Diaria")
    
    caja_diaria = get_caja_diaria()
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    
    col1, col2, col3, col4 = st.columns(4)
    
    if fecha_actual in caja_diaria and caja_diaria[fecha_actual].get("abierta", False):
        registro = caja_diaria[fecha_actual]
        saldo = registro["apertura"] + registro.get("total_ingresos", 0) - registro.get("total_egresos", 0)
        
        with col1:
            st.metric("📌 Estado", "✅ Abierta")
        with col2:
            st.metric("💰 Apertura", f"${registro['apertura']:.2f}")
        with col3:
            st.metric("📈 Ingresos", f"${registro.get('total_ingresos', 0):.2f}")
        with col4:
            st.metric("💰 Saldo", f"${saldo:.2f}")
    else:
        with col1:
            st.metric("📌 Estado", "🔒 Cerrada")
        with col2:
            st.metric("💰 Apertura", "$0.00")
        with col3:
            st.metric("📈 Ingresos", "$0.00")
        with col4:
            st.metric("💰 Saldo", "$0.00")
    
    st.divider()
    st.subheader("📋 Movimientos del Día")
    
    if fecha_actual in caja_diaria:
        movimientos = caja_diaria[fecha_actual].get("movimientos", [])
        if movimientos:
            data = []
            for m in movimientos[-20:]:
                data.append({
                    "Hora": m.get("hora", ""),
                    "Tipo": "💰 Ingreso" if m.get("tipo") == "ingreso" else "💸 Egreso",
                    "Concepto": m.get("concepto", ""),
                    "Monto": f"${m.get('monto', 0):.2f}",
                    "Usuario": m.get("usuario", "")
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay movimientos registrados para hoy")
    else:
        st.info("No hay caja abierta para hoy")

def pagina_clientes():
    st.title("👥 Clientes")
    
    clientes = get_clientes()
    
    with st.form("agregar_cliente"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre del cliente")
        with col2:
            telefono = st.text_input("Teléfono")
        
        if st.form_submit_button("Agregar Cliente", use_container_width=True):
            if nombre:
                cliente_id = len(clientes) + 1
                clientes.append({"id": cliente_id, "nombre": nombre, "telefono": telefono})
                st.session_state.data['clientes'] = clientes
                guardar_datos()
                st.success(f"✅ Cliente '{nombre}' agregado")
                st.rerun()
            else:
                st.error("El nombre es obligatorio")
    
    st.divider()
    
    if clientes:
        df = pd.DataFrame(clientes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay clientes registrados")

def pagina_materiales():
    st.title("📦 Materiales")
    
    materiales = get_materiales()
    secciones = list(materiales.keys())
    
    seccion_sel = st.selectbox("Seleccionar sección", secciones)
    
    if seccion_sel in materiales:
        items = materiales[seccion_sel]
        
        st.subheader(f"📁 {seccion_sel.upper()}")
        
        with st.form("agregar_material"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nombre = st.text_input("Material")
            with col2:
                precio = st.number_input("Precio Venta ($/kg)", min_value=0.0, step=0.01, format="%.2f")
            with col3:
                empresa = st.selectbox("Empresa", EMPRESAS_DISPONIBLES)
            
            if st.form_submit_button("Agregar Material", use_container_width=True):
                if nombre:
                    items.append({"nombre": nombre, "precio_venta": precio, "empresa": empresa})
                    st.session_state.data['materiales'][seccion_sel] = items
                    guardar_datos()
                    st.success(f"✅ Material '{nombre}' agregado")
                    st.rerun()
                else:
                    st.error("El nombre es obligatorio")
        
        if items:
            data = []
            for m in items:
                nombre = m['nombre']
                precio_venta = m.get('precio_venta', 0)
                precio_cliente = calcular_precio_cliente(nombre, precio_venta)
                ganancia = calcular_ganancia(nombre, precio_venta)
                porcentaje = obtener_porcentaje_ganancia(nombre) * 100
                
                data.append({
                    "Material": nombre,
                    "Precio Venta": f"${precio_venta:.2f}",
                    "Precio Cliente": f"${precio_cliente:.2f}",
                    "Ganancia": f"${ganancia:.2f} ({porcentaje:.1f}%)",
                    "Empresa": m.get('empresa', 'Sin asignar')
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No hay materiales en {seccion_sel}")

def pagina_ventas():
    st.title("🛒 Ventas")
    
    clientes = get_clientes()
    inventario = get_inventario()
    ventas = get_ventas()
    
    with st.form("registrar_venta"):
        st.subheader("📝 Nueva Venta")
        
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.selectbox("Cliente", [c['nombre'] for c in clientes])
            materiales_con_stock = [m for m, d in inventario.items() if d.get("stock", 0) > 0]
            material = st.selectbox("Material", materiales_con_stock)
        
        with col2:
            cantidad = st.number_input("Cantidad (kg)", min_value=0.01, step=0.1, format="%.2f")
            if material in inventario:
                stock_disp = inventario[material].get("stock", 0)
                st.caption(f"📦 Stock disponible: {stock_disp:.2f} kg")
        
        if st.form_submit_button("✅ Registrar Venta", use_container_width=True):
            if cliente and material and cantidad > 0:
                if material in inventario:
                    stock_disp = inventario[material].get("stock", 0)
                    if cantidad <= stock_disp:
                        precio_venta = inventario[material].get("precio_venta", 0)
                        precio_cliente = calcular_precio_cliente(material, precio_venta)
                        ganancia_kg = calcular_ganancia(material, precio_venta)
                        total = redondear(cantidad * precio_cliente)
                        ganancia_total = redondear(cantidad * ganancia_kg)
                        
                        inventario[material]["stock"] = redondear(stock_disp - cantidad)
                        
                        venta = {
                            "id": len(ventas) + 1,
                            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "cliente": cliente,
                            "material": material,
                            "cantidad": cantidad,
                            "precio_unitario": precio_venta,
                            "precio_cliente": precio_cliente,
                            "ganancia": ganancia_total,
                            "porcentaje_ganancia": obtener_porcentaje_ganancia(material) * 100,
                            "total": total
                        }
                        ventas.append(venta)
                        
                        caja_actual = get_caja_general()
                        st.session_state.data['caja_general'] = redondear(caja_actual + total)
                        
                        st.session_state.data['inventario'] = inventario
                        st.session_state.data['ventas'] = ventas
                        guardar_datos()
                        
                        st.success(f"✅ Venta registrada: ${total:.2f}")
                        st.rerun()
                    else:
                        st.error(f"⚠️ Stock insuficiente. Disponible: {stock_disp:.2f} kg")
                else:
                    st.error("Material no encontrado en inventario")
            else:
                st.error("Complete todos los campos")
    
    st.divider()
    st.subheader("📜 Historial de Ventas")
    
    if ventas:
        data = []
        for v in sorted(ventas, key=lambda x: x.get('fecha', ''), reverse=True)[:50]:
            data.append({
                "ID": v.get('id', ''),
                "Fecha": v.get('fecha', '')[:16],
                "Cliente": v.get('cliente', ''),
                "Material": v.get('material', ''),
                "Cantidad": v.get('cantidad', 0),
                "Total": f"${v.get('total', 0):.2f}",
                "Ganancia": f"${v.get('ganancia', 0):.2f}"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay ventas registradas")

def pagina_posventa():
    st.title("📊 Pos Venta")
    st.info("📌 Esta funcionalidad está disponible en la versión de escritorio.")

def pagina_remisiones():
    st.title("📋 Remisiones")
    
    remisiones = get_remisiones()
    
    if remisiones:
        data = []
        for r in sorted(remisiones, key=lambda x: x.get('id', 0), reverse=True):
            tipo = r.get('tipo', 'remision')
            tipo_mostrar = {
                'remision': '📋 Remisión',
                'venta': '🛒 Venta',
                'compra': '📦 Compra'
            }.get(tipo, '📋 Remisión')
            
            data.append({
                "ID": r.get('id', ''),
                "Fecha": r.get('fecha', '')[:16],
                "Cliente": r.get('cliente', ''),
                "Tipo": tipo_mostrar,
                "Items": len(r.get('items', [])),
                "Total": f"${r.get('total', 0):.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay remisiones generadas")

def pagina_historial():
    st.title("📜 Historial")
    
    compras = get_compras()
    compras_mayoreo = get_compras_mayoreo()
    ventas = get_ventas()
    
    transacciones = []
    
    for c in compras:
        transacciones.append({
            "fecha": c.get('fecha', ''),
            "cliente": c.get('cliente', ''),
            "material": c.get('material', ''),
            "cantidad": c.get('cantidad', 0),
            "total": c.get('total', 0),
            "tipo": c.get('tipo_precio', 'compra')
        })
    
    for c in compras_mayoreo:
        transacciones.append({
            "fecha": c.get('fecha', ''),
            "cliente": c.get('cliente', ''),
            "material": c.get('material', ''),
            "cantidad": c.get('cantidad', 0),
            "total": c.get('total', 0),
            "tipo": "mayoreo"
        })
    
    for v in ventas:
        transacciones.append({
            "fecha": v.get('fecha', ''),
            "cliente": v.get('cliente', ''),
            "material": v.get('material', ''),
            "cantidad": v.get('cantidad', 0),
            "total": v.get('total', 0),
            "tipo": "venta_inventario"
        })
    
    if transacciones:
        transacciones.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        data = []
        for t in transacciones[:100]:
            tipo_mostrar = {
                'cliente': 'Cliente',
                'mayoreo': 'Mayoreo',
                'compra_inventario': 'Compra Inv',
                'venta_inventario': 'Venta Inv'
            }.get(t.get('tipo', ''), t.get('tipo', ''))
            
            data.append({
                "Fecha": t.get('fecha', '')[:16],
                "Cliente": t.get('cliente', ''),
                "Material": t.get('material', ''),
                "Cantidad": f"{t.get('cantidad', 0):.2f}",
                "Total": f"${t.get('total', 0):.2f}",
                "Tipo": tipo_mostrar
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay transacciones registradas")

def pagina_gastos():
    st.title("💰 Gastos")
    
    gastos = get_gastos()
    
    with st.form("registrar_gasto"):
        st.subheader("📝 Nuevo Gasto")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            concepto = st.text_input("Concepto")
        with col2:
            monto = st.number_input("Monto ($)", min_value=0.01, step=0.01, format="%.2f")
        with col3:
            categoria = st.selectbox("Categoría", ["Operativos", "Salarios", "Compras", "Mantenimiento", "Servicios", "Otros"])
        
        if st.form_submit_button("Registrar Gasto", use_container_width=True):
            if concepto and monto > 0:
                gasto = {
                    "id": len(gastos) + 1,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "concepto": concepto,
                    "monto": monto,
                    "categoria": categoria,
                    "usuario": st.session_state.usuario
                }
                gastos.append(gasto)
                
                caja_actual = get_caja_general()
                st.session_state.data['caja_general'] = redondear(caja_actual - monto)
                st.session_state.data['gastos'] = gastos
                guardar_datos()
                
                st.success(f"✅ Gasto registrado: ${monto:.2f}")
                st.rerun()
            else:
                st.error("Complete todos los campos")
    
    st.divider()
    st.subheader("📋 Historial de Gastos")
    
    if gastos:
        total_gastos = sum(g.get('monto', 0) for g in gastos)
        st.metric("💰 Total Gastos", f"${total_gastos:.2f}")
        
        data = []
        for g in sorted(gastos, key=lambda x: x.get('fecha', ''), reverse=True)[:50]:
            data.append({
                "ID": g.get('id', ''),
                "Fecha": g.get('fecha', '')[:16],
                "Concepto": g.get('concepto', ''),
                "Monto": f"${g.get('monto', 0):.2f}",
                "Categoría": g.get('categoria', ''),
                "Usuario": g.get('usuario', '')
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay gastos registrados")

def pagina_metricas():
    st.title("📈 Métricas")
    
    inventario = get_inventario()
    ventas = get_ventas()
    gastos = get_gastos()
    remisiones = get_remisiones()
    caja_general = get_caja_general()
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_stock = sum(d.get("stock", 0) for d in inventario.values())
    total_valor = sum(redondear(d.get("stock", 0) * d.get("precio_venta", 0)) for d in inventario.values())
    total_inversion = sum(d.get("inversion_total", 0) for d in inventario.values())
    total_ventas = sum(v.get("total", 0) for v in ventas)
    total_gastos = sum(g.get("monto", 0) for g in gastos)
    total_remisiones = len(remisiones)
    
    ganancia_potencial = 0
    for material, datos in inventario.items():
        stock = datos.get("stock", 0)
        precio_venta = datos.get("precio_venta", 0)
        if stock > 0:
            ganancia_potencial += redondear(stock * calcular_ganancia(material, precio_venta))
    
    with col1:
        st.metric("💰 Caja General", f"${caja_general:.2f}")
    with col2:
        st.metric("📦 Total Stock", f"{total_stock:.2f} kg")
    with col3:
        st.metric("💎 Valor Inventario", f"${total_valor:.2f}")
    with col4:
        st.metric("💰 Inversión Total", f"${total_inversion:.2f}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 Total Ventas", f"${total_ventas:.2f}")
    with col2:
        st.metric("💰 Ganancia Potencial", f"${ganancia_potencial:.2f}")
    with col3:
        st.metric("📈 Total Gastos", f"${total_gastos:.2f}")
    with col4:
        st.metric("📋 Total Remisiones", total_remisiones)
    
    st.divider()
    st.subheader("📊 Resumen por Categoría")
    
    categorias = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"]
    
    data_cat = []
    for cat in categorias:
        stock_cat = 0
        valor_cat = 0
        inversion_cat = 0
        ganancia_cat = 0
        cantidad = 0
        
        for material, datos in inventario.items():
            if datos.get("seccion") == cat:
                stock = datos.get("stock", 0)
                precio_venta = datos.get("precio_venta", 0)
                stock_cat += stock
                valor_cat += redondear(stock * precio_venta)
                inversion_cat += datos.get("inversion_total", 0)
                if stock > 0:
                    ganancia_cat += redondear(stock * calcular_ganancia(material, precio_venta))
                cantidad += 1
        
        data_cat.append({
            "Categoría": cat.upper(),
            "Materiales": cantidad,
            "Stock (kg)": f"{stock_cat:.2f}",
            "Valor": f"${valor_cat:.2f}",
            "Inversión": f"${inversion_cat:.2f}",
            "Ganancia": f"${ganancia_cat:.2f}"
        })
    
    if data_cat:
        df = pd.DataFrame(data_cat)
        st.dataframe(df, use_container_width=True)

def pagina_frecuencia():
    st.title("📊 Frecuencia de Clientes")
    
    ventas = get_ventas()
    
    frecuencia = {}
    for venta in ventas:
        cliente = venta.get('cliente')
        if not cliente:
            continue
        
        if cliente not in frecuencia:
            frecuencia[cliente] = {
                "total_visitas": 0,
                "ultima_visita": "",
                "total_kg": 0,
                "total_compras": 0
            }
        
        frecuencia[cliente]["total_visitas"] += 1
        fecha = venta.get('fecha', '')
        if fecha and (not frecuencia[cliente]["ultima_visita"] or fecha > frecuencia[cliente]["ultima_visita"]):
            frecuencia[cliente]["ultima_visita"] = fecha[:16]
        frecuencia[cliente]["total_kg"] += venta.get('cantidad', 0)
        frecuencia[cliente]["total_compras"] += venta.get('total', 0)
    
    if frecuencia:
        data = []
        for cliente, datos in sorted(frecuencia.items(), key=lambda x: x[1]["total_visitas"], reverse=True):
            data.append({
                "Cliente": cliente,
                "Visitas": datos["total_visitas"],
                "Última Visita": datos["ultima_visita"],
                "Total kg": f"{redondear(datos['total_kg']):.2f}",
                "Total Compras": f"${datos['total_compras']:.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        if data:
            top_cliente = data[0]
            st.metric(
                "🏆 Cliente Más Frecuente",
                top_cliente["Cliente"],
                f"{top_cliente['Visitas']} visitas"
            )
    else:
        st.info("No hay datos de clientes para mostrar")

# ============================================================
# MAIN
# ============================================================

def main():
    st.set_page_config(
        page_title="♻️ Reciclaje Industrial",
        page_icon="♻️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.page = "inventario"
        st.session_state.data_loaded = False
    
    if DRIVE_AVAILABLE and 'drive_initialized' not in st.session_state:
        with st.spinner("Conectando con Google Drive..."):
            drive_sync.connect()
            st.session_state.drive_initialized = True
    
    if not st.session_state.data_loaded:
        cargar_datos()
    
    if not st.session_state.logged_in:
        mostrar_login()
        return
    
    mostrar_sidebar()
    
    page = st.session_state.get('page', 'inventario')
    
    if page == "inventario":
        pagina_inventario()
    elif page == "caja":
        pagina_caja()
    elif page == "clientes":
        pagina_clientes()
    elif page == "materiales":
        pagina_materiales()
    elif page == "ventas":
        pagina_ventas()
    elif page == "posventa":
        pagina_posventa()
    elif page == "remisiones":
        pagina_remisiones()
    elif page == "historial":
        pagina_historial()
    elif page == "gastos":
        pagina_gastos()
    elif page == "metricas":
        pagina_metricas()
    elif page == "frecuencia":
        pagina_frecuencia()
    else:
        pagina_inventario()
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"♻️ Reciclaje Industrial - Cloud v3.0")
    with col2:
        if DRIVE_AVAILABLE and drive_sync.connected:
            st.caption("✅ Sincronizado con Google Drive")
        else:
            st.caption("⚠️ Sin conexión a Google Drive")
    with col3:
        st.caption(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
