# app_streamlit.py
# Sistema de Reciclaje Industrial - Versión Cloud
# Desplegar en: https://share.streamlit.io/

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

# ============================================================
# CONFIGURACIÓN DE ALMACENAMIENTO EN LA NUBE
# ============================================================

# Para Streamlit Cloud, usamos st.session_state como base de datos
# Los datos se guardan en un archivo JSON que se almacena en la nube

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

# ============================================================
# GESTOR DE DATOS
# ============================================================

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

def cargar_datos():
    """Carga los datos desde session_state o archivo"""
    if 'data' not in st.session_state:
        # Intentar cargar desde archivo
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.session_state.data = data
                st.session_state.data_loaded = True
                return data
            except:
                pass
        
        # Si no hay archivo, inicializar datos por defecto
        st.session_state.data = inicializar_datos_por_defecto()
        st.session_state.data_loaded = True
        guardar_datos()
    
    return st.session_state.data

def guardar_datos():
    """Guarda los datos en session_state y archivo"""
    if 'data' in st.session_state:
        try:
            # Guardar en archivo
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.data, f, indent=2, ensure_ascii=False)
        except:
            pass
        return True
    return False

def guardar_caja_diaria():
    """Guarda la caja diaria"""
    if 'data' in st.session_state:
        try:
            caja_file = "caja_diaria.json"
            with open(caja_file, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.data.get('caja_diaria', {}), f, indent=2, ensure_ascii=False)
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
    """Muestra la pantalla de login"""
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <h1 style="color: #2c3e50;">♻️ RECICLAJE INDUSTRIAL</h1>
        <p style="color: #7f8c8d;">Sistemas Computerionales de México</p>
    </div>
    """, unsafe_allow_html=True)
    
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
    """Muestra la barra lateral con navegación"""
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.usuario} ({st.session_state.rol})")
        st.divider()
        
        if st.button("📊 Inventario", use_container_width=True):
            st.session_state.page = "inventario"
            st.rerun()
        
        if st.button("💰 Caja Diaria", use_container_width=True):
            st.session_state.page = "caja"
            st.rerun()
        
        if st.button("👥 Clientes", use_container_width=True):
            st.session_state.page = "clientes"
            st.rerun()
        
        if st.button("📦 Materiales", use_container_width=True):
            st.session_state.page = "materiales"
            st.rerun()
        
        if st.button("🛒 Ventas", use_container_width=True):
            st.session_state.page = "ventas"
            st.rerun()
        
        if st.button("📊 Pos Venta", use_container_width=True):
            st.session_state.page = "posventa"
            st.rerun()
        
        if st.button("📋 Remisiones", use_container_width=True):
            st.session_state.page = "remisiones"
            st.rerun()
        
        if st.button("📜 Historial", use_container_width=True):
            st.session_state.page = "historial"
            st.rerun()
        
        if st.button("💰 Gastos", use_container_width=True):
            st.session_state.page = "gastos"
            st.rerun()
        
        if st.button("📈 Métricas", use_container_width=True):
            st.session_state.page = "metricas"
            st.rerun()
        
        if st.button("📊 Frecuencia Clientes", use_container_width=True):
            st.session_state.page = "frecuencia"
            st.rerun()
        
        st.divider()
        
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
        
        st.markdown("---")
        st.caption(f"Versión Cloud - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================
# PÁGINA: INVENTARIO
# ============================================================

def pagina_inventario():
    st.title("📊 Inventario")
    st.caption("Gestión de stock y materiales")
    
    inventario = get_inventario()
    
    # Resumen
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
    
    # Formulario para agregar/editar
    with st.expander("➕ Agregar/Editar Material", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Material")
            seccion = st.selectbox("Sección", ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"])
            stock = st.number_input("Stock (kg)", min_value=0.0, step=0.1, format="%.2f")
        
        with col2:
            precio_venta = st.number_input("Precio Venta ($/kg)", min_value=0.0, step=0.01, format="%.2f")
            precio_cliente = st.number_input("Precio Cliente ($/kg)", min_value=0.0, step=0.01, format="%.2f")
            descripcion = st.text_input("Descripción")
        
        if st.button("Guardar Material", use_container_width=True):
            if nombre:
                inventario[nombre] = {
                    "stock": stock,
                    "precio_venta": precio_venta,
                    "precio_compra_cliente": precio_cliente,
                    "seccion": seccion,
                    "descripcion": descripcion,
                    "inversion_total": 0,
                    "inversion_promedio": 0,
                    "total_comprado": 0
                }
                st.session_state.data['inventario'] = inventario
                guardar_datos()
                st.success(f"✅ Material '{nombre}' guardado correctamente")
                st.rerun()
            else:
                st.error("El nombre del material es obligatorio")
    
    # Tabla de inventario
    if inventario:
        data = []
        for material, datos in inventario.items():
            stock = datos.get("stock", 0)
            precio = datos.get("precio_venta", 0)
            precio_cli = calcular_precio_cliente(material, precio)
            ganancia_kg = calcular_ganancia(material, precio)
            valor = redondear(stock * precio)
            
            data.append({
                "Material": material,
                "Sección": datos.get("seccion", ""),
                "Stock (kg)": stock,
                "Precio Venta": precio,
                "Precio Cliente": precio_cli,
                "Ganancia/kg": ganancia_kg,
                "Valor Total": valor
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, height=400)
        
        # Botones de acción
        col1, col2, col3 = st.columns(3)
        with col1:
            materiales = list(inventario.keys())
            material_sel = st.selectbox("Seleccionar material para editar", materiales)
        
        with col2:
            if st.button("✏️ Editar Seleccionado"):
                st.session_state.edit_material = material_sel
                st.rerun()
        
        with col3:
            if st.button("🗑️ Eliminar Seleccionado"):
                if material_sel in inventario:
                    del inventario[material_sel]
                    st.session_state.data['inventario'] = inventario
                    guardar_datos()
                    st.success(f"✅ Material eliminado")
                    st.rerun()
        
        # Editar material seleccionado
        if 'edit_material' in st.session_state and st.session_state.edit_material:
            mat = st.session_state.edit_material
            if mat in inventario:
                with st.expander(f"✏️ Editando: {mat}", expanded=True):
                    datos = inventario[mat]
                    nuevo_nombre = st.text_input("Nombre", mat)
                    nueva_seccion = st.selectbox("Sección", ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"], 
                                                index=["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"].index(datos.get("seccion", "ferrosos")))
                    nuevo_stock = st.number_input("Stock (kg)", min_value=0.0, value=float(datos.get("stock", 0)), step=0.1, format="%.2f")
                    nuevo_precio = st.number_input("Precio Venta ($/kg)", min_value=0.0, value=float(datos.get("precio_venta", 0)), step=0.01, format="%.2f")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Guardar Cambios"):
                            if nuevo_nombre and nuevo_nombre != mat:
                                del inventario[mat]
                            inventario[nuevo_nombre] = {
                                "stock": nuevo_stock,
                                "precio_venta": nuevo_precio,
                                "precio_compra_cliente": calcular_precio_cliente(nuevo_nombre, nuevo_precio),
                                "seccion": nueva_seccion,
                                "descripcion": datos.get("descripcion", ""),
                                "inversion_total": datos.get("inversion_total", 0),
                                "inversion_promedio": datos.get("inversion_promedio", 0),
                                "total_comprado": datos.get("total_comprado", 0)
                            }
                            st.session_state.data['inventario'] = inventario
                            guardar_datos()
                            del st.session_state.edit_material
                            st.success("✅ Material actualizado")
                            st.rerun()
                    
                    with col2:
                        if st.button("Cancelar"):
                            del st.session_state.edit_material
                            st.rerun()
    else:
        st.info("No hay materiales en el inventario. Agrega uno usando el formulario.")

# ============================================================
# PÁGINA: CAJA DIARIA
# ============================================================

def pagina_caja():
    st.title("💰 Caja Diaria")
    st.caption("Gestión de caja y movimientos")
    
    caja_diaria = get_caja_diaria()
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    
    # Estado de caja
    col1, col2, col3, col4 = st.columns(4)
    
    if fecha_actual in caja_diaria and caja_diaria[fecha_actual].get("abierta", False):
        registro = caja_diaria[fecha_actual]
        saldo = registro["apertura"] + registro.get("total_ingresos", 0) - registro.get("total_egresos", 0)
        
        with col1:
            st.metric("📌 Estado", "✅ Abierta", delta="Caja activa")
        with col2:
            st.metric("💰 Apertura", f"${registro['apertura']:.2f}")
        with col3:
            st.metric("📈 Ingresos", f"${registro.get('total_ingresos', 0):.2f}", delta="+")
        with col4:
            st.metric("💰 Saldo", f"${saldo:.2f}")
        
        if st.button("🔒 Cerrar Caja", use_container_width=True):
            if st.button("Confirmar Cierre"):
                registro["cierre"] = saldo
                registro["abierta"] = False
                registro["hora_cierre"] = datetime.now().strftime("%H:%M:%S")
                st.session_state.data['caja_diaria'][fecha_actual] = registro
                guardar_datos()
                guardar_caja_diaria()
                st.success("✅ Caja cerrada correctamente")
                st.rerun()
    else:
        with col1:
            st.metric("📌 Estado", "🔒 Cerrada")
        with col2:
            st.metric("💰 Apertura", "$0.00")
        with col3:
            st.metric("📈 Ingresos", "$0.00")
        with col4:
            st.metric("💰 Saldo", "$0.00")
        
        if st.button("🔓 Abrir Caja", use_container_width=True):
            monto = st.number_input("Monto inicial en caja:", min_value=0.0, value=float(get_caja_general()), step=100.0)
            if st.button("Confirmar Apertura"):
                caja_diaria[fecha_actual] = {
                    "fecha": fecha_actual,
                    "apertura": monto,
                    "cierre": 0,
                    "abierta": True,
                    "movimientos": [],
                    "total_ingresos": 0,
                    "total_egresos": 0,
                    "hora_apertura": datetime.now().strftime("%H:%M:%S"),
                    "hora_cierre": "",
                    "usuario": st.session_state.usuario
                }
                st.session_state.data['caja_diaria'] = caja_diaria
                st.session_state.data['caja_general'] = monto
                guardar_datos()
                guardar_caja_diaria()
                st.success("✅ Caja abierta correctamente")
                st.rerun()
    
    st.divider()
    
    # Movimientos del día
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
                    "Monto": m.get("monto", 0),
                    "Usuario": m.get("usuario", "")
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No hay movimientos registrados para hoy")
    else:
        st.info("No hay caja abierta para hoy")
    
    st.divider()
    
    # Historial de caja
    st.subheader("📊 Historial de Caja")
    
    historial = []
    for fecha, registro in sorted(caja_diaria.items(), reverse=True):
        if not registro.get("abierta", True):
            historial.append({
                "Fecha": fecha,
                "Apertura": registro.get("apertura", 0),
                "Cierre": registro.get("cierre", 0),
                "Ingresos": registro.get("total_ingresos", 0),
                "Egresos": registro.get("total_egresos", 0),
                "Usuario": registro.get("usuario", "N/A")
            })
    
    if historial:
        df = pd.DataFrame(historial)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay historial de caja")

# ============================================================
# PÁGINA: CLIENTES
# ============================================================

def pagina_clientes():
    st.title("👥 Clientes")
    st.caption("Gestión de clientes")
    
    clientes = get_clientes()
    
    # Formulario para agregar cliente
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
    
    # Lista de clientes
    if clientes:
        df = pd.DataFrame(clientes)
        st.dataframe(df, use_container_width=True)
        
        # Eliminar cliente
        nombres = [c['nombre'] for c in clientes]
        cliente_eliminar = st.selectbox("Seleccionar cliente para eliminar", nombres)
        
        if st.button("🗑️ Eliminar Cliente", use_container_width=True):
            if st.checkbox("Confirmar eliminación"):
                st.session_state.data['clientes'] = [c for c in clientes if c['nombre'] != cliente_eliminar]
                guardar_datos()
                st.success(f"✅ Cliente eliminado")
                st.rerun()
    else:
        st.info("No hay clientes registrados")

# ============================================================
# PÁGINA: MATERIALES
# ============================================================

def pagina_materiales():
    st.title("📦 Materiales")
    st.caption("Gestión de materiales por sección")
    
    materiales = get_materiales()
    secciones = list(materiales.keys())
    
    seccion_sel = st.selectbox("Seleccionar sección", secciones)
    
    if seccion_sel in materiales:
        items = materiales[seccion_sel]
        
        st.subheader(f"📁 {seccion_sel.upper()}")
        
        # Formulario para agregar material
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
        
        # Lista de materiales
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
                    "Precio Venta": precio_venta,
                    "Precio Cliente": precio_cliente,
                    "Ganancia": f"${ganancia:.2f} ({porcentaje:.1f}%)",
                    "Empresa": m.get('empresa', 'Sin asignar')
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"No hay materiales en {seccion_sel}")

# ============================================================
# PÁGINA: VENTAS
# ============================================================

def pagina_ventas():
    st.title("🛒 Ventas")
    st.caption("Registro de ventas de inventario")
    
    clientes = get_clientes()
    inventario = get_inventario()
    ventas = get_ventas()
    
    # Formulario de venta
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
                        
                        # Actualizar stock
                        inventario[material]["stock"] = redondear(stock_disp - cantidad)
                        
                        # Registrar venta
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
                            "total": total,
                            "stock_anterior": stock_disp,
                            "stock_actual": inventario[material]["stock"],
                            "seccion": inventario[material].get("seccion", "inventario")
                        }
                        ventas.append(venta)
                        
                        # Actualizar caja
                        caja_actual = get_caja_general()
                        st.session_state.data['caja_general'] = redondear(caja_actual + total)
                        
                        # Guardar
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
    
    # Historial de ventas
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
                "Total": v.get('total', 0),
                "Ganancia": v.get('ganancia', 0)
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay ventas registradas")

# ============================================================
# PÁGINA: POS VENTA
# ============================================================

def pagina_posventa():
    st.title("📊 Pos Venta")
    st.caption("Simulación de ventas a empresas")
    
    materiales_pos = get_materiales().get('pos_venta', [])
    ventas_sim = get_ventas_simuladas()
    inventario = get_inventario()
    
    st.subheader("📝 Registrar Venta Simulada")
    
    with st.form("registrar_posventa"):
        col1, col2, col3 = st.columns(3)
        with col1:
            empresa = st.selectbox("Empresa", EMPRESAS_POS_VENTA)
        with col2:
            material_pos = st.selectbox("Material", [m['nombre'] for m in materiales_pos])
        with col3:
            cantidad_pos = st.number_input("Cantidad (kg)", min_value=0.01, step=0.1, format="%.2f")
        
        if st.form_submit_button("✅ Registrar Venta Simulada", use_container_width=True):
            if empresa and material_pos and cantidad_pos > 0:
                # Buscar precio
                precio = 0
                for m in materiales_pos:
                    if m['nombre'] == material_pos:
                        precio = m.get('precio_venta', 0)
                        break
                
                if precio > 0:
                    total = redondear(cantidad_pos * precio)
                    
                    venta = {
                        "id": len(ventas_sim) + 1,
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "empresa": empresa,
                        "material": material_pos,
                        "cantidad": cantidad_pos,
                        "precio_unitario": precio,
                        "total": total,
                        "stock_actual": inventario.get(material_pos, {}).get("stock", 0)
                    }
                    ventas_sim.append(venta)
                    st.session_state.data['ventas_simuladas'] = ventas_sim
                    guardar_datos()
                    st.success(f"✅ Venta simulada registrada: ${total:.2f}")
                    st.rerun()
                else:
                    st.error("Material sin precio configurado")
            else:
                st.error("Complete todos los campos")
    
    st.divider()
    
    # Lista de ventas simuladas
    st.subheader("📋 Ventas Simuladas")
    
    if ventas_sim:
        total_sim = sum(v.get('total', 0) for v in ventas_sim)
        st.metric("💰 Total Simulado", f"${total_sim:.2f}")
        
        data = []
        for v in sorted(ventas_sim, key=lambda x: x.get('id', 0), reverse=True):
            data.append({
                "ID": v.get('id', ''),
                "Fecha": v.get('fecha', '')[:16],
                "Empresa": v.get('empresa', ''),
                "Material": v.get('material', ''),
                "Cantidad": v.get('cantidad', 0),
                "Total": v.get('total', 0)
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay ventas simuladas registradas")

# ============================================================
# PÁGINA: REMISIONES
# ============================================================

def pagina_remisiones():
    st.title("📋 Remisiones")
    st.caption("Gestión de remisiones generadas")
    
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
            
            ganancia_total = 0
            for item in r.get('items', []):
                ganancia_total += item.get('ganancia', 0)
            
            data.append({
                "ID": r.get('id', ''),
                "Fecha": r.get('fecha', '')[:16],
                "Cliente": r.get('cliente', ''),
                "Tipo": tipo_mostrar,
                "Items": len(r.get('items', [])),
                "Total": r.get('total', 0),
                "Ganancia": ganancia_total
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Descargar remisión
        ids = [r.get('id') for r in remisiones]
        remision_id = st.selectbox("Seleccionar remisión para descargar", ids)
        
        if st.button("📥 Descargar Remisión", use_container_width=True):
            remision = None
            for r in remisiones:
                if r.get('id') == remision_id:
                    remision = r
                    break
            
            if remision:
                # Generar HTML
                html = generar_html_nota(remision)
                st.download_button(
                    label="📄 Descargar HTML",
                    data=html,
                    file_name=f"remision_{remision_id}.html",
                    mime="text/html",
                    use_container_width=True
                )
    else:
        st.info("No hay remisiones generadas")

def generar_html_nota(remision):
    tipo = remision.get('tipo', 'remision')
    titulo = "NOTA DE REMISIÓN" if tipo == 'remision' else "NOTA DE VENTA" if tipo == 'venta' else "NOTA DE COMPRA"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{titulo} #{remision['id']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 20px; }}
            .header h1 {{ color: #2c3e50; }}
            .info {{ margin: 20px 0; }}
            .info table {{ width: 100%; }}
            .info td {{ padding: 5px; }}
            table.items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            table.items th {{ background: #2c3e50; color: white; padding: 10px; text-align: left; }}
            table.items td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            .total {{ text-align: right; font-size: 18px; font-weight: bold; margin: 20px 0; }}
            .footer {{ margin-top: 40px; text-align: center; color: #7f8c8d; font-size: 12px; }}
            .qr {{ text-align: center; margin: 20px 0; }}
            .tipo-tag {{ display: inline-block; padding: 3px 12px; border-radius: 15px; font-size: 12px; font-weight: bold; }}
            .tipo-remision {{ background: #3498db; color: white; }}
            .tipo-venta {{ background: #27ae60; color: white; }}
            .tipo-compra {{ background: #f39c12; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>♻️ RECICLAJE INDUSTRIAL</h1>
            <p>Sistemas Computerionales de México</p>
            <h2>{titulo} #{remision['id']}</h2>
            <span class="tipo-tag tipo-{tipo}">{tipo.upper()}</span>
        </div>
        
        <div class="info">
            <table>
                <tr><td><strong>Fecha:</strong></td><td>{remision['fecha']}</td></tr>
                <tr><td><strong>Cliente:</strong></td><td>{remision['cliente']}</td></tr>
                <tr><td><strong>Usuario:</strong></td><td>{remision.get('usuario', 'N/A')}</td></tr>
            </table>
        </div>
        
        <table class="items">
            <thead>
                <tr>
                    <th>Material</th>
                    <th>Cantidad (kg)</th>
                    <th>Precio ($/kg)</th>
                    <th>Total ($)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for item in remision.get('items', []):
        html += f"""
                <tr>
                    <td>{item['material']}</td>
                    <td>{item['cantidad']:.2f}</td>
                    <td>${item['precio']:.2f}</td>
                    <td>${item['total']:.2f}</td>
                </tr>
        """
    
    html += f"""
            </tbody>
        </table>
        
        <div class="total">
            TOTAL: ${remision['total']:.2f}
        </div>
        
        <div class="footer">
            <p>Este documento es una {titulo.lower()}.</p>
            <p>Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    return html

# ============================================================
# PÁGINA: HISTORIAL
# ============================================================

def pagina_historial():
    st.title("📜 Historial")
    st.caption("Historial completo de transacciones")
    
    compras = get_compras()
    compras_mayoreo = get_compras_mayoreo() if 'compras_mayoreo' in st.session_state.data else []
    ventas = get_ventas()
    
    # Combinar todas las transacciones
    transacciones = []
    
    for c in compras:
        transacciones.append({
            "id": c.get('id', ''),
            "fecha": c.get('fecha', ''),
            "cliente": c.get('cliente', ''),
            "material": c.get('material', ''),
            "cantidad": c.get('cantidad', 0),
            "precio": c.get('precio_unitario', 0),
            "total": c.get('total', 0),
            "tipo": c.get('tipo_precio', 'compra'),
            "ganancia": c.get('ganancia', 0)
        })
    
    for c in compras_mayoreo:
        transacciones.append({
            "id": c.get('id', ''),
            "fecha": c.get('fecha', ''),
            "cliente": c.get('cliente', ''),
            "material": c.get('material', ''),
            "cantidad": c.get('cantidad', 0),
            "precio": c.get('precio_unitario', 0),
            "total": c.get('total', 0),
            "tipo": "mayoreo",
            "ganancia": c.get('ganancia', 0)
        })
    
    for v in ventas:
        transacciones.append({
            "id": v.get('id', ''),
            "fecha": v.get('fecha', ''),
            "cliente": v.get('cliente', ''),
            "material": v.get('material', ''),
            "cantidad": v.get('cantidad', 0),
            "precio": v.get('precio_unitario', 0),
            "total": v.get('total', 0),
            "tipo": "venta_inventario",
            "ganancia": v.get('ganancia', 0)
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
                "ID": t.get('id', ''),
                "Fecha": t.get('fecha', '')[:16],
                "Cliente": t.get('cliente', ''),
                "Material": t.get('material', ''),
                "Cantidad": t.get('cantidad', 0),
                "Precio": t.get('precio', 0),
                "Total": t.get('total', 0),
                "Ganancia": t.get('ganancia', 0),
                "Tipo": tipo_mostrar
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # Exportar
        if st.button("📄 Exportar a CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"historial_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.info("No hay transacciones registradas")

# ============================================================
# PÁGINA: GASTOS
# ============================================================

def pagina_gastos():
    st.title("💰 Gastos")
    st.caption("Registro de gastos")
    
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
                
                # Actualizar caja
                caja_actual = get_caja_general()
                st.session_state.data['caja_general'] = redondear(caja_actual - monto)
                st.session_state.data['gastos'] = gastos
                guardar_datos()
                
                st.success(f"✅ Gasto registrado: ${monto:.2f}")
                st.rerun()
            else:
                st.error("Complete todos los campos")
    
    st.divider()
    
    # Lista de gastos
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
                "Monto": g.get('monto', 0),
                "Categoría": g.get('categoria', ''),
                "Usuario": g.get('usuario', '')
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay gastos registrados")

# ============================================================
# PÁGINA: MÉTRICAS
# ============================================================

def pagina_metricas():
    st.title("📈 Métricas")
    st.caption("Resumen general del negocio")
    
    inventario = get_inventario()
    ventas = get_ventas()
    gastos = get_gastos()
    remisiones = get_remisiones()
    ventas_sim = get_ventas_simuladas()
    caja_general = get_caja_general()
    fondo_salarios = get_fondo_salarios()
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    total_stock = sum(d.get("stock", 0) for d in inventario.values())
    total_valor = sum(redondear(d.get("stock", 0) * d.get("precio_venta", 0)) for d in inventario.values())
    total_inversion = sum(d.get("inversion_total", 0) for d in inventario.values())
    total_ventas = sum(v.get("total", 0) for v in ventas)
    total_gastos = sum(g.get("monto", 0) for g in gastos)
    total_remisiones = len(remisiones)
    total_pos_venta = sum(v.get("total", 0) for v in ventas_sim)
    
    ganancia_potencial = 0
    for material, datos in inventario.items():
        stock = datos.get("stock", 0)
        precio_venta = datos.get("precio_venta", 0)
        if stock > 0:
            ganancia_potencial += redondear(stock * calcular_ganancia(material, precio_venta))
    
    with col1:
        st.metric("💰 Caja General", f"${caja_general:.2f}")
    with col2:
        st.metric("👥 Fondo Salarios", f"${fondo_salarios:.2f}")
    with col3:
        st.metric("📦 Total Stock", f"{total_stock:.2f} kg")
    with col4:
        st.metric("💎 Valor Inventario", f"${total_valor:.2f}")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Inversión Total", f"${total_inversion:.2f}")
    with col2:
        st.metric("💵 Total Ventas", f"${total_ventas:.2f}")
    with col3:
        st.metric("💰 Ganancia Potencial", f"${ganancia_potencial:.2f}")
    with col4:
        st.metric("📈 Total Gastos", f"${total_gastos:.2f}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 Total Remisiones", total_remisiones)
    with col2:
        st.metric("📊 Pos Venta Total", f"${total_pos_venta:.2f}")
    with col3:
        st.metric("📊 Total Materiales", len(inventario))
    
    st.divider()
    
    # Resumen por categoría
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
            "Stock (kg)": stock_cat,
            "Valor": valor_cat,
            "Inversión": inversion_cat,
            "Ganancia": ganancia_cat
        })
    
    if data_cat:
        df = pd.DataFrame(data_cat)
        st.dataframe(df, use_container_width=True)

# ============================================================
# PÁGINA: FRECUENCIA CLIENTES
# ============================================================

def pagina_frecuencia():
    st.title("📊 Frecuencia de Clientes")
    st.caption("Análisis de visitas de clientes")
    
    ventas = get_ventas()
    clientes = get_clientes()
    
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
                "Total kg": redondear(datos["total_kg"]),
                "Total Compras": datos["total_compras"]
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        
        # Cliente más frecuente
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
    
    # Inicializar session_state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.page = "inventario"
        st.session_state.data_loaded = False
    
    # Cargar datos
    if not st.session_state.data_loaded:
        cargar_datos()
    
    if not st.session_state.logged_in:
        mostrar_login()
        return
    
    # Mostrar sidebar y contenido
    mostrar_sidebar()
    
    # Navegación
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
    
    # Footer
    st.divider()
    st.caption(f"♻️ Reciclaje Industrial - Cloud v2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
