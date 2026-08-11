# reciclaje.py - Sistema de Control de Reciclaje Industrial
# Con sincronización Google Drive - TODAS las secciones originales intactas

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import shutil
from datetime import datetime
from collections import defaultdict
import qrcode
from PIL import Image, ImageTk
import webbrowser
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import http.server
import socketserver
import threading
import socket
import base64
from io import BytesIO

# ============================================================
# NUEVO: MÓDULO DE SINCRONIZACIÓN CON GOOGLE DRIVE
# ============================================================

try:
    from drive_sync import drive_sync
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False
    print("⚠️ Módulo drive_sync no encontrado. Sincronización con Drive deshabilitada.")

DATA_FILE = "reciclaje_data.json"
BACKUP_FOLDER = "backups"
MAX_BACKUPS = 5
CAJA_FILE = "caja_diaria.json"
PORT = 8080

# ============================================================
# PORCENTAJES DE GANANCIA (ORIGINAL)
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
# FUNCIONES DE UTILIDAD (ORIGINALES)
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
# GESTOR DE DATOS (MODIFICADO PARA SINCRONIZACIÓN)
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

# ============================================================
# CLASE PRINCIPAL DEL SISTEMA (MODIFICADA PARA SINCRONIZACIÓN)
# ============================================================

class SistemaReciclaje:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Control - Reciclaje Industrial")
        self.root.geometry("1400x800")
        self.usuario_actual = None
        
        # Crear carpetas necesarias
        if not os.path.exists(BACKUP_FOLDER):
            os.makedirs(BACKUP_FOLDER)
        
        self.clientes = []
        self.materiales = {}
        self.compras = []
        self.gastos = []
        self.compras_mayoreo = []
        self.ventas = []
        self.ventas_simuladas = []
        self.inversion_inicial = 10000
        self.fondo_salarios = 0
        self.caja_general = 10000
        self.carrito_compras = []
        self.temp_html_file = None
        self.inventario = {}
        self.caja_diaria = {}
        self.caja_abierta = False
        self.caja_fecha = None
        self.caja_apertura = 0
        self.caja_movimientos = []
        self.servidor_web = None
        
        self.correo_password = "cnqa hhwn bsmx dnjt"
        self.correo_remitente = "reciclamexico2026@gmail.com"
        self.correo_destinatario = "reciclamexico2026@gmail.com"
        
        self.trees_materiales = {}
        self.remisiones_generadas = []
        self.ventas_agrupadas = []
        
        self.visitas_clientes = {}
        self.frecuencia_clientes = {}
        
        # ============================================================
        # NUEVO: Estado de sincronización
        # ============================================================
        self.sync_enabled = False
        self.last_sync_time = None
        self.sync_status_label = None
        
        # Intentar conectar con Google Drive
        self.init_drive_sync()
        # ============================================================
        
        self.mostrar_login()
    
    # ============================================================
    # NUEVO: FUNCIONES DE SINCRONIZACIÓN CON GOOGLE DRIVE
    # ============================================================
    
    def init_drive_sync(self):
        """Inicializa la sincronización con Google Drive"""
        if not DRIVE_AVAILABLE:
            print("⚠️ Sincronización con Drive no disponible")
            self.sync_enabled = False
            return
            
        try:
            def connect_drive():
                if drive_sync.connect():
                    self.sync_enabled = True
                    print("✅ Sincronización con Google Drive habilitada")
                    self.root.after(100, self.cargar_desde_drive)
                else:
                    print("⚠️ Sincronización con Google Drive no disponible")
                    self.sync_enabled = False
            
            threading.Thread(target=connect_drive, daemon=True).start()
            
        except Exception as e:
            print(f"⚠️ Error al inicializar Drive: {e}")
            self.sync_enabled = False
    
    def cargar_desde_drive(self):
        """Carga los datos desde Google Drive"""
        try:
            data = drive_sync.sync_data()
            if data:
                print("✅ Datos cargados desde Google Drive")
                self.clientes = data.get('clientes', [])
                self.materiales = data.get('materiales', {})
                self.compras = data.get('compras', [])
                self.gastos = data.get('gastos', [])
                self.compras_mayoreo = data.get('compras_mayoreo', [])
                self.ventas = data.get('ventas', [])
                self.ventas_simuladas = data.get('ventas_simuladas', [])
                self.inversion_inicial = data.get('inversion_inicial', 10000)
                self.fondo_salarios = data.get('fondo_salarios', 0)
                self.caja_general = data.get('caja_general', 10000)
                self.inventario = data.get('inventario', {})
                self.remisiones_generadas = data.get('remisiones_generadas', [])
                self.ventas_agrupadas = data.get('ventas_agrupadas', [])
                self.visitas_clientes = data.get('visitas_clientes', {})
                self.frecuencia_clientes = data.get('frecuencia_clientes', {})
                self.last_sync_time = datetime.now()
                self.actualizar_estado_sync()
                return True
            
            return self.cargar_datos()
            
        except Exception as e:
            print(f"⚠️ Error al cargar desde Drive: {e}")
            return self.cargar_datos()
    
    def sincronizar_con_drive(self):
        """Sincroniza los datos con Google Drive"""
        if not self.sync_enabled:
            messagebox.showwarning("Sincronización", 
                "⚠️ No hay conexión con Google Drive.\n\n"
                "Pasos para configurar:\n"
                "1. Ve a https://console.cloud.google.com/\n"
                "2. Crea un proyecto y habilita Google Drive API\n"
                "3. Crea una cuenta de servicio y descarga credentials.json\n"
                "4. Coloca el archivo en la misma carpeta del programa")
            return False
        
        try:
            data = self.obtener_datos_completos()
            
            if drive_sync.sync_data(data):
                drive_sync.upload_backup(data)
                self.last_sync_time = datetime.now()
                self.actualizar_estado_sync()
                print(f"✅ Datos sincronizados con Drive a las {self.last_sync_time}")
                return True
            else:
                print("❌ Error al sincronizar con Drive")
                return False
        except Exception as e:
            print(f"❌ Error en sincronización: {e}")
            messagebox.showerror("Error de Sincronización", 
                f"Error al sincronizar con Google Drive:\n{str(e)}")
            return False
    
    def obtener_datos_completos(self):
        """Obtiene todos los datos en un diccionario"""
        return {
            'clientes': self.clientes,
            'materiales': self.materiales,
            'compras': self.compras,
            'gastos': self.gastos,
            'compras_mayoreo': self.compras_mayoreo,
            'ventas': self.ventas,
            'ventas_simuladas': self.ventas_simuladas,
            'inversion_inicial': self.inversion_inicial,
            'fondo_salarios': self.fondo_salarios,
            'caja_general': self.caja_general,
            'inventario': self.inventario,
            'remisiones_generadas': self.remisiones_generadas,
            'ventas_agrupadas': self.ventas_agrupadas,
            'visitas_clientes': self.visitas_clientes,
            'frecuencia_clientes': self.frecuencia_clientes,
            'ultima_actualizacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def actualizar_estado_sync(self):
        """Actualiza el label de estado de sincronización"""
        if self.sync_status_label:
            if self.sync_enabled and self.last_sync_time:
                self.sync_status_label.config(
                    text=f"✅ Sincronizado: {self.last_sync_time.strftime('%H:%M:%S')}",
                    foreground="green"
                )
            elif self.sync_enabled:
                self.sync_status_label.config(
                    text="✅ Conectado a Google Drive",
                    foreground="green"
                )
            else:
                self.sync_status_label.config(
                    text="⚠️ Sin conexión a Google Drive",
                    foreground="red"
                )
    
    def sincronizar_manual(self):
        """Sincroniza manualmente con Google Drive"""
        if not self.sync_enabled:
            messagebox.showwarning("Sincronización", 
                "⚠️ No hay conexión con Google Drive.\n\n"
                "Pasos para configurar:\n"
                "1. Ve a https://console.cloud.google.com/\n"
                "2. Crea un proyecto y habilita Google Drive API\n"
                "3. Crea una cuenta de servicio y descarga credentials.json\n"
                "4. Coloca el archivo en la misma carpeta del programa")
            return
        
        try:
            messagebox.showinfo("Sincronización", "🔄 Sincronizando con Google Drive...\n\nPor favor espera...")
            
            if self.sincronizar_con_drive():
                messagebox.showinfo("Éxito", 
                    "✅ Datos sincronizados correctamente con Google Drive\n\n"
                    f"📅 Última sincronización: {datetime.now().strftime('%H:%M:%S')}")
                
                self.actualizar_estado_sync()
                self.actualizar_todas_las_tablas()
            else:
                messagebox.showerror("Error", "❌ Error al sincronizar con Google Drive\n\nVerifica tu conexión a internet.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al sincronizar:\n{str(e)}")
    
    def restaurar_desde_drive(self):
        """Restaura datos desde un backup en Google Drive"""
        if not self.sync_enabled:
            messagebox.showwarning("Sincronización", "No hay conexión con Google Drive")
            return
        
        try:
            backups = drive_sync.list_backups()
            
            if not backups:
                messagebox.showinfo("Backups", "No hay backups disponibles en Google Drive")
                return
            
            ventana = tk.Toplevel(self.root)
            ventana.title("Restaurar desde Google Drive")
            ventana.geometry("550x350")
            ventana.transient(self.root)
            ventana.grab_set()
            
            tk.Label(ventana, text="📥 Selecciona un backup para restaurar:", 
                    font=("Arial", 11)).pack(pady=10)
            
            frame = ttk.Frame(ventana)
            frame.pack(fill='both', expand=True, padx=10, pady=5)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side='right', fill='y')
            
            tree = ttk.Treeview(frame, columns=("Archivo", "Fecha"), 
                               show='headings', yscrollcommand=scrollbar.set)
            tree.heading("Archivo", text="Archivo")
            tree.heading("Fecha", text="Fecha")
            tree.pack(fill='both', expand=True)
            scrollbar.config(command=tree.yview)
            
            for backup in backups:
                tree.insert("", "end", values=(
                    backup['name'],
                    backup.get('createdTime', 'N/A')
                ))
            
            def restaurar():
                seleccion = tree.selection()
                if not seleccion:
                    messagebox.showwarning("Error", "Selecciona un backup")
                    return
                
                item = tree.item(seleccion)
                nombre = item['values'][0]
                
                if not messagebox.askyesno("Confirmar", 
                    f"⚠️ ¿Restaurar desde '{nombre}'?\n\n"
                    "Esto reemplazará TODOS los datos actuales.\n"
                    "Los datos actuales se perderán.\n\n"
                    "¿Estás seguro?"):
                    return
                
                try:
                    results = drive_sync.service.files().list(
                        q=f"name='{nombre}' and '{drive_sync.folder_id}' in parents and trashed=false",
                        spaces='drive',
                        fields='files(id, name)'
                    ).execute()
                    
                    files = results.get('files', [])
                    if not files:
                        messagebox.showerror("Error", "Backup no encontrado")
                        return
                    
                    file_id = files[0]['id']
                    
                    request = drive_sync.service.files().get_media(fileId=file_id)
                    file_data = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_data, request)
                    
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    file_data.seek(0)
                    data = json.loads(file_data.read().decode('utf-8'))
                    
                    self.clientes = data.get('clientes', [])
                    self.materiales = data.get('materiales', {})
                    self.compras = data.get('compras', [])
                    self.gastos = data.get('gastos', [])
                    self.compras_mayoreo = data.get('compras_mayoreo', [])
                    self.ventas = data.get('ventas', [])
                    self.ventas_simuladas = data.get('ventas_simuladas', [])
                    self.inversion_inicial = data.get('inversion_inicial', 10000)
                    self.fondo_salarios = data.get('fondo_salarios', 0)
                    self.caja_general = data.get('caja_general', 10000)
                    self.inventario = data.get('inventario', {})
                    self.remisiones_generadas = data.get('remisiones_generadas', [])
                    self.ventas_agrupadas = data.get('ventas_agrupadas', [])
                    self.visitas_clientes = data.get('visitas_clientes', {})
                    self.frecuencia_clientes = data.get('frecuencia_clientes', {})
                    
                    self.guardar_datos()
                    ventana.destroy()
                    
                    messagebox.showinfo("Éxito", "✅ Datos restaurados correctamente desde Google Drive")
                    self.actualizar_todas_las_tablas()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Error al restaurar:\n{str(e)}")
            
            frame_botones = ttk.Frame(ventana)
            frame_botones.pack(pady=10)
            
            ttk.Button(frame_botones, text="✅ Restaurar Seleccionado", 
                      command=restaurar).pack(side='left', padx=5)
            ttk.Button(frame_botones, text="❌ Cancelar", 
                      command=ventana.destroy).pack(side='left', padx=5)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al listar backups:\n{str(e)}")
    
    def _sync_in_background(self):
        """Sincroniza en segundo plano con Drive"""
        try:
            data = self.obtener_datos_completos()
            drive_sync.sync_data(data)
            self.root.after(0, self.actualizar_estado_sync)
        except Exception as e:
            print(f"⚠️ Error en sincronización en segundo plano: {e}")
    
    def actualizar_todas_las_tablas(self):
        """Actualiza todas las tablas de la interfaz"""
        if hasattr(self, 'tree_inventario'):
            self.actualizar_tabla_inventario()
        if hasattr(self, 'tree_clientes'):
            self.actualizar_lista_clientes()
        if hasattr(self, 'tree_ventas'):
            self.actualizar_lista_ventas()
        if hasattr(self, 'tree_carrito'):
            self.actualizar_carrito()
        if hasattr(self, 'tree_remisiones'):
            self.actualizar_lista_remisiones()
        if hasattr(self, 'tree_historial'):
            self.actualizar_historial()
        if hasattr(self, 'tree_gastos'):
            self.actualizar_lista_gastos()
        if hasattr(self, 'tree_movimientos'):
            self.actualizar_movimientos_caja()
        if hasattr(self, 'tree_historial_caja'):
            self.actualizar_historial_caja()
        if hasattr(self, 'tree_frecuencia'):
            self.actualizar_frecuencia_clientes()
        self.actualizar_metricas()
        self.actualizar_info_caja()
        self.actualizar_estado_sync()
    
    # ============================================================
    # FIN DE LAS FUNCIONES DE SINCRONIZACIÓN
    # ============================================================
    
    # ============================================================
    # FUNCIONES ORIGINALES (COMPLETAMENTE SIN MODIFICAR)
    # ============================================================
    
    def redondear(self, valor, decimales=2):
        return round(valor, decimales)
    
    def calcular_precio_cliente(self, material, precio_venta):
        return calcular_precio_cliente(material, precio_venta)
    
    def calcular_ganancia(self, material, precio_venta):
        return calcular_ganancia(material, precio_venta)
    
    def obtener_porcentaje_ganancia(self, material):
        return obtener_porcentaje_ganancia(material)
    
    def ordenar_materiales_alfabeticamente(self):
        secciones_a_ordenar = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza"]
        
        for seccion in secciones_a_ordenar:
            if seccion in self.materiales:
                self.materiales[seccion] = sorted(
                    self.materiales[seccion], 
                    key=lambda x: x.get('nombre', '').lower()
                )
        
        if "pos_venta" in self.materiales:
            self.materiales["pos_venta"] = sorted(
                self.materiales["pos_venta"], 
                key=lambda x: x.get('nombre', '').lower()
            )
    
    # ==================== INICIO DE SESIÓN ====================
    
    def mostrar_login(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        frame_login = tk.Frame(self.root, bg="#2c3e50")
        frame_login.pack(fill='both', expand=True)
        
        frame_form = tk.Frame(frame_login, bg="white", bd=5, relief='ridge')
        frame_form.place(relx=0.5, rely=0.5, anchor='center', width=450, height=420)
        
        tk.Label(frame_form, text="♻️ RECICLAJE INDUSTRIAL", 
                 font=("Arial", 16, "bold"), bg="white", fg="#2c3e50").pack(pady=20)
        
        tk.Label(frame_form, text="Sistemas Computerionales de México", 
                 font=("Arial", 10), bg="white", fg="#7f8c8d").pack(pady=(0, 5))
        
        # Estado de sincronización
        if DRIVE_AVAILABLE and drive_sync.connected:
            sync_text = "✅ Google Drive conectado"
            sync_color = "green"
        else:
            sync_text = "⚠️ Sin conexión a Google Drive"
            sync_color = "red"
        
        tk.Label(frame_form, text=sync_text, 
                 font=("Arial", 9), bg="white", fg=sync_color).pack(pady=(0, 15))
        
        tk.Label(frame_form, text="Usuario:", font=("Arial", 11), bg="white").pack(pady=(10, 2))
        self.entry_usuario = tk.Entry(frame_form, font=("Arial", 12), width=25, bd=2, relief='solid')
        self.entry_usuario.pack(pady=(0, 5))
        self.entry_usuario.focus()
        
        tk.Label(frame_form, text="Contraseña:", font=("Arial", 11), bg="white").pack(pady=(10, 2))
        self.entry_password = tk.Entry(frame_form, font=("Arial", 12), width=25, bd=2, relief='solid', show="•")
        self.entry_password.pack(pady=(0, 5))
        self.entry_password.bind('<Return>', lambda e: self.iniciar_sesion())
        
        btn_login = tk.Button(frame_form, text="INICIAR SESIÓN", font=("Arial", 12, "bold"),
                              bg="#2c3e50", fg="white", padx=20, pady=8, 
                              command=self.iniciar_sesion, relief='flat')
        btn_login.pack(pady=20)
        
        self.label_error = tk.Label(frame_form, text="", font=("Arial", 10), bg="white", fg="red")
        self.label_error.pack()
        
        tk.Label(frame_login, text="Versión 5.0 - Sincronización Google Drive", 
                 font=("Arial", 9), bg="#2c3e50", fg="#7f8c8d").pack(side='bottom', pady=10)
    
    def iniciar_sesion(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get().strip()
        
        if usuario == "admin" and password == "admin123":
            self.usuario_actual = usuario
            self.rol_actual = "administrador"
            self.label_error.config(text="")
            self.iniciar_sistema()
        elif usuario == "usuario" and password == "usuario123":
            self.usuario_actual = usuario
            self.rol_actual = "usuario"
            self.label_error.config(text="")
            self.iniciar_sistema()
        else:
            self.label_error.config(text="❌ Usuario o contraseña incorrectos")
            self.entry_password.delete(0, tk.END)
            self.entry_password.focus()
    
    def iniciar_sistema(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # ============================================================
        # BARRA SUPERIOR CON BOTONES DE SINCRONIZACIÓN (NUEVO)
        # ============================================================
        frame_usuario = tk.Frame(self.root, bg="#34495e", height=45)
        frame_usuario.pack(fill='x', side='top')
        frame_usuario.pack_propagate(False)
        
        tk.Label(frame_usuario, text=f"👤 Usuario: {self.usuario_actual} ({self.rol_actual})", 
                 font=("Arial", 10), bg="#34495e", fg="white").pack(side='left', padx=15, pady=10)
        
        # Label de estado de sincronización
        self.sync_status_label = tk.Label(frame_usuario, text="🔄 Conectando...", 
                                          font=("Arial", 9), bg="#34495e", fg="#f1c40f")
        self.sync_status_label.pack(side='left', padx=15, pady=10)
        
        # Botón de sincronización manual
        btn_sync = tk.Button(frame_usuario, text="☁️ Sincronizar Drive", 
                             font=("Arial", 10, "bold"), bg="#27ae60", fg="white", 
                             padx=15, pady=5, relief='raised', bd=2, cursor="hand2",
                             command=self.sincronizar_manual)
        btn_sync.pack(side='right', padx=5, pady=5)
        
        # Botón de restaurar desde backup
        btn_restore = tk.Button(frame_usuario, text="📥 Restaurar Backup", 
                               font=("Arial", 10), bg="#f39c12", fg="white", 
                               padx=12, pady=5, relief='raised', bd=2, cursor="hand2",
                               command=self.restaurar_desde_drive)
        btn_restore.pack(side='right', padx=5, pady=5)
        
        tk.Button(frame_usuario, text="🔒 Cerrar Sesión", font=("Arial", 10), 
                  bg="#e74c3c", fg="white", padx=12, pady=5, 
                  relief='raised', bd=2, cursor="hand2",
                  command=self.cerrar_sesion).pack(side='right', padx=15, pady=5)
        # ============================================================
        
        # Actualizar estado de sincronización
        self.actualizar_estado_sync()
        
        # Cargar datos y crear interfaz
        self.cargar_datos()
        self.cargar_caja_diaria()
        self.crear_interfaz()
        self.iniciar_servidor_web()
    
    def cerrar_sesion(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea cerrar sesión?"):
            if self.servidor_web:
                try:
                    self.servidor_web.shutdown()
                except:
                    pass
            self.mostrar_login()
    
    # ==================== CARGA Y GUARDADO DE DATOS ====================
    
    def crear_backup(self):
        if os.path.exists(DATA_FILE):
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(BACKUP_FOLDER, f"reciclaje_data_backup_{timestamp}.json")
                shutil.copy2(DATA_FILE, backup_file)
                
                backups = sorted([f for f in os.listdir(BACKUP_FOLDER) if f.startswith("reciclaje_data_backup_")])
                while len(backups) > MAX_BACKUPS:
                    os.remove(os.path.join(BACKUP_FOLDER, backups.pop(0)))
                return True
            except Exception as e:
                print(f"Error al crear backup: {e}")
                return False
        return False
    
    def restaurar_desde_backup(self):
        try:
            backups = sorted([f for f in os.listdir(BACKUP_FOLDER) if f.startswith("reciclaje_data_backup_")], reverse=True)
            
            if not backups:
                return None
            
            for backup in backups:
                try:
                    backup_path = os.path.join(BACKUP_FOLDER, backup)
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    print(f"✅ Respaldo recuperado exitosamente: {backup}")
                    messagebox.showwarning(
                        "Recuperación de Datos", 
                        f"El archivo principal de datos estaba corrupto.\n\n"
                        f"Se ha recuperado exitosamente el respaldo del archivo:\n"
                        f"{backup}\n\n"
                        f"✅ Los datos han sido restaurados correctamente."
                    )
                    return data
                    
                except Exception as e:
                    print(f"Error al leer respaldo {backup}: {e}")
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error en restauración: {e}")
            return None
    
    def cargar_datos(self):
        # Intentar cargar desde Drive primero (si está disponible)
        if DRIVE_AVAILABLE and drive_sync.connected:
            data = drive_sync.sync_data()
            if data:
                self.clientes = data.get('clientes', [])
                self.materiales = data.get('materiales', {})
                self.compras = data.get('compras', [])
                self.gastos = data.get('gastos', [])
                self.compras_mayoreo = data.get('compras_mayoreo', [])
                self.ventas = data.get('ventas', [])
                self.ventas_simuladas = data.get('ventas_simuladas', [])
                self.inversion_inicial = data.get('inversion_inicial', 10000)
                self.fondo_salarios = data.get('fondo_salarios', 0)
                self.caja_general = data.get('caja_general', 10000)
                self.inventario = data.get('inventario', {})
                self.remisiones_generadas = data.get('remisiones_generadas', [])
                self.ventas_agrupadas = data.get('ventas_agrupadas', [])
                self.visitas_clientes = data.get('visitas_clientes', {})
                self.frecuencia_clientes = data.get('frecuencia_clientes', {})
                self.last_sync_time = datetime.now()
                self.actualizar_estado_sync()
                print("✅ Datos cargados desde Google Drive")
                return
        
        # Fallback: cargar desde archivo local
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if not isinstance(data, dict) or 'clientes' not in data:
                    raise ValueError("Archivo de datos corrupto o estructura inválida")
                
                self.clientes = data.get('clientes', [])
                self.materiales = data.get('materiales', {})
                self.compras = data.get('compras', [])
                self.gastos = data.get('gastos', [])
                self.compras_mayoreo = data.get('compras_mayoreo', [])
                self.ventas = data.get('ventas', [])
                self.ventas_simuladas = data.get('ventas_simuladas', [])
                self.inversion_inicial = data.get('inversion_inicial', 10000)
                self.fondo_salarios = data.get('fondo_salarios', 0)
                self.caja_general = data.get('caja_general', 10000)
                self.inventario = data.get('inventario', {})
                self.remisiones_generadas = data.get('remisiones_generadas', [])
                self.ventas_agrupadas = data.get('ventas_agrupadas', [])
                self.visitas_clientes = data.get('visitas_clientes', {})
                self.frecuencia_clientes = data.get('frecuencia_clientes', {})
                
                for material, datos in self.inventario.items():
                    if 'stock' not in datos:
                        datos['stock'] = 0
                    if 'precio_venta' not in datos:
                        datos['precio_venta'] = 0
                    if 'precio_compra_cliente' not in datos:
                        datos['precio_compra_cliente'] = 0
                    if 'seccion' not in datos:
                        datos['seccion'] = 'inventario'
                    if 'inversion_total' not in datos:
                        datos['inversion_total'] = 0
                    if 'inversion_promedio' not in datos:
                        datos['inversion_promedio'] = 0
                    if 'total_comprado' not in datos:
                        datos['total_comprado'] = 0
                
                for i, compra in enumerate(self.compras):
                    if 'id' not in compra:
                        compra['id'] = i + 1
                
                for i, compra in enumerate(self.compras_mayoreo):
                    if 'id' not in compra:
                        compra['id'] = i + 1
                
                for i, venta in enumerate(self.ventas):
                    if 'id' not in venta:
                        venta['id'] = i + 1
                
                for i, venta_sim in enumerate(self.ventas_simuladas):
                    if 'id' not in venta_sim:
                        venta_sim['id'] = i + 1
                
                for i, gasto in enumerate(self.gastos):
                    if 'id' not in gasto:
                        gasto['id'] = i + 1
                
                if 'por_pieza' not in self.materiales:
                    self.materiales['por_pieza'] = self.inicializar_materiales_por_pieza()
                
                if 'pos_venta' not in self.materiales:
                    self.materiales['pos_venta'] = self.inicializar_materiales_pos_venta()
                
                self.ordenar_materiales_alfabeticamente()
                
                if not self.materiales:
                    self.inicializar_datos()
                else:
                    print(f"✅ Datos cargados exitosamente. {len(self.inventario)} materiales en inventario.")
                    self.guardar_datos()
                    
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                print(f"❌ Error al cargar datos: {e}")
                print("Intentando restaurar desde respaldo...")
                
                data_recuperada = self.restaurar_desde_backup()
                
                if data_recuperada:
                    self.clientes = data_recuperada.get('clientes', [])
                    self.materiales = data_recuperada.get('materiales', {})
                    self.compras = data_recuperada.get('compras', [])
                    self.gastos = data_recuperada.get('gastos', [])
                    self.compras_mayoreo = data_recuperada.get('compras_mayoreo', [])
                    self.ventas = data_recuperada.get('ventas', [])
                    self.ventas_simuladas = data_recuperada.get('ventas_simuladas', [])
                    self.inversion_inicial = data_recuperada.get('inversion_inicial', 10000)
                    self.fondo_salarios = data_recuperada.get('fondo_salarios', 0)
                    self.caja_general = data_recuperada.get('caja_general', 10000)
                    self.inventario = data_recuperada.get('inventario', {})
                    self.remisiones_generadas = data_recuperada.get('remisiones_generadas', [])
                    self.ventas_agrupadas = data_recuperada.get('ventas_agrupadas', [])
                    self.visitas_clientes = data_recuperada.get('visitas_clientes', {})
                    self.frecuencia_clientes = data_recuperada.get('frecuencia_clientes', {})
                    if 'por_pieza' not in self.materiales:
                        self.materiales['por_pieza'] = self.inicializar_materiales_por_pieza()
                    if 'pos_venta' not in self.materiales:
                        self.materiales['pos_venta'] = self.inicializar_materiales_pos_venta()
                    self.ordenar_materiales_alfabeticamente()
                    self.guardar_datos()
                    print("✅ Datos recuperados y guardados exitosamente")
                else:
                    print("⚠️ No se encontraron respaldos válidos. Inicializando datos por defecto...")
                    self.inicializar_datos()
                    
            except Exception as e:
                print(f"❌ Error inesperado al cargar datos: {e}")
                self.inicializar_datos()
        else:
            print("Archivo de datos no encontrado. Inicializando nuevo sistema...")
            self.inicializar_datos()
    
    def inicializar_materiales_por_pieza(self):
        return [
            {"nombre": "motor", "precio_venta": 15.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "bomba", "precio_venta": 12.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "compresor", "precio_venta": 18.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "transformador", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "alternador", "precio_venta": 14.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "generador", "precio_venta": 20.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "caja de velocidades", "precio_venta": 8.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "diferencial", "precio_venta": 9.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "eje", "precio_venta": 6.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "polea", "precio_venta": 5.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "engrane", "precio_venta": 7.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "cigueñal", "precio_venta": 11.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "biela", "precio_venta": 6.50, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "piston", "precio_venta": 4.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "cabeza de motor", "precio_venta": 13.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "bloque de motor", "precio_venta": 16.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "radiador", "precio_venta": 22.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "intercooler", "precio_venta": 25.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "turbo", "precio_venta": 30.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "freno", "precio_venta": 3.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "disco de freno", "precio_venta": 4.50, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "cilindro hidráulico", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "bomba hidráulica", "precio_venta": 12.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "motor eléctrico", "precio_venta": 8.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "cable industrial", "precio_venta": 2.50, "empresa": "Centro de Acopio Tláhuac"},
        ]
    
    def inicializar_materiales_pos_venta(self):
        return [
            {"nombre": "cobre 1a", "precio_venta": 225.00, "empresa": "Grupo Imperio Steel"},
            {"nombre": "cobre 2a", "precio_venta": 202.00, "empresa": "Grupo Imperio Steel"},
            {"nombre": "aluminio macizo", "precio_venta": 48.00, "empresa": "Green Power Tezoyuca"},
            {"nombre": "bronce amarillo", "precio_venta": 150.50, "empresa": "La Batería Verde"},
            {"nombre": "chatarra", "precio_venta": 4.60, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "pet cristal", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "carton", "precio_venta": 0.80, "empresa": "Centro de Acopio Tláhuac"},
            {"nombre": "bateria automotriz", "precio_venta": 14.00, "empresa": "Grupo Imperio Steel"},
            {"nombre": "acero 304", "precio_venta": 19.50, "empresa": "Green Power Tezoyuca"},
            {"nombre": "plomo blando", "precio_venta": 42.00, "empresa": "Grupo Imperio Steel"},
        ]
    
    def guardar_datos(self):
        try:
            if os.path.exists(DATA_FILE):
                try:
                    with open(DATA_FILE, 'r', encoding='utf-8') as f:
                        json.load(f)
                    self.crear_backup()
                except:
                    print("Archivo principal corrupto, no se creará backup del mismo")
            
            self.ordenar_materiales_alfabeticamente()
            
            data = {
                'clientes': self.clientes,
                'materiales': self.materiales,
                'compras': self.compras,
                'gastos': self.gastos,
                'compras_mayoreo': self.compras_mayoreo,
                'ventas': self.ventas,
                'ventas_simuladas': self.ventas_simuladas,
                'inversion_inicial': self.inversion_inicial,
                'fondo_salarios': self.fondo_salarios,
                'caja_general': self.caja_general,
                'inventario': self.inventario,
                'remisiones_generadas': self.remisiones_generadas,
                'ventas_agrupadas': self.ventas_agrupadas,
                'visitas_clientes': self.visitas_clientes,
                'frecuencia_clientes': self.frecuencia_clientes,
                'ultima_actualizacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            temp_file = DATA_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            shutil.move(temp_file, DATA_FILE)
            print(f"✅ Datos guardados exitosamente a las {datetime.now().strftime('%H:%M:%S')}")
            
            # ============================================================
            # NUEVO: Sincronizar con Drive en segundo plano
            # ============================================================
            if self.sync_enabled:
                threading.Thread(target=self._sync_in_background, daemon=True).start()
            # ============================================================
            
        except Exception as e:
            print(f"❌ Error al guardar datos: {e}")
            messagebox.showerror(
                "Error al Guardar", 
                f"No se pudieron guardar los datos.\nError: {str(e)}\n\n"
                f"Por favor, verifique que tenga permisos de escritura en la carpeta."
            )
    
    def inicializar_datos(self):
        self.materiales = {
            "ferrosos": [
                {"nombre": "cobre 1a", "precio_venta": 225.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "cobre 2a", "precio_venta": 202.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "tubo candy", "precio_venta": 212.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "radiador de cobre", "precio_venta": 180.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "cable forrado de cobre", "precio_venta": 120.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "bronce amarillo", "precio_venta": 150.50, "empresa": "La Batería Verde"},
                {"nombre": "bronce rojo", "precio_venta": 204.00, "empresa": "La Batería Verde"},
                {"nombre": "rebaba de bronce", "precio_venta": 140.00, "empresa": "La Batería Verde"},
                {"nombre": "radiador de bronce", "precio_venta": 142.00, "empresa": "La Batería Verde"},
                {"nombre": "cable de aluminio", "precio_venta": 70.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "aluminio blando", "precio_venta": 38.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "aluminio macizo", "precio_venta": 48.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "aluminio perfil sin pintura", "precio_venta": 64.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "aluminio perfil con pintura", "precio_venta": 51.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "aluminio bote", "precio_venta": 42.00, "empresa": "La Batería Verde"},
                {"nombre": "aluminio tubo", "precio_venta": 36.50, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "rin de aluminio", "precio_venta": 67.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "piston de aluminio", "precio_venta": 39.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "radiador aluminio/cobre", "precio_venta": 115.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "litografia", "precio_venta": 57.00, "empresa": "Green Power Tezoyuca"},
                {"nombre": "spray", "precio_venta": 51.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "chatarra", "precio_venta": 4.60, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "lata de fierro", "precio_venta": 4.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "fierro colado", "precio_venta": 7.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "plomo blando", "precio_venta": 42.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "plomo duro", "precio_venta": 25.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "plomo balancin", "precio_venta": 20.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "antimonio", "precio_venta": 42.50, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "acero 304", "precio_venta": 19.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "rebaba acero 304", "precio_venta": 15.50, "empresa": "Green Power Tezoyuca"},
                {"nombre": "bateria automotriz", "precio_venta": 14.00, "empresa": "Grupo Imperio Steel"},
                {"nombre": "bateria industrial", "precio_venta": 16.00, "empresa": "Grupo Imperio Steel"},
            ],
            "plasticos": [
                {"nombre": "pet cristal", "precio_venta": 10.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "pet verde", "precio_venta": 8.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "electrolit", "precio_venta": 6.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "plastico duro", "precio_venta": 5.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cd", "precio_venta": 5.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "radiografia", "precio_venta": 92.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "membrana", "precio_venta": 200.00, "empresa": "Centro de Acopio Tláhuac"},
            ],
            "electronicos": [
                {"nombre": "primera", "precio_venta": 200, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "segunda", "precio_venta": 180, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "tercera", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "dorada", "precio_venta": 300, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "semi dorada", "precio_venta": 250, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "peine limpio", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "peine sucio", "precio_venta": 120, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cuadro grande", "precio_venta": 100, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cuadro chico", "precio_venta": 80, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "servidor", "precio_venta": 500, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "laptop", "precio_venta": 400, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "tableta", "precio_venta": 300, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "black panel", "precio_venta": 200, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "celular tecla limpio", "precio_venta": 250, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "celular touch limpio", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "celular sucio", "precio_venta": 55, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "logica de celular", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "pila de celular y tablet", "precio_venta": 50, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "pila de laptop", "precio_venta": 80, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "Fuente", "precio_venta": 120, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "cpu", "precio_venta": 180, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "electronico", "precio_venta": 100, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador dorado", "precio_venta": 500, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador ceramico", "precio_venta": 400, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador negro", "precio_venta": 350, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador con pines", "precio_venta": 300, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador con pines sucio", "precio_venta": 250, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador liso", "precio_venta": 280, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "procesador liso sucio", "precio_venta": 230, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "audio limpio", "precio_venta": 60, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "audio sucio", "precio_venta": 40, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "tv", "precio_venta": 200, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "automotriz", "precio_venta": 150, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "intermedia", "precio_venta": 130, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "medidor", "precio_venta": 90, "empresa": "Centro de Acopio Tláhuac"}
            ],
            "papel": [
                {"nombre": "carton", "precio_venta": 0.80, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "archivo blanco", "precio_venta": 2.40, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "hoja de color", "precio_venta": 1.00, "empresa": "Centro de Acopio Tláhuac"},
                {"nombre": "periodico", "precio_venta": 2.00, "empresa": "Centro de Acopio Tláhuac"}
            ],
            "por_pieza": self.inicializar_materiales_por_pieza(),
            "pos_venta": self.inicializar_materiales_pos_venta()
        }
        
        self.ordenar_materiales_alfabeticamente()
        
        self.compras = []
        self.compras_mayoreo = []
        self.ventas = []
        self.ventas_simuladas = []
        self.gastos = []
        self.clientes = []
        self.fondo_salarios = 0
        self.caja_general = 10000
        self.inventario = {}
        self.remisiones_generadas = []
        self.ventas_agrupadas = []
        self.visitas_clientes = {}
        self.frecuencia_clientes = {}
        self.guardar_datos()
        print("✅ Datos inicializados por defecto")
    
    # ==================== CAJA DIARIA ====================
    
    def cargar_caja_diaria(self):
        if os.path.exists(CAJA_FILE):
            try:
                with open(CAJA_FILE, 'r', encoding='utf-8') as f:
                    self.caja_diaria = json.load(f)
                print(f"✅ Caja diaria cargada: {len(self.caja_diaria)} días")
            except:
                self.caja_diaria = {}
        else:
            self.caja_diaria = {}
    
    def guardar_caja_diaria(self):
        try:
            with open(CAJA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.caja_diaria, f, indent=2, ensure_ascii=False)
            print("✅ Caja diaria guardada")
        except Exception as e:
            print(f"❌ Error al guardar caja diaria: {e}")
    
    def abrir_caja(self):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        if fecha_actual in self.caja_diaria and self.caja_diaria[fecha_actual].get("abierta", False):
            messagebox.showwarning("Caja", f"Ya hay una caja abierta para hoy {fecha_actual}")
            return
        
        monto = simpledialog.askfloat("Apertura de Caja", 
            f"📅 Fecha: {fecha_actual}\n\n"
            f"Ingrese el monto inicial en caja:",
            initialvalue=self.caja_general)
        
        if monto is None:
            return
        
        if monto < 0:
            messagebox.showwarning("Error", "El monto no puede ser negativo")
            return
        
        self.caja_diaria[fecha_actual] = {
            "fecha": fecha_actual,
            "apertura": monto,
            "cierre": 0,
            "abierta": True,
            "movimientos": [],
            "total_ingresos": 0,
            "total_egresos": 0,
            "hora_apertura": datetime.now().strftime("%H:%M:%S"),
            "hora_cierre": "",
            "usuario": self.usuario_actual
        }
        
        self.caja_abierta = True
        self.caja_fecha = fecha_actual
        self.caja_apertura = monto
        self.caja_movimientos = []
        self.caja_general = monto
        
        self.guardar_caja_diaria()
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        self.actualizar_info_caja()
        
        messagebox.showinfo("Éxito", f"✅ Caja abierta correctamente\n\n"
            f"📅 Fecha: {fecha_actual}\n"
            f"👤 Usuario: {self.usuario_actual}\n"
            f"💰 Monto inicial: ${monto:.2f}")
    
    def cerrar_caja(self):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        if fecha_actual not in self.caja_diaria:
            messagebox.showwarning("Caja", "No hay una caja abierta para hoy")
            return
        
        if not self.caja_diaria[fecha_actual].get("abierta", False):
            messagebox.showwarning("Caja", "La caja ya está cerrada")
            return
        
        registro = self.caja_diaria[fecha_actual]
        total_ingresos = registro.get("total_ingresos", 0)
        total_egresos = registro.get("total_egresos", 0)
        saldo_actual = registro["apertura"] + total_ingresos - total_egresos
        
        if not messagebox.askyesno("Cerrar Caja", 
            f"📅 Fecha: {fecha_actual}\n"
            f"👤 Usuario: {self.usuario_actual}\n"
            f"💰 Apertura: ${registro['apertura']:.2f}\n"
            f"📈 Ingresos: ${total_ingresos:.2f}\n"
            f"📉 Egresos: ${total_egresos:.2f}\n"
            f"💰 Saldo actual: ${saldo_actual:.2f}\n"
            f"💰 Saldo en caja general: ${self.caja_general:.2f}\n\n"
            f"¿Confirmar cierre de caja?"):
            return
        
        registro["cierre"] = saldo_actual
        registro["abierta"] = False
        registro["hora_cierre"] = datetime.now().strftime("%H:%M:%S")
        registro["caja_general_final"] = self.caja_general
        
        self.caja_abierta = False
        self.caja_fecha = None
        self.caja_movimientos = []
        
        self.guardar_caja_diaria()
        self.actualizar_info_caja()
        self.actualizar_historial_caja()
        
        messagebox.showinfo("Éxito", f"✅ Caja cerrada correctamente\n\n"
            f"📅 Fecha: {fecha_actual}\n"
            f"👤 Usuario: {self.usuario_actual}\n"
            f"💰 Apertura: ${registro['apertura']:.2f}\n"
            f"💰 Cierre: ${registro['cierre']:.2f}\n"
            f"📈 Total Ingresos: ${total_ingresos:.2f}\n"
            f"📉 Total Egresos: ${total_egresos:.2f}")
    
    def registrar_movimiento_caja(self, tipo, concepto, monto):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        if fecha_actual not in self.caja_diaria or not self.caja_diaria[fecha_actual].get("abierta", False):
            return
        
        movimiento = {
            "hora": datetime.now().strftime("%H:%M:%S"),
            "tipo": tipo,
            "concepto": concepto,
            "monto": monto,
            "usuario": self.usuario_actual
        }
        
        self.caja_diaria[fecha_actual]["movimientos"].append(movimiento)
        
        if tipo == "ingreso":
            self.caja_diaria[fecha_actual]["total_ingresos"] += monto
        else:
            self.caja_diaria[fecha_actual]["total_egresos"] += monto
        
        self.guardar_caja_diaria()
        self.actualizar_info_caja()
        self.actualizar_movimientos_caja()
    
    def actualizar_info_caja(self):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        if fecha_actual in self.caja_diaria:
            registro = self.caja_diaria[fecha_actual]
            estado = "✅ Abierta" if registro.get("abierta", False) else "🔒 Cerrada"
            
            if hasattr(self, 'label_estado_caja'):
                self.label_estado_caja.config(text=f"Estado: {estado} ({registro.get('usuario', 'N/A')})")
            if hasattr(self, 'label_apertura_caja'):
                self.label_apertura_caja.config(text=f"Apertura: ${registro['apertura']:.2f}")
            if hasattr(self, 'label_ingresos_caja'):
                self.label_ingresos_caja.config(text=f"Ingresos: ${registro.get('total_ingresos', 0):.2f}")
            if hasattr(self, 'label_egresos_caja'):
                self.label_egresos_caja.config(text=f"Egresos: ${registro.get('total_egresos', 0):.2f}")
            if hasattr(self, 'label_saldo_caja'):
                saldo = registro['apertura'] + registro.get('total_ingresos', 0) - registro.get('total_egresos', 0)
                self.label_saldo_caja.config(text=f"Saldo: ${saldo:.2f}")
        else:
            if hasattr(self, 'label_estado_caja'):
                self.label_estado_caja.config(text="Estado: 🔒 Cerrada")
            if hasattr(self, 'label_apertura_caja'):
                self.label_apertura_caja.config(text="Apertura: $0.00")
            if hasattr(self, 'label_ingresos_caja'):
                self.label_ingresos_caja.config(text="Ingresos: $0.00")
            if hasattr(self, 'label_egresos_caja'):
                self.label_egresos_caja.config(text="Egresos: $0.00")
            if hasattr(self, 'label_saldo_caja'):
                self.label_saldo_caja.config(text="Saldo: $0.00")
    
    def actualizar_movimientos_caja(self):
        for item in self.tree_movimientos.get_children():
            self.tree_movimientos.delete(item)
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        if fecha_actual in self.caja_diaria:
            movimientos = self.caja_diaria[fecha_actual].get("movimientos", [])
            for mov in movimientos[-30:]:
                self.tree_movimientos.insert("", "end", values=(
                    mov.get("hora", ""),
                    "💰 Ingreso" if mov.get("tipo") == "ingreso" else "💸 Egreso",
                    mov.get("concepto", ""),
                    f"{mov.get('monto', 0):.2f}",
                    mov.get("usuario", "")
                ))
    
    def actualizar_historial_caja(self):
        for item in self.tree_historial_caja.get_children():
            self.tree_historial_caja.delete(item)
        
        for fecha, registro in sorted(self.caja_diaria.items(), reverse=True):
            if not registro.get("abierta", True):
                saldo = registro.get("cierre", 0)
                self.tree_historial_caja.insert("", "end", values=(
                    fecha,
                    f"{registro.get('apertura', 0):.2f}",
                    f"{registro.get('cierre', 0):.2f}",
                    f"{registro.get('total_ingresos', 0):.2f}",
                    f"{registro.get('total_egresos', 0):.2f}",
                    f"{saldo:.2f}",
                    registro.get('usuario', 'N/A')
                ))
    
    # ==================== BORRAR MOVIMIENTO INDIVIDUAL ====================
    
    def borrar_movimiento_seleccionado(self):
        try:
            seleccion = self.tree_movimientos.selection()
            if not seleccion:
                messagebox.showwarning("Error", "Seleccione un movimiento para borrar")
                return
            
            item = self.tree_movimientos.item(seleccion)
            valores = item['values']
            
            if len(valores) < 4:
                messagebox.showwarning("Error", "Datos del movimiento incompletos")
                return
            
            hora = valores[0]
            tipo_mostrar = valores[1]
            concepto = valores[2]
            monto_str = valores[3].replace('$', '')
            try:
                monto = float(monto_str)
            except:
                messagebox.showwarning("Error", "No se pudo obtener el monto del movimiento")
                return
            
            tipo = "ingreso" if "Ingreso" in tipo_mostrar else "egreso"
            usuario = valores[4] if len(valores) > 4 else "N/A"
            
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            
            if fecha_actual not in self.caja_diaria:
                messagebox.showwarning("Caja", "No hay una caja abierta para hoy.")
                return
            
            registro = self.caja_diaria[fecha_actual]
            
            if not registro.get("abierta", False):
                messagebox.showwarning("Caja", "La caja ya está cerrada. No se pueden borrar movimientos.")
                return
            
            movimiento_encontrado = None
            indice_encontrado = -1
            
            for i, mov in enumerate(registro.get("movimientos", [])):
                if (mov.get("hora") == hora and 
                    mov.get("tipo") == tipo and 
                    mov.get("concepto") == concepto and 
                    abs(mov.get("monto", 0) - monto) < 0.01):
                    movimiento_encontrado = mov
                    indice_encontrado = i
                    break
            
            if movimiento_encontrado is None:
                messagebox.showwarning("Error", "No se encontró el movimiento en la caja")
                return
            
            mensaje = f"⚠️ ¿ELIMINAR MOVIMIENTO?\n\n"
            mensaje += f"📋 Concepto: {concepto}\n"
            mensaje += f"💰 Tipo: {tipo_mostrar}\n"
            mensaje += f"💰 Monto: ${monto:.2f}\n"
            mensaje += f"🕐 Hora: {hora}\n"
            mensaje += f"👤 Usuario: {usuario}\n\n"
            mensaje += f"💰 Saldo actual en caja: ${self.caja_general:.2f}\n"
            
            if tipo == "ingreso":
                mensaje += f"💰 Saldo después de borrar: ${self.caja_general - monto:.2f}\n"
            else:
                mensaje += f"💰 Saldo después de borrar: ${self.caja_general + monto:.2f}\n"
            
            mensaje += f"\n⚠️ Esta acción NO se puede deshacer.\n"
            mensaje += f"¿Está seguro de continuar?"
            
            if not messagebox.askyesno("Confirmar Borrado", mensaje):
                return
            
            registro["movimientos"].pop(indice_encontrado)
            
            if tipo == "ingreso":
                registro["total_ingresos"] = self.redondear(registro.get("total_ingresos", 0) - monto)
                self.caja_general = self.redondear(self.caja_general - monto)
            else:
                registro["total_egresos"] = self.redondear(registro.get("total_egresos", 0) - monto)
                self.caja_general = self.redondear(self.caja_general + monto)
            
            self.guardar_caja_diaria()
            self.guardar_datos()
            
            self.actualizar_info_caja()
            self.actualizar_movimientos_caja()
            self.actualizar_historial_caja()
            self.actualizar_metricas()
            
            messagebox.showinfo("Éxito", 
                f"✅ Movimiento eliminado correctamente.\n\n"
                f"📋 Concepto: {concepto}\n"
                f"💰 Monto: ${monto:.2f}\n"
                f"💰 Saldo actual en caja: ${self.caja_general:.2f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al borrar movimiento:\n{str(e)}")
    
    # ==================== ACTUALIZAR CAJA DESDE REMISIÓN ====================
    
    def actualizar_caja_desde_remision(self):
        try:
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            if fecha_actual not in self.caja_diaria or not self.caja_diaria[fecha_actual].get("abierta", False):
                messagebox.showwarning("Caja", "No hay una caja abierta para hoy. Abra la caja primero.")
                return
            
            total_remisiones = len(self.remisiones_generadas)
            if total_remisiones == 0:
                messagebox.showinfo("Actualizar Caja", "No hay remisiones registradas para procesar.")
                return
            
            total_egresos_remisiones = 0
            total_ingresos_remisiones = 0
            remisiones_procesadas = []
            
            for remision in self.remisiones_generadas:
                tipo = remision.get('tipo', 'remision')
                total = remision.get('total', 0)
                
                if tipo == 'compra':
                    total_egresos_remisiones += total
                    remisiones_procesadas.append(f"Compra #{remision.get('id')}: ${total:.2f}")
                elif tipo == 'venta':
                    total_ingresos_remisiones += total
                    remisiones_procesadas.append(f"Venta #{remision.get('id')}: ${total:.2f}")
            
            if total_egresos_remisiones == 0 and total_ingresos_remisiones == 0:
                messagebox.showinfo("Actualizar Caja", "No hay compras o ventas en las remisiones para procesar.")
                return
            
            registro = self.caja_diaria[fecha_actual]
            saldo_calculado = registro["apertura"] + registro.get("total_ingresos", 0) - registro.get("total_egresos", 0)
            
            mensaje = f"📊 ACTUALIZACIÓN DE CAJA DESDE REMISIONES\n\n"
            mensaje += f"📅 Fecha: {fecha_actual}\n"
            mensaje += f"💰 Saldo actual en caja: ${saldo_calculado:.2f}\n"
            mensaje += f"💰 Saldo en caja general: ${self.caja_general:.2f}\n\n"
            
            mensaje += f"📋 Remisiones a procesar:\n"
            for rem in remisiones_procesadas[:10]:
                mensaje += f"   • {rem}\n"
            if len(remisiones_procesadas) > 10:
                mensaje += f"   ... y {len(remisiones_procesadas) - 10} más\n"
            
            mensaje += f"\n📊 Totales a procesar:\n"
            mensaje += f"   💰 Ingresos por ventas: ${total_ingresos_remisiones:.2f}\n"
            mensaje += f"   💸 Egresos por compras: ${total_egresos_remisiones:.2f}\n"
            mensaje += f"   📊 Neto: ${total_ingresos_remisiones - total_egresos_remisiones:.2f}\n\n"
            
            mensaje += f"⚠️ NOTA: Se agregarán estos movimientos a la caja diaria.\n"
            mensaje += f"Los movimientos duplicados no serán registrados.\n\n"
            mensaje += f"¿Confirmar la actualización?"
            
            if not messagebox.askyesno("Confirmar Actualización", mensaje):
                return
            
            movimientos_agregados = 0
            total_egresos_agregados = 0
            total_ingresos_agregados = 0
            
            conceptos_existentes = set()
            for mov in registro.get("movimientos", []):
                conceptos_existentes.add(mov.get("concepto", ""))
            
            for remision in self.remisiones_generadas:
                tipo = remision.get('tipo', 'remision')
                total = remision.get('total', 0)
                remision_id = remision.get('id', '')
                cliente = remision.get('cliente', 'N/A')
                
                if tipo == 'compra':
                    concepto = f"Compra remisión #{remision_id} - {cliente}"
                    if concepto not in conceptos_existentes:
                        self.registrar_movimiento_caja("egreso", concepto, total)
                        total_egresos_agregados += total
                        movimientos_agregados += 1
                        conceptos_existentes.add(concepto)
                        
                elif tipo == 'venta':
                    concepto = f"Venta remisión #{remision_id} - {cliente}"
                    if concepto not in conceptos_existentes:
                        self.registrar_movimiento_caja("ingreso", concepto, total)
                        total_ingresos_agregados += total
                        movimientos_agregados += 1
                        conceptos_existentes.add(concepto)
            
            if movimientos_agregados == 0:
                messagebox.showinfo("Actualizar Caja", "No se agregaron nuevos movimientos. Todos ya estaban registrados.")
                return
            
            self.caja_general = self.redondear(self.caja_general + total_ingresos_agregados - total_egresos_agregados)
            
            self.guardar_datos()
            self.guardar_caja_diaria()
            
            self.actualizar_info_caja()
            self.actualizar_movimientos_caja()
            self.actualizar_historial_caja()
            self.actualizar_metricas()
            
            mensaje_exito = f"✅ CAJA ACTUALIZADA EXITOSAMENTE\n\n"
            mensaje_exito += f"📋 Movimientos agregados: {movimientos_agregados}\n"
            mensaje_exito += f"💰 Ingresos agregados: ${total_ingresos_agregados:.2f}\n"
            mensaje_exito += f"💰 Egresos agregados: ${total_egresos_agregados:.2f}\n"
            mensaje_exito += f"📊 Neto: ${total_ingresos_agregados - total_egresos_agregados:.2f}\n\n"
            mensaje_exito += f"💰 Nuevo saldo en caja general: ${self.caja_general:.2f}"
            
            messagebox.showinfo("Éxito", mensaje_exito)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al actualizar caja desde remisión:\n{str(e)}")
    
    # ==================== ELIMINAR REMISIÓN ====================
    
    def eliminar_remision(self):
        try:
            if not hasattr(self, 'tree_remisiones'):
                messagebox.showwarning("Error", "No se encontró la lista de remisiones")
                return
            
            seleccion = self.tree_remisiones.selection()
            if not seleccion:
                messagebox.showwarning("Error", "Seleccione una remisión para eliminar")
                return
            
            item = self.tree_remisiones.item(seleccion)
            valores = item['values']
            remision_id = int(valores[0])
            remision_cliente = valores[2] if len(valores) > 2 else "N/A"
            remision_total = float(valores[5]) if len(valores) > 5 else 0
            
            remision_encontrada = None
            for r in self.remisiones_generadas:
                if r.get('id') == remision_id:
                    remision_encontrada = r
                    break
            
            if not remision_encontrada:
                messagebox.showwarning("Error", "Remisión no encontrada en la lista")
                return
            
            tipo = remision_encontrada.get('tipo', 'remision')
            tipo_mostrar = {
                'remision': '📋 Remisión',
                'venta': '🛒 Venta',
                'compra': '📦 Compra'
            }.get(tipo, '📋 Remisión')
            
            afecta_caja = tipo in ['venta', 'compra']
            
            mensaje = f"⚠️ ¿ELIMINAR REMISIÓN #{remision_id}?\n\n"
            mensaje += f"📋 Tipo: {tipo_mostrar}\n"
            mensaje += f"👤 Cliente: {remision_cliente}\n"
            mensaje += f"💰 Total: ${remision_total:.2f}\n"
            mensaje += f"📦 Items: {len(remision_encontrada.get('items', []))}\n"
            mensaje += f"📅 Fecha: {remision_encontrada.get('fecha', 'N/A')}\n\n"
            
            if afecta_caja:
                mensaje += f"⚠️ Esta remisión afecta la caja.\n"
                mensaje += f"💰 Se revertirá el movimiento de caja asociado.\n\n"
            
            mensaje += f"Esta acción no se puede deshacer. ¿Confirmar?"
            
            if not messagebox.askyesno("Confirmar Eliminación", mensaje):
                return
            
            self.remisiones_generadas = [r for r in self.remisiones_generadas if r.get('id') != remision_id]
            
            if afecta_caja:
                fecha_actual = datetime.now().strftime("%Y-%m-%d")
                if fecha_actual in self.caja_diaria:
                    registro = self.caja_diaria[fecha_actual]
                    movimientos_originales = registro.get("movimientos", [])
                    
                    movimientos_a_eliminar = []
                    for mov in movimientos_originales:
                        concepto = mov.get("concepto", "")
                        if tipo == 'venta' and f"Venta remisión #{remision_id}" in concepto:
                            movimientos_a_eliminar.append(mov)
                        elif tipo == 'compra' and f"Compra remisión #{remision_id}" in concepto:
                            movimientos_a_eliminar.append(mov)
                    
                    if movimientos_a_eliminar:
                        for mov in movimientos_a_eliminar:
                            monto = mov.get("monto", 0)
                            tipo_mov = mov.get("tipo", "")
                            
                            if tipo_mov == "ingreso":
                                registro["total_ingresos"] = self.redondear(registro.get("total_ingresos", 0) - monto)
                            else:
                                registro["total_egresos"] = self.redondear(registro.get("total_egresos", 0) - monto)
                            
                            if tipo_mov == "ingreso":
                                self.caja_general = self.redondear(self.caja_general - monto)
                            else:
                                self.caja_general = self.redondear(self.caja_general + monto)
                        
                        registro["movimientos"] = [m for m in movimientos_originales if m not in movimientos_a_eliminar]
                        self.guardar_caja_diaria()
                        self.actualizar_info_caja()
                        self.actualizar_movimientos_caja()
                
                self.compras = [c for c in self.compras if c.get('remision_id') != remision_id]
                self.compras_mayoreo = [c for c in self.compras_mayoreo if c.get('remision_id') != remision_id]
            
            self.guardar_datos()
            
            self.actualizar_lista_remisiones()
            self.actualizar_historial()
            self.actualizar_metricas()
            self.actualizar_tabla_inventario()
            
            if hasattr(self, 'tree_remisiones_guardadas'):
                self.actualizar_remisiones_guardadas()
            
            messagebox.showinfo("Éxito", f"✅ Remisión #{remision_id} eliminada correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar remisión:\n{str(e)}")
    
    # ==================== SERVIDOR WEB PARA CELULAR ====================
    
    def iniciar_servidor_web(self):
        try:
            def handler_with_sistema(*args, **kwargs):
                return self.CrearHandlerWeb(self, *args, **kwargs)
            
            self.servidor_web = socketserver.TCPServer(("", PORT), handler_with_sistema)
            
            thread = threading.Thread(target=self.servidor_web.serve_forever, daemon=True)
            thread.start()
            
            hostname = socket.gethostname()
            ip_local = socket.gethostbyname(hostname)
            
            print(f"✅ Servidor web iniciado en http://{ip_local}:{PORT}")
            print(f"📱 Accede desde tu celular en: http://{ip_local}:{PORT}")
            
            messagebox.showinfo("Servidor Web", 
                f"✅ Servidor web iniciado\n\n"
                f"📱 Desde tu celular accede a:\n"
                f"http://{ip_local}:{PORT}\n\n"
                f"⚠️ Asegúrate de que ambos dispositivos estén\n"
                f"en la misma red WiFi.")
        except Exception as e:
            print(f"❌ Error al iniciar servidor web: {e}")
            messagebox.showerror("Error", f"No se pudo iniciar el servidor web:\n{str(e)}")
    
    class CrearHandlerWeb(http.server.SimpleHTTPRequestHandler):
        def __init__(self, sistema, *args, **kwargs):
            self.sistema = sistema
            super().__init__(*args, **kwargs)
        
        def log_message(self, format, *args):
            pass
        
        def do_GET(self):
            try:
                if self.path == '/':
                    self.enviar_pagina_principal()
                elif self.path == '/inventario':
                    self.enviar_inventario()
                elif self.path == '/ventas':
                    self.enviar_ventas()
                elif self.path == '/caja':
                    self.enviar_caja()
                elif self.path == '/historial':
                    self.enviar_historial()
                elif self.path == '/precios':
                    self.enviar_editar_precios()
                elif self.path == '/posventa':
                    self.enviar_pos_venta()
                elif self.path.startswith('/api/inventario'):
                    self.enviar_api_inventario()
                elif self.path.startswith('/api/ventas'):
                    self.enviar_api_ventas()
                elif self.path.startswith('/api/remisiones'):
                    self.enviar_api_remisiones()
                elif self.path.startswith('/api/descargar_remision'):
                    self.enviar_descargar_remision()
                elif self.path.startswith('/api/descargar_remision_venta'):
                    self.enviar_descargar_remision_venta()
                elif self.path.startswith('/api/pos_venta'):
                    self.enviar_api_pos_venta()
                elif self.path.startswith('/api/registrar_venta_simulada'):
                    self.registrar_venta_simulada()
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Pagina no encontrada')
            except Exception as e:
                print(f"Error en servidor web: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
        
        def do_POST(self):
            try:
                if self.path.startswith('/api/actualizar_precio'):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    
                    seccion = data.get('seccion')
                    material = data.get('material')
                    nuevo_precio = data.get('precio')
                    
                    if seccion and material and nuevo_precio is not None:
                        nuevo_precio = round(float(nuevo_precio), 2)
                        
                        if seccion in self.sistema.materiales:
                            for m in self.sistema.materiales[seccion]:
                                if m['nombre'] == material:
                                    m['precio_venta'] = nuevo_precio
                                    break
                        
                        if material in self.sistema.inventario:
                            self.sistema.inventario[material]['precio_venta'] = nuevo_precio
                        
                        self.sistema.guardar_datos()
                        self.sistema.actualizar_tabla_inventario()
                        self.sistema.actualizar_lista_venta()
                        self.sistema.actualizar_todas_tablas_materiales()
                        
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": True, "message": "Precio actualizado correctamente"}).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "Datos incompletos"}).encode('utf-8'))
                elif self.path.startswith('/api/descargar_remision'):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    remision_id = data.get('remision_id')
                    
                    if remision_id:
                        remision = None
                        for r in self.sistema.remisiones_generadas:
                            if r.get('id') == remision_id:
                                remision = r
                                break
                        
                        if remision:
                            html_content = self.sistema.generar_html_nota(remision)
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.send_header('Content-Disposition', f'attachment; filename=remision_{remision_id}.html')
                            self.end_headers()
                            self.wfile.write(html_content.encode('utf-8'))
                        else:
                            self.send_response(404)
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": False, "message": "Remisión no encontrada"}).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "ID de remisión requerido"}).encode('utf-8'))
                elif self.path.startswith('/api/registrar_venta_movil'):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    
                    cliente = data.get('cliente')
                    material = data.get('material')
                    cantidad = data.get('cantidad')
                    precio = data.get('precio')
                    
                    if cliente and material and cantidad and precio:
                        resultado = self.sistema.registrar_venta_desde_movil(cliente, material, cantidad, precio)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(resultado).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "Datos incompletos"}).encode('utf-8'))
                elif self.path.startswith('/api/registrar_venta_simulada'):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    
                    empresa = data.get('empresa')
                    material = data.get('material')
                    cantidad = data.get('cantidad')
                    
                    if empresa and material and cantidad:
                        resultado = self.sistema.registrar_venta_simulada(empresa, material, cantidad)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(resultado).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "Datos incompletos"}).encode('utf-8'))
                elif self.path.startswith('/api/eliminar_venta_simulada'):
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode('utf-8'))
                    venta_id = data.get('venta_id')
                    
                    if venta_id:
                        resultado = self.sistema.eliminar_venta_simulada(venta_id)
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(resultado).encode('utf-8'))
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "message": "ID de venta requerido"}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode('utf-8'))
        
        def enviar_pagina_principal(self):
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Reciclaje Industrial - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
                    .header h1 { font-size: 24px; }
                    .header p { font-size: 14px; opacity: 0.8; }
                    .menu { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
                    .menu-item { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-decoration: none; color: #2c3e50; font-weight: bold; transition: transform 0.2s; }
                    .menu-item:active { transform: scale(0.95); }
                    .icon { font-size: 40px; display: block; margin-bottom: 10px; }
                    .footer { margin-top: 20px; text-align: center; color: #7f8c8d; font-size: 12px; }
                    .status { background: #ecf0f1; padding: 10px; border-radius: 10px; margin-top: 10px; text-align: center; font-size: 14px; }
                    .badge-nuevo { background: #e74c3c; color: white; font-size: 10px; padding: 2px 8px; border-radius: 10px; margin-left: 5px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>♻️ Reciclaje Industrial</h1>
                    <p>Sistemas Computerionales de México</p>
                    <p style="font-size: 12px; margin-top: 5px;">📱 Versión Móvil</p>
                </div>
                <div class="menu">
                    <a href="/inventario" class="menu-item">
                        <span class="icon">📦</span>
                        Inventario
                    </a>
                    <a href="/ventas" class="menu-item">
                        <span class="icon">🛒</span>
                        Ventas
                    </a>
                    <a href="/caja" class="menu-item">
                        <span class="icon">💰</span>
                        Caja Diaria
                    </a>
                    <a href="/historial" class="menu-item">
                        <span class="icon">📜</span>
                        Historial
                    </a>
                    <a href="/precios" class="menu-item" style="background: #e8f5e9;">
                        <span class="icon">💲</span>
                        Editar Precios
                        <span class="badge-nuevo">NUEVO</span>
                    </a>
                    <a href="/posventa" class="menu-item" style="background: #fce4ec;">
                        <span class="icon">📊</span>
                        Pos Venta
                        <span class="badge-nuevo">NUEVO</span>
                    </a>
                    <a href="#" class="menu-item" style="background: #fff3e0;" onclick="mostrarRemisiones()">
                        <span class="icon">📋</span>
                        Mis Remisiones
                        <span class="badge-nuevo">NUEVO</span>
                    </a>
                </div>
                <div class="status">
                    📊 Datos en tiempo real
                </div>
                <div id="remisiones-container" style="display:none; margin-top: 15px;">
                    <div class="header" style="background: #2980b9;">
                        <h2>📋 Mis Remisiones</h2>
                    </div>
                    <div id="lista-remisiones"></div>
                </div>
                <div class="footer">
                    <p>Última actualización: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                    <p style="margin-top: 5px;">🔗 Conectado al sistema principal</p>
                </div>
                <script>
                    function mostrarRemisiones() {
                        var container = document.getElementById('remisiones-container');
                        if (container.style.display === 'none') {
                            container.style.display = 'block';
                            cargarRemisiones();
                        } else {
                            container.style.display = 'none';
                        }
                    }
                    
                    function cargarRemisiones() {
                        fetch('/api/remisiones')
                            .then(response => response.json())
                            .then(data => {
                                var lista = document.getElementById('lista-remisiones');
                                lista.innerHTML = '';
                                if (data.remisiones.length === 0) {
                                    lista.innerHTML = '<div style="text-align:center;padding:20px;color:#7f8c8d;">No hay remisiones registradas</div>';
                                    return;
                                }
                                data.remisiones.forEach(function(rem) {
                                    var div = document.createElement('div');
                                    div.style.cssText = 'background:white;border-radius:10px;padding:15px;margin-bottom:10px;box-shadow:0 2px 5px rgba(0,0,0,0.1);';
                                    div.innerHTML = `
                                        <div style="display:flex;justify-content:space-between;align-items:center;">
                                            <div>
                                                <strong>#${rem.id}</strong> - ${rem.cliente}
                                                <div style="font-size:12px;color:#7f8c8d;">${rem.fecha}</div>
                                            </div>
                                            <div style="text-align:right;">
                                                <div style="font-weight:bold;color:#27ae60;">$${rem.total.toFixed(2)}</div>
                                                <div style="font-size:11px;color:#7f8c8d;">${rem.items} items</div>
                                            </div>
                                        </div>
                                        <div style="margin-top:10px;display:flex;gap:5px;">
                                            <button onclick="descargarRemision(${rem.id})" style="background:#3498db;color:white;border:none;padding:5px 15px;border-radius:5px;cursor:pointer;">📥 Descargar</button>
                                            <button onclick="verRemision(${rem.id})" style="background:#2c3e50;color:white;border:none;padding:5px 15px;border-radius:5px;cursor:pointer;">👁️ Ver</button>
                                        </div>
                                    `;
                                    lista.appendChild(div);
                                });
                            })
                            .catch(error => {
                                document.getElementById('lista-remisiones').innerHTML = '<div style="text-align:center;padding:20px;color:red;">Error al cargar remisiones</div>';
                            });
                    }
                    
                    function descargarRemision(id) {
                        fetch('/api/descargar_remision', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ remision_id: id })
                        })
                        .then(response => response.blob())
                        .then(blob => {
                            var url = window.URL.createObjectURL(blob);
                            var a = document.createElement('a');
                            a.href = url;
                            a.download = `remision_${id}.html`;
                            document.body.appendChild(a);
                            a.click();
                            a.remove();
                        })
                        .catch(error => {
                            alert('Error al descargar la remisión');
                        });
                    }
                    
                    function verRemision(id) {
                        fetch('/api/descargar_remision', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ remision_id: id })
                        })
                        .then(response => response.blob())
                        .then(blob => {
                            var url = window.URL.createObjectURL(blob);
                            window.open(url, '_blank');
                        })
                        .catch(error => {
                            alert('Error al ver la remisión');
                        });
                    }
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_pos_venta(self):
            ventas_simuladas = self.sistema.ventas_simuladas[-30:]
            total_simulado = sum(v.get('total', 0) for v in ventas_simuladas)
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Pos Venta - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .form-group { margin-bottom: 10px; }
                    .form-group label { display: block; font-weight: bold; font-size: 14px; margin-bottom: 3px; }
                    .form-group input, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
                    .btn { background: #27ae60; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-size: 16px; cursor: pointer; width: 100%; }
                    .btn:active { transform: scale(0.95); }
                    .btn-danger { background: #e74c3c; }
                    .btn-secondary { background: #3498db; }
                    .venta-item { padding: 10px 0; border-bottom: 1px solid #ecf0f1; display: flex; justify-content: space-between; align-items: center; }
                    .venta-item:last-child { border-bottom: none; }
                    .venta-total { color: #27ae60; font-weight: bold; }
                    .total-box { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-top: 10px; text-align: center; }
                    .total-box p { margin: 3px 0; }
                    .no-data { text-align: center; color: #7f8c8d; padding: 20px; }
                    .stock-info { font-size: 12px; color: #7f8c8d; }
                    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; }
                    .badge-success { background: #27ae60; color: white; }
                    .badge-danger { background: #e74c3c; color: white; }
                    .badge-warning { background: #f39c12; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>📊 Pos Venta (Simulación)</h1>
                </div>
                
                <div class="card">
                    <h3 style="margin-bottom:10px;">📝 Registrar Venta Simulada</h3>
                    <div class="form-group">
                        <label>Empresa:</label>
                        <select id="empresa_select" onchange="cargarMaterialesPosVenta()">
                            <option value="">Seleccionar empresa...</option>
                            <option value="Grupo Imperio Steel">Grupo Imperio Steel</option>
                            <option value="Recicladora Reforma">Recicladora Reforma</option>
                            <option value="Centro de Acopio Tláhuac">Centro de Acopio Tláhuac</option>
                            <option value="Chinos">Chinos</option>
                            <option value="La Batería Verde">La Batería Verde</option>
                            <option value="Green Power Tezoyuca">Green Power Tezoyuca</option>
                            <option value="JRG Comercial S.A. de C.V.">JRG Comercial S.A. de C.V.</option>
                            <option value="Otro">Otro</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Material:</label>
                        <select id="material_posventa">
                            <option value="">Seleccionar material...</option>
                        </select>
                        <div id="stock_info" class="stock-info"></div>
                    </div>
                    <div class="form-group">
                        <label>Cantidad (kg):</label>
                        <input type="number" id="cantidad_posventa" value="1" min="0.01" step="0.01">
                    </div>
                    <button class="btn" onclick="registrarVentaSimulada()">✅ Registrar Venta Simulada</button>
                </div>
                
                <div class="total-box">
                    <p>💰 Total Simulado: $""" + f"{total_simulado:.2f}" + """</p>
                    <p style="font-size:12px;opacity:0.8;">""" + str(len(ventas_simuladas)) + """ ventas registradas</p>
                </div>
                
                <div id="lista-ventas-simuladas">
            """
            
            if not ventas_simuladas:
                html += '<div class="no-data">📭 No hay ventas simuladas registradas</div>'
            else:
                for venta in reversed(ventas_simuladas):
                    html += f"""
                    <div class="card" id="venta_{venta.get('id', 0)}">
                        <div class="venta-item">
                            <div>
                                <strong>{venta.get('empresa', 'N/A')}</strong>
                                <div style="font-size:12px;color:#7f8c8d;">{venta.get('material', 'N/A')} - {venta.get('cantidad', 0):.2f} kg</div>
                                <div style="font-size:11px;color:#95a5a6;">{venta.get('fecha', '')[:16]}</div>
                            </div>
                            <div style="text-align:right;">
                                <div class="venta-total">${venta.get('total', 0):.2f}</div>
                                <button onclick="eliminarVentaSimulada({venta.get('id', 0)})" style="background:#e74c3c;color:white;border:none;padding:2px 10px;border-radius:3px;cursor:pointer;font-size:11px;">🗑️</button>
                            </div>
                        </div>
                    </div>
                    """
            
            html += """
                </div>
                
                <script>
                    function cargarMaterialesPosVenta() {
                        fetch('/api/pos_venta')
                            .then(response => response.json())
                            .then(data => {
                                var select = document.getElementById('material_posventa');
                                select.innerHTML = '<option value="">Seleccionar material...</option>';
                                data.materiales.forEach(function(m) {
                                    var option = document.createElement('option');
                                    option.value = m.nombre;
                                    option.textContent = m.nombre + ' ($' + m.precio_venta.toFixed(2) + '/kg)';
                                    select.appendChild(option);
                                });
                            })
                            .catch(error => {
                                console.error('Error:', error);
                            });
                    }
                    
                    function registrarVentaSimulada() {
                        var empresa = document.getElementById('empresa_select').value;
                        var material = document.getElementById('material_posventa').value;
                        var cantidad = parseFloat(document.getElementById('cantidad_posventa').value);
                        
                        if (!empresa) {
                            alert('Seleccione una empresa');
                            return;
                        }
                        if (!material) {
                            alert('Seleccione un material');
                            return;
                        }
                        if (!cantidad || cantidad <= 0) {
                            alert('Ingrese una cantidad válida');
                            return;
                        }
                        
                        fetch('/api/registrar_venta_simulada', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                empresa: empresa,
                                material: material,
                                cantidad: cantidad
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(data.message);
                                location.reload();
                            } else {
                                alert('Error: ' + data.message);
                            }
                        })
                        .catch(error => {
                            alert('Error al registrar la venta: ' + error);
                        });
                    }
                    
                    function eliminarVentaSimulada(id) {
                        if (!confirm('¿Eliminar esta venta simulada?')) return;
                        
                        fetch('/api/eliminar_venta_simulada', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ venta_id: id })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                location.reload();
                            } else {
                                alert('Error: ' + data.message);
                            }
                        })
                        .catch(error => {
                            alert('Error al eliminar: ' + error);
                        });
                    }
                    
                    cargarMaterialesPosVenta();
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_api_pos_venta(self):
            materiales = []
            if 'pos_venta' in self.sistema.materiales:
                for m in self.sistema.materiales['pos_venta']:
                    materiales.append({
                        'nombre': m['nombre'],
                        'precio_venta': m['precio_venta'],
                        'empresa': m.get('empresa', 'Sin asignar')
                    })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({"materiales": materiales}).encode('utf-8'))
        
        def registrar_venta_simulada(self):
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                empresa = data.get('empresa')
                material = data.get('material')
                cantidad = data.get('cantidad')
                
                resultado = self.sistema.registrar_venta_simulada(empresa, material, cantidad)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(resultado).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "message": str(e)}).encode('utf-8'))
        
        def enviar_editar_precios(self):
            materiales_por_seccion = {}
            for seccion, items in self.sistema.materiales.items():
                materiales_por_seccion[seccion] = items
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Editar Precios - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .precio-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #ecf0f1; }
                    .precio-item:last-child { border-bottom: none; }
                    .material-name { font-weight: bold; font-size: 15px; }
                    .precio-actual { color: #7f8c8d; font-size: 13px; }
                    .precio-input { width: 80px; padding: 5px; border: 2px solid #ddd; border-radius: 5px; font-size: 14px; text-align: center; }
                    .precio-input:focus { border-color: #2c3e50; outline: none; }
                    .btn-actualizar { background: #27ae60; color: white; border: none; padding: 5px 15px; border-radius: 5px; cursor: pointer; font-size: 13px; }
                    .btn-actualizar:active { transform: scale(0.95); }
                    .btn-actualizar:disabled { background: #95a5a6; cursor: not-allowed; }
                    .seccion-titulo { background: #2c3e50; color: white; padding: 8px 15px; border-radius: 5px; margin: 10px 0; font-size: 14px; }
                    .mensaje { padding: 10px; border-radius: 5px; margin: 10px 0; display: none; }
                    .mensaje-exito { background: #d5f5e3; color: #1a7a42; display: block; }
                    .mensaje-error { background: #fadbd8; color: #922b21; display: block; }
                    .loading { text-align: center; padding: 10px; color: #7f8c8d; }
                    .search { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 15px; font-size: 16px; }
                    .btn-recargar { background: #3498db; color: white; border: none; padding: 8px 20px; border-radius: 5px; cursor: pointer; font-size: 14px; margin-bottom: 15px; width: 100%; }
                    .btn-recargar:active { transform: scale(0.95); }
                    .ganancia-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 5px; }
                    .ganancia-especial { background: #e74c3c; color: white; }
                    .ganancia-normal { background: #27ae60; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>💲 Editar Precios</h1>
                </div>
                <div id="mensaje" class="mensaje"></div>
                <button class="btn-recargar" onclick="recargarPagina()">🔄 Recargar Precios</button>
                <input type="text" class="search" placeholder="🔍 Buscar material..." id="search" onkeyup="filtrar()">
                <div id="lista-precios">
            """
            
            for seccion, items in materiales_por_seccion.items():
                html += f"""
                <div class="seccion-titulo">📁 {seccion.upper()}</div>
                """
                for item in items:
                    nombre = item.get('nombre', '')
                    precio = self.sistema.redondear(item.get('precio_venta', 0))
                    porcentaje = self.sistema.obtener_porcentaje_ganancia(nombre)
                    ganancia = self.sistema.calcular_ganancia(nombre, precio)
                    precio_cliente = self.sistema.calcular_precio_cliente(nombre, precio)
                    
                    es_especial = nombre.lower() in [m.lower() for m in PORCENTAJES_ESPECIALES]
                    ganancia_tag = f'<span class="ganancia-tag {"ganancia-especial" if es_especial else "ganancia-normal"}">{porcentaje*100:.1f}% ganancia</span>'
                    
                    html += f"""
                    <div class="card precio-item" data-material="{nombre.lower()}">
                        <div>
                            <div class="material-name">{nombre} {ganancia_tag}</div>
                            <div class="precio-actual">Precio Venta: ${precio:.2f}</div>
                            <div class="precio-actual" style="color:#27ae60;">Precio Cliente: ${precio_cliente:.2f}</div>
                            <div class="precio-actual" style="color:#e74c3c;">Ganancia: ${ganancia:.2f} ({porcentaje*100:.1f}%)</div>
                        </div>
                        <div>
                            <input type="number" class="precio-input" id="precio_{seccion}_{nombre}" 
                                   value="{precio:.2f}" step="0.01" min="0">
                            <button class="btn-actualizar" onclick="actualizarPrecio('{seccion}', '{nombre}')">Actualizar</button>
                        </div>
                    </div>
                    """
            
            html += """
                </div>
                <script>
                    function recargarPagina() {
                        mostrarMensaje('🔄 Recargando precios...', 'exito');
                        setTimeout(function() {
                            location.reload();
                        }, 500);
                    }
                    
                    function filtrar() {
                        var input = document.getElementById('search');
                        var filter = input.value.toLowerCase();
                        var cards = document.querySelectorAll('.precio-item');
                        for (var i = 0; i < cards.length; i++) {
                            var material = cards[i].getAttribute('data-material');
                            if (material.indexOf(filter) > -1) {
                                cards[i].style.display = '';
                            } else {
                                cards[i].style.display = 'none';
                            }
                        }
                    }
                    
                    function mostrarMensaje(texto, tipo) {
                        var mensaje = document.getElementById('mensaje');
                        mensaje.textContent = texto;
                        mensaje.className = 'mensaje mensaje-' + tipo;
                        setTimeout(function() {
                            mensaje.className = 'mensaje';
                        }, 5000);
                    }
                    
                    function actualizarPrecio(seccion, material) {
                        var input = document.getElementById('precio_' + seccion + '_' + material);
                        var nuevoPrecio = parseFloat(input.value);
                        
                        if (isNaN(nuevoPrecio) || nuevoPrecio < 0) {
                            mostrarMensaje('❌ Ingrese un precio válido', 'error');
                            return;
                        }
                        
                        var btn = event.target;
                        btn.disabled = true;
                        btn.textContent = '⏳...';
                        
                        fetch('/api/actualizar_precio', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                seccion: seccion,
                                material: material,
                                precio: nuevoPrecio
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                mostrarMensaje('✅ ' + data.message, 'exito');
                                var precioActual = input.parentElement.parentElement.querySelector('.precio-actual');
                                precioActual.textContent = 'Precio Venta: $' + nuevoPrecio.toFixed(2);
                            } else {
                                mostrarMensaje('❌ ' + data.message, 'error');
                            }
                        })
                        .catch(error => {
                            mostrarMensaje('❌ Error al actualizar: ' + error, 'error');
                        })
                        .finally(() => {
                            btn.disabled = false;
                            btn.textContent = 'Actualizar';
                        });
                    }
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_inventario(self):
            datos = self.sistema.inventario
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Inventario - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .search { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 15px; font-size: 16px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .material-name { font-weight: bold; font-size: 16px; }
                    .material-info { display: flex; justify-content: space-between; margin-top: 5px; color: #7f8c8d; font-size: 14px; }
                    .stock { font-weight: bold; }
                    .stock-low { color: #e74c3c; }
                    .stock-medium { color: #f39c12; }
                    .stock-high { color: #27ae60; }
                    .section-tag { background: #3498db; color: white; padding: 2px 10px; border-radius: 20px; font-size: 11px; }
                    .total { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center; }
                    .total p { margin: 3px 0; }
                    .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
                    .badge-success { background: #27ae60; color: white; }
                    .badge-danger { background: #e74c3c; color: white; }
                    .badge-warning { background: #f39c12; color: white; }
                    .ganancia-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 5px; }
                    .ganancia-especial { background: #e74c3c; color: white; }
                    .ganancia-normal { background: #27ae60; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>📦 Inventario</h1>
                </div>
                <input type="text" class="search" placeholder="🔍 Buscar material..." id="search" onkeyup="filtrar()">
                <div id="lista-materiales">
            """
            
            total_stock = 0
            total_valor = 0
            materiales_con_stock = 0
            
            for material, datos in sorted(datos.items()):
                stock = datos.get("stock", 0)
                precio = datos.get("precio_venta", 0)
                seccion = datos.get("seccion", "inventario")
                valor = self.sistema.redondear(stock * precio)
                total_stock += stock
                total_valor += valor
                if stock > 0:
                    materiales_con_stock += 1
                
                if stock == 0:
                    stock_class = "stock-low"
                    badge = '<span class="badge badge-danger">Sin stock</span>'
                elif stock < 10:
                    stock_class = "stock-medium"
                    badge = '<span class="badge badge-warning">Stock bajo</span>'
                else:
                    stock_class = "stock-high"
                    badge = '<span class="badge badge-success">Stock OK</span>'
                
                porcentaje = self.sistema.obtener_porcentaje_ganancia(material)
                es_especial = material.lower() in [m.lower() for m in PORCENTAJES_ESPECIALES]
                ganancia_tag = f'<span class="ganancia-tag {"ganancia-especial" if es_especial else "ganancia-normal"}">{porcentaje*100:.1f}%</span>'
                precio_cliente = self.sistema.calcular_precio_cliente(material, precio)
                
                html += f"""
                <div class="card" data-material="{material.lower()}">
                    <div class="material-name">{material} {badge} {ganancia_tag}</div>
                    <div class="material-info">
                        <span>Sección: <span class="section-tag">{seccion}</span></span>
                        <span class="stock {stock_class}">{stock:.2f} kg</span>
                    </div>
                    <div class="material-info">
                        <span>💰 ${precio:.2f}/kg</span>
                        <span>💎 ${valor:.2f}</span>
                    </div>
                    <div class="material-info">
                        <span style="color:#27ae60;">Precio Cliente: ${precio_cliente:.2f}/kg</span>
                        <span style="color:#e74c3c;">Ganancia: ${self.sistema.calcular_ganancia(material, precio):.2f}/kg</span>
                    </div>
                </div>
                """
            
            html += f"""
                </div>
                <div class="total">
                    <p>📊 Total Stock: {total_stock:.2f} kg</p>
                    <p>💰 Valor Total: ${total_valor:.2f}</p>
                    <p style="font-size:12px;opacity:0.8;">{materiales_con_stock} materiales con stock</p>
                </div>
                
                <script>
                    function filtrar() {{
                        var input = document.getElementById('search');
                        var filter = input.value.toLowerCase();
                        var cards = document.querySelectorAll('.card');
                        for (var i = 0; i < cards.length; i++) {{
                            var material = cards[i].getAttribute('data-material');
                            if (material.indexOf(filter) > -1) {{
                                cards[i].style.display = '';
                            }} else {{
                                cards[i].style.display = 'none';
                            }}
                        }}
                    }}
                </script>
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_ventas(self):
            ventas = self.sistema.ventas[-30:]
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Ventas - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .venta-cliente { font-weight: bold; font-size: 16px; }
                    .venta-info { display: flex; justify-content: space-between; margin-top: 5px; color: #7f8c8d; font-size: 14px; }
                    .venta-total { color: #27ae60; font-weight: bold; font-size: 18px; }
                    .venta-fecha { color: #95a5a6; font-size: 12px; }
                    .total { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center; }
                    .total p { margin: 3px 0; }
                    .no-data { text-align: center; color: #7f8c8d; padding: 30px; }
                    .ganancia-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 5px; }
                    .ganancia-especial { background: #e74c3c; color: white; }
                    .ganancia-normal { background: #27ae60; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>🛒 Ventas</h1>
                </div>
            """
            
            if not ventas:
                html += '<div class="no-data">📭 No hay ventas registradas</div>'
            else:
                total_ventas = 0
                for venta in reversed(ventas):
                    total_ventas += venta.get("total", 0)
                    material = venta.get('material', 'N/A')
                    porcentaje = self.sistema.obtener_porcentaje_ganancia(material)
                    es_especial = material.lower() in [m.lower() for m in PORCENTAJES_ESPECIALES]
                    ganancia_tag = f'<span class="ganancia-tag {"ganancia-especial" if es_especial else "ganancia-normal"}">{porcentaje*100:.1f}%</span>'
                    
                    html += f"""
                    <div class="card">
                        <div class="venta-cliente">{venta.get('cliente', 'N/A')}</div>
                        <div class="venta-info">
                            <span>{material} {ganancia_tag}</span>
                            <span>{venta.get('cantidad', 0):.2f} kg</span>
                        </div>
                        <div class="venta-info">
                            <span class="venta-fecha">{venta.get('fecha', '')[:16]}</span>
                            <span class="venta-total">${venta.get('total', 0):.2f}</span>
                        </div>
                        <div class="venta-info" style="color:#e74c3c;font-size:12px;">
                            <span>Ganancia: ${venta.get('ganancia', 0):.2f}</span>
                        </div>
                    </div>
                    """
                
                html += f"""
                <div class="total">
                    <p>💰 Total Ventas: ${total_ventas:.2f}</p>
                    <p style="font-size:12px;opacity:0.8;">Últimas {len(ventas)} ventas</p>
                </div>
                """
            
            html += """
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_caja(self):
            caja = self.sistema.caja_diaria
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Caja Diaria - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ecf0f1; }
                    .info-row:last-child { border-bottom: none; }
                    .label { color: #7f8c8d; }
                    .value { font-weight: bold; }
                    .value.ingreso { color: #27ae60; }
                    .value.egreso { color: #e74c3c; }
                    .value.abierta { color: #27ae60; }
                    .value.cerrada { color: #e74c3c; }
                    .movimiento { padding: 5px 0; border-bottom: 1px solid #ecf0f1; font-size: 14px; display: flex; justify-content: space-between; }
                    .movimiento-ingreso { color: #27ae60; }
                    .movimiento-egreso { color: #e74c3c; }
                    .subtitle { font-size: 14px; margin-bottom: 10px; color: #2c3e50; }
                    .no-data { text-align: center; color: #7f8c8d; padding: 20px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>💰 Caja Diaria</h1>
                </div>
            """
            
            if fecha_actual in caja:
                registro = caja[fecha_actual]
                estado = "✅ Abierta" if registro.get("abierta", False) else "🔒 Cerrada"
                estado_class = "abierta" if registro.get("abierta", False) else "cerrada"
                saldo = registro["apertura"] + registro.get("total_ingresos", 0) - registro.get("total_egresos", 0)
                
                html += f"""
                <div class="card">
                    <div class="info-row">
                        <span class="label">📅 Fecha</span>
                        <span class="value">{fecha_actual}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">📌 Estado</span>
                        <span class="value {estado_class}">{estado}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">👤 Usuario</span>
                        <span class="value">{registro.get('usuario', 'N/A')}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">💰 Apertura</span>
                        <span class="value">${registro['apertura']:.2f}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">📈 Ingresos</span>
                        <span class="value ingreso">${registro.get('total_ingresos', 0):.2f}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">📉 Egresos</span>
                        <span class="value egreso">${registro.get('total_egresos', 0):.2f}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">💰 Saldo</span>
                        <span class="value">${saldo:.2f}</span>
                    </div>
                </div>
                """
                
                movimientos = registro.get("movimientos", [])
                if movimientos:
                    html += """
                    <div class="card">
                        <div class="subtitle">📋 Movimientos del día</div>
                    """
                    for mov in movimientos[-15:]:
                        clase = "movimiento-ingreso" if mov["tipo"] == "ingreso" else "movimiento-egreso"
                        signo = "+" if mov["tipo"] == "ingreso" else "-"
                        html += f"""
                        <div class="movimiento">
                            <span>{mov['hora']} - {mov['concepto']}</span>
                            <span class="{clase}">{signo}${mov['monto']:.2f}</span>
                        </div>
                        """
                    html += "</div>"
            else:
                html += """
                <div class="card">
                    <div class="no-data">📭 No hay caja abierta para hoy</div>
                </div>
                """
            
            html += """
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_historial(self):
            compras = self.sistema.compras + self.sistema.compras_mayoreo
            compras.sort(key=lambda x: x.get('fecha', ''), reverse=True)
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Historial - Móvil</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { font-family: Arial, sans-serif; background: #f5f5f5; padding: 15px; }
                    .header { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; align-items: center; }
                    .header a { color: white; text-decoration: none; font-size: 20px; margin-right: 15px; }
                    .header h1 { font-size: 18px; }
                    .card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                    .compra-info { display: flex; justify-content: space-between; align-items: center; }
                    .compra-material { font-weight: bold; font-size: 15px; }
                    .compra-cliente { color: #7f8c8d; font-size: 13px; }
                    .compra-detalle { display: flex; justify-content: space-between; margin-top: 5px; color: #7f8c8d; font-size: 13px; }
                    .compra-total { color: #27ae60; font-weight: bold; font-size: 16px; }
                    .compra-fecha { color: #95a5a6; font-size: 11px; }
                    .tipo-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; }
                    .tipo-cliente { background: #3498db; color: white; }
                    .tipo-inventario { background: #f39c12; color: white; }
                    .tipo-venta { background: #e74c3c; color: white; }
                    .total { background: #2c3e50; color: white; padding: 15px; border-radius: 10px; margin-top: 15px; text-align: center; }
                    .no-data { text-align: center; color: #7f8c8d; padding: 30px; }
                    .ganancia-tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 5px; }
                    .ganancia-especial { background: #e74c3c; color: white; }
                    .ganancia-normal { background: #27ae60; color: white; }
                </style>
            </head>
            <body>
                <div class="header">
                    <a href="/">⬅️</a>
                    <h1>📜 Historial</h1>
                </div>
            """
            
            if not compras:
                html += '<div class="no-data">📭 No hay registros en el historial</div>'
            else:
                total_general = 0
                for compra in compras[:50]:
                    total_general += compra.get("total", 0)
                    tipo = compra.get('tipo_precio', 'desconocido')
                    tipo_class = {
                        'cliente': 'tipo-cliente',
                        'compra_inventario': 'tipo-inventario',
                        'venta_inventario': 'tipo-venta'
                    }.get(tipo, 'tipo-cliente')
                    tipo_nombre = {
                        'cliente': 'Cliente',
                        'compra_inventario': 'Compra Inv',
                        'venta_inventario': 'Venta Inv'
                    }.get(tipo, 'Otro')
                    
                    material = compra.get('material', 'N/A')
                    porcentaje = self.sistema.obtener_porcentaje_ganancia(material)
                    es_especial = material.lower() in [m.lower() for m in PORCENTAJES_ESPECIALES]
                    ganancia_tag = f'<span class="ganancia-tag {"ganancia-especial" if es_especial else "ganancia-normal"}">{porcentaje*100:.1f}%</span>'
                    
                    html += f"""
                    <div class="card">
                        <div class="compra-info">
                            <div>
                                <div class="compra-material">{material} {ganancia_tag}</div>
                                <div class="compra-cliente">👤 {compra.get('cliente', 'N/A')}</div>
                            </div>
                            <div>
                                <span class="tipo-tag {tipo_class}">{tipo_nombre}</span>
                                <div class="compra-total">${compra.get('total', 0):.2f}</div>
                            </div>
                        </div>
                        <div class="compra-detalle">
                            <span>📦 {compra.get('cantidad', 0):.2f} kg</span>
                            <span class="compra-fecha">{compra.get('fecha', '')[:16]}</span>
                        </div>
                    </div>
                    """
                
                html += f"""
                <div class="total">
                    <p>💰 Total General: ${total_general:.2f}</p>
                    <p style="font-size:12px;opacity:0.8;">Últimas {min(50, len(compras))} transacciones</p>
                </div>
                """
            
            html += """
            </body>
            </html>
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def enviar_api_inventario(self):
            datos = self.sistema.inventario
            resultado = {
                "total_materiales": len(datos),
                "total_stock": 0,
                "total_valor": 0,
                "total_ganancia_potencial": 0,
                "materiales": []
            }
            
            for material, info in datos.items():
                stock = info.get("stock", 0)
                precio_venta = info.get("precio_venta", 0)
                costo_promedio = info.get("inversion_promedio", 0)
                valor = self.sistema.redondear(stock * precio_venta)
                ganancia = self.sistema.calcular_ganancia(material, precio_venta) * stock
                ganancia = self.sistema.redondear(ganancia)
                es_especial = material.lower() in [m.lower() for m in PORCENTAJES_ESPECIALES]
                porcentaje = self.sistema.obtener_porcentaje_ganancia(material)
                
                resultado["total_stock"] += stock
                resultado["total_valor"] += valor
                resultado["total_ganancia_potencial"] += ganancia
                resultado["materiales"].append({
                    "material": material,
                    "stock": stock,
                    "precio_venta": precio_venta,
                    "costo_promedio": costo_promedio,
                    "valor_total": valor,
                    "ganancia_potencial": ganancia,
                    "seccion": info.get("seccion", "inventario"),
                    "es_especial": es_especial,
                    "porcentaje_ganancia": porcentaje
                })
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, indent=2).encode('utf-8'))
        
        def enviar_api_ventas(self):
            ventas = self.sistema.ventas[-50:]
            resultado = {
                "total_ventas": len(ventas),
                "monto_total": sum(v.get("total", 0) for v in ventas),
                "ventas": ventas
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, indent=2, default=str).encode('utf-8'))
        
        def enviar_api_remisiones(self):
            remisiones = self.sistema.remisiones_generadas[-50:]
            resultado = {
                "total": len(remisiones),
                "remisiones": remisiones
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(resultado, indent=2, default=str).encode('utf-8'))
        
        def enviar_descargar_remision(self):
            try:
                if '=' in self.path:
                    remision_id = int(self.path.split('=')[1])
                else:
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0:
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        remision_id = data.get('remision_id')
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'ID de remision requerido')
                        return
                
                remision = None
                for r in self.sistema.remisiones_generadas:
                    if r.get('id') == remision_id:
                        remision = r
                        break
                
                if remision:
                    html_content = self.sistema.generar_html_nota(remision)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Content-Disposition', f'attachment; filename=remision_{remision_id}.html')
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Remision no encontrada')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
        
        def enviar_descargar_remision_venta(self):
            try:
                if '=' in self.path:
                    remision_id = int(self.path.split('=')[1])
                else:
                    content_length = int(self.headers.get('Content-Length', 0))
                    if content_length > 0:
                        post_data = self.rfile.read(content_length)
                        data = json.loads(post_data.decode('utf-8'))
                        remision_id = data.get('remision_id')
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b'ID de remision requerido')
                        return
                
                remision = None
                for r in self.sistema.remisiones_generadas:
                    if r.get('id') == remision_id and r.get('tipo') == 'venta':
                        remision = r
                        break
                
                if remision:
                    html_content = self.sistema.generar_html_nota(remision)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Content-Disposition', f'attachment; filename=remision_venta_{remision_id}.html')
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b'Remision de venta no encontrada')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))
    
    # ==================== REGISTRAR VENTA SIMULADA (POS VENTA) ====================
    
    def registrar_venta_simulada(self, empresa, material, cantidad):
        try:
            if not empresa or not material or not cantidad or cantidad <= 0:
                return {"success": False, "message": "Datos incompletos para la venta simulada"}
            
            precio_venta = 0
            material_encontrado = False
            
            if 'pos_venta' in self.materiales:
                for m in self.materiales['pos_venta']:
                    if m['nombre'] == material:
                        precio_venta = m.get('precio_venta', 0)
                        material_encontrado = True
                        break
            
            if not material_encontrado:
                return {"success": False, "message": f"Material '{material}' no encontrado en Pos Venta"}
            
            if precio_venta <= 0:
                return {"success": False, "message": "El material no tiene precio de venta configurado"}
            
            cantidad = float(cantidad)
            total = self.redondear(cantidad * precio_venta)
            
            stock_disponible = 0
            if material in self.inventario:
                stock_disponible = self.inventario[material].get("stock", 0)
            
            if cantidad > stock_disponible:
                return {
                    "success": False, 
                    "message": f"Stock insuficiente en inventario. Disponible: {stock_disponible:.2f} kg"
                }
            
            venta_id = max([v.get('id', 0) for v in self.ventas_simuladas]) + 1 if self.ventas_simuladas else 1
            
            venta_sim = {
                "id": venta_id,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "empresa": empresa,
                "material": material,
                "cantidad": cantidad,
                "precio_unitario": precio_venta,
                "total": total,
                "stock_actual": stock_disponible,
                "stock_restante": self.redondear(stock_disponible - cantidad)
            }
            
            self.ventas_simuladas.append(venta_sim)
            self.guardar_datos()
            
            self.actualizar_lista_ventas_simuladas()
            self.actualizar_metricas()
            
            mensaje = f"✅ Venta simulada registrada\n\n"
            mensaje += f"🏢 Empresa: {empresa}\n"
            mensaje += f"📦 Material: {material}\n"
            mensaje += f"📊 Cantidad: {cantidad:.2f} kg\n"
            mensaje += f"💰 Precio: ${precio_venta:.2f}/kg\n"
            mensaje += f"💰 Total: ${total:.2f}\n"
            mensaje += f"📊 Stock actual: {stock_disponible:.2f} kg\n"
            mensaje += f"📊 Stock restante: {venta_sim['stock_restante']:.2f} kg"
            
            return {
                "success": True,
                "message": mensaje,
                "venta_id": venta_id,
                "total": total
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error al registrar venta simulada: {str(e)}"}
    
    def eliminar_venta_simulada(self, venta_id):
        try:
            venta_eliminada = None
            for v in self.ventas_simuladas:
                if v.get('id') == venta_id:
                    venta_eliminada = v
                    break
            
            if not venta_eliminada:
                return {"success": False, "message": "Venta simulada no encontrada"}
            
            self.ventas_simuladas = [v for v in self.ventas_simuladas if v.get('id') != venta_id]
            self.guardar_datos()
            
            self.actualizar_lista_ventas_simuladas()
            self.actualizar_metricas()
            
            return {"success": True, "message": f"Venta simulada #{venta_id} eliminada"}
            
        except Exception as e:
            return {"success": False, "message": f"Error al eliminar venta simulada: {str(e)}"}
    
    def actualizar_lista_ventas_simuladas(self):
        if not hasattr(self, 'tree_ventas_simuladas'):
            return
        
        for item in self.tree_ventas_simuladas.get_children():
            self.tree_ventas_simuladas.delete(item)
        
        for venta in sorted(self.ventas_simuladas, key=lambda x: x.get('id', 0), reverse=True):
            self.tree_ventas_simuladas.insert("", "end", values=(
                venta.get('id', ''),
                venta.get('fecha', '')[:16],
                venta.get('empresa', ''),
                venta.get('material', ''),
                f"{venta.get('cantidad', 0):.2f}",
                f"{venta.get('precio_unitario', 0):.2f}",
                f"{venta.get('total', 0):.2f}",
                f"{venta.get('stock_actual', 0):.2f}",
                f"{venta.get('stock_restante', 0):.2f}"
            ))
    
    # ==================== ACTUALIZAR TABLAS DE MATERIALES ====================
    
    def actualizar_todas_tablas_materiales(self):
        for tipo, tree in self.trees_materiales.items():
            if tree and tree.winfo_exists():
                self.actualizar_tabla_materiales(tree, tipo)
    
    def actualizar_tabla_materiales(self, tree, tipo):
        for item in tree.get_children():
            tree.delete(item)
        
        if tipo in self.materiales:
            for m in self.materiales[tipo]:
                nombre = m['nombre']
                precio_venta = self.redondear(m['precio_venta'])
                precio_cliente = self.calcular_precio_cliente(nombre, precio_venta)
                ganancia = self.calcular_ganancia(nombre, precio_venta)
                porcentaje = self.obtener_porcentaje_ganancia(nombre) * 100
                empresa = m.get('empresa', 'Sin asignar')
                tree.insert("", "end", values=(
                    nombre, 
                    f"{precio_venta:.2f}", 
                    f"{precio_cliente:.2f}",
                    f"{ganancia:.2f} ({porcentaje:.1f}%)",
                    empresa
                ))
    
    # ==================== REGISTRAR VENTA DESDE MÓVIL ====================
    
    def registrar_venta_desde_movil(self, cliente, material, cantidad, precio):
        try:
            cliente_existente = False
            for c in self.clientes:
                if c['nombre'] == cliente:
                    cliente_existente = True
                    break
            
            if not cliente_existente:
                self.clientes.append({"id": len(self.clientes) + 1, "nombre": cliente, "telefono": ""})
            
            if material not in self.inventario:
                return {"success": False, "message": f"Material '{material}' no encontrado en inventario"}
            
            datos = self.inventario[material]
            stock_disponible = datos.get("stock", 0)
            
            if cantidad > stock_disponible:
                return {
                    "success": False, 
                    "message": f"Stock insuficiente. Disponible: {stock_disponible:.2f} kg"
                }
            
            precio_venta = datos.get("precio_venta", 0)
            if precio_venta <= 0:
                return {"success": False, "message": "El material no tiene precio de venta configurado"}
            
            precio_cliente = self.calcular_precio_cliente(material, precio_venta)
            ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
            ganancia_total = self.redondear(cantidad * ganancia_por_kg)
            total_venta = self.redondear(cantidad * precio_cliente)
            
            caja = self.redondear(total_venta)
            salarios = self.redondear(total_venta * 0.10)
            
            stock_anterior = stock_disponible
            nuevo_stock = self.redondear(stock_anterior - cantidad)
            datos["stock"] = nuevo_stock
            
            if nuevo_stock == 0:
                datos["inversion_total"] = 0
                datos["inversion_promedio"] = 0
                datos["total_comprado"] = 0
            
            self.caja_general = self.redondear(self.caja_general + caja)
            self.fondo_salarios = self.redondear(self.fondo_salarios + salarios)
            
            concepto = f"Venta móvil - {material} ({cliente})"
            if ganancia_total > 0:
                concepto += f" (ganancia: ${ganancia_total:.2f})"
            self.registrar_movimiento_caja("ingreso", concepto, caja)
            
            venta_id = max([v.get('id', 0) for v in self.ventas]) + 1 if self.ventas else 1
            venta = {
                "id": venta_id,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cliente": cliente,
                "material": material,
                "cantidad": cantidad,
                "precio_unitario": precio_venta,
                "precio_cliente": precio_cliente,
                "ganancia": ganancia_total,
                "porcentaje_ganancia": self.obtener_porcentaje_ganancia(material) * 100,
                "total": total_venta,
                "caja_asignada": caja,
                "salarios_asignados": salarios,
                "seccion": datos.get("seccion", "inventario"),
                "stock_anterior": stock_anterior,
                "stock_actual": nuevo_stock,
                "origen": "movil"
            }
            self.ventas.append(venta)
            
            remision_existente = None
            for r in self.remisiones_generadas:
                if r.get('cliente') == cliente and r.get('tipo') == 'venta' and r.get('fecha', '')[:10] == datetime.now().strftime("%Y-%m-%d"):
                    remision_existente = r
                    break
            
            if remision_existente:
                remision_existente['items'].append({
                    "material": material,
                    "cantidad": cantidad,
                    "precio": precio_cliente,
                    "precio_original": precio_venta,
                    "ganancia": ganancia_total,
                    "porcentaje_ganancia": self.obtener_porcentaje_ganancia(material) * 100,
                    "total": total_venta,
                    "seccion": datos.get("seccion", "inventario")
                })
                remision_existente['total'] = self.redondear(remision_existente['total'] + total_venta)
                remision_existente['ganancia_total'] = self.redondear(remision_existente.get('ganancia_total', 0) + ganancia_total)
                remision_existente['qr_base64'] = self.generar_qr_remision(remision_existente)
                remision_id = remision_existente['id']
            else:
                remision_id = max([r.get('id', 0) for r in self.remisiones_generadas]) + 1 if self.remisiones_generadas else 1
                remision = {
                    "id": remision_id,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cliente": cliente,
                    "usuario": "movil",
                    "items": [{
                        "material": material,
                        "cantidad": cantidad,
                        "precio": precio_cliente,
                        "precio_original": precio_venta,
                        "ganancia": ganancia_total,
                        "porcentaje_ganancia": self.obtener_porcentaje_ganancia(material) * 100,
                        "total": total_venta,
                        "seccion": datos.get("seccion", "inventario")
                    }],
                    "total": total_venta,
                    "ganancia_total": ganancia_total,
                    "tipo": "venta",
                    "venta_id": venta_id
                }
                qr_base64 = self.generar_qr_remision(remision)
                remision["qr_base64"] = qr_base64
                self.remisiones_generadas.append(remision)
            
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_lista_venta()
            self.actualizar_lista_ventas()
            self.actualizar_metricas()
            self.actualizar_info_caja()
            self.actualizar_movimientos_caja()
            self.actualizar_lista_remisiones()
            
            self.enviar_correo_remision_completa(cliente, remision_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                                                self.remisiones_generadas[-1]['items'] if remision_existente else remision['items'], 
                                                self.remisiones_generadas[-1]['total'] if remision_existente else total_venta, 
                                                es_venta=True)
            
            mensaje = f"Venta registrada exitosamente\nTotal: ${total_venta:.2f}"
            if ganancia_total > 0:
                mensaje += f"\nGanancia ({self.obtener_porcentaje_ganancia(material)*100:.1f}%): ${ganancia_total:.2f}"
            
            return {
                "success": True,
                "message": mensaje,
                "remision_id": remision_id,
                "total": total_venta,
                "ganancia": ganancia_total
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error al registrar venta: {str(e)}"}
    
    # ==================== GENERAR HTML DE REMISIÓN ====================
    
    def generar_html_nota(self, remision):
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
        
        for item in remision['items']:
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
            
            <div class="qr">
                <img src="data:image/png;base64,{remision.get('qr_base64', '')}" alt="QR" width="150">
                <p style="font-size:12px;color:#7f8c8d;">Código QR - {titulo}</p>
            </div>
            
            <div class="footer">
                <p>Este documento es una {titulo.lower()}.</p>
                <p>Generado el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def generar_qr_remision(self, remision):
        qr_data = {
            "remision_id": remision['id'],
            "cliente": remision['cliente'],
            "fecha": remision['fecha'],
            "total": remision['total'],
            "tipo": remision.get('tipo', 'remision')
        }
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return img_base64
    
    def descargar_remision(self, remision_id, es_venta=False):
        try:
            remision = None
            for r in self.remisiones_generadas:
                if r.get('id') == remision_id:
                    if es_venta and r.get('tipo') != 'venta':
                        continue
                    remision = r
                    break
            
            if not remision:
                messagebox.showerror("Error", "Remisión no encontrada")
                return
            
            html_content = self.generar_html_nota(remision)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w', encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            webbrowser.open(temp_file.name)
            
            messagebox.showinfo("Éxito", f"✅ Remisión #{remision_id} descargada correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al descargar remisión: {str(e)}")
    
    # ==================== ENVIAR CORREO ====================
    
    def enviar_correo_remision_completa(self, cliente_nombre, remision_id, fecha, materiales, total, es_venta=False):
        try:
            tipo = "VENTA" if es_venta else "REMISIÓN"
            
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    table {{ width: 100%; border-collapse: collapse; }}
                    th {{ background: #34495e; color: white; padding: 10px; text-align: left; }}
                    td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                    .total {{ font-size: 18px; font-weight: bold; color: #27ae60; }}
                    .footer {{ text-align: center; color: #7f8c8d; font-size: 12px; margin-top: 20px; }}
                    .tipo-tag {{ display: inline-block; padding: 3px 12px; border-radius: 15px; font-size: 14px; font-weight: bold; }}
                    .tipo-remision {{ background: #3498db; color: white; }}
                    .tipo-venta {{ background: #27ae60; color: white; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>♻️ Reciclaje Industrial</h1>
                    <p>Sistemas Computerionales de México</p>
                </div>
                <div class="content">
                    <h2>📋 {tipo} #{remision_id}</h2>
                    <span class="tipo-tag tipo-{'venta' if es_venta else 'remision'}">{tipo}</span>
                    <p><strong>Cliente:</strong> {cliente_nombre}</p>
                    <p><strong>Fecha:</strong> {fecha}</p>
                    
                    <h3>Detalle de Materiales</h3>
                    <table>
                        <tr>
                            <th>Material</th>
                            <th>Cantidad (kg)</th>
                            <th>Precio ($/kg)</th>
                            <th>Total ($)</th>
                        </tr>
            """
            
            for item in materiales:
                html_content += f"""
                        <tr>
                            <td>{item['material']}</td>
                            <td>{item['cantidad']:.2f}</td>
                            <td>${item['precio']:.2f}</td>
                            <td>${item['total']:.2f}</td>
                        </tr>
                """
            
            html_content += f"""
                    </table>
                    <p class="total">TOTAL: ${total:.2f}</p>
                    <p style="margin-top: 10px; color: #7f8c8d;">
                        📎 Se adjunta la {tipo.lower()} en formato HTML.
                    </p>
                </div>
                <div class="footer">
                    <p>Este correo es una confirmación de la {tipo.lower()}.</p>
                    <p>Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </body>
            </html>
            """
            
            msg = MIMEMultipart()
            msg['From'] = self.correo_remitente
            msg['To'] = self.correo_destinatario
            msg['Subject'] = f"{tipo} #{remision_id} - {cliente_nombre}"
            
            msg.attach(MIMEText(html_content, 'html'))
            
            remision_data = {
                "id": remision_id,
                "fecha": fecha,
                "cliente": cliente_nombre,
                "usuario": self.usuario_actual,
                "items": materiales,
                "total": total,
                "tipo": "venta" if es_venta else "remision",
                "qr_base64": self.generar_qr_remision({
                    "id": remision_id,
                    "cliente": cliente_nombre,
                    "fecha": fecha,
                    "total": total,
                    "tipo": "venta" if es_venta else "remision"
                })
            }
            
            html_adjunto = self.generar_html_nota(remision_data)
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(html_adjunto.encode('utf-8'))
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={tipo.lower()}_{remision_id}.html')
            msg.attach(part)
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.correo_remitente, self.correo_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Correo enviado para {tipo} #{remision_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error al enviar correo: {e}")
            return False
    
    # ==================== INTERFAZ PRINCIPAL ====================
    
    def crear_interfaz(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True)
        
        self.tab_inventario = ttk.Frame(notebook)
        notebook.add(self.tab_inventario, text="📊 INVENTARIO")
        self.crear_tab_inventario()
        
        self.tab_caja = ttk.Frame(notebook)
        notebook.add(self.tab_caja, text="💰 CAJA DIARIA")
        self.crear_tab_caja()
        
        self.tab_clientes = ttk.Frame(notebook)
        notebook.add(self.tab_clientes, text="1. Clientes")
        self.crear_tab_clientes()
        
        self.tab_ferrosos = ttk.Frame(notebook)
        notebook.add(self.tab_ferrosos, text="2. Ferrosos")
        self.crear_tab_materiales(self.tab_ferrosos, "ferrosos")
        
        self.tab_plasticos = ttk.Frame(notebook)
        notebook.add(self.tab_plasticos, text="3. Plásticos")
        self.crear_tab_materiales(self.tab_plasticos, "plasticos")
        
        self.tab_electronicos = ttk.Frame(notebook)
        notebook.add(self.tab_electronicos, text="4. Electrónicos")
        self.crear_tab_materiales(self.tab_electronicos, "electronicos")
        
        self.tab_papel = ttk.Frame(notebook)
        notebook.add(self.tab_papel, text="5. Papel")
        self.crear_tab_materiales(self.tab_papel, "papel")
        
        self.tab_por_pieza = ttk.Frame(notebook)
        notebook.add(self.tab_por_pieza, text="6. Por Pieza")
        self.crear_tab_materiales(self.tab_por_pieza, "por_pieza")
        
        self.tab_pos_venta = ttk.Frame(notebook)
        notebook.add(self.tab_pos_venta, text="7. Pos Venta")
        self.crear_tab_pos_venta()
        
        self.tab_venta_inventario = ttk.Frame(notebook)
        notebook.add(self.tab_venta_inventario, text="🛒 VENTA")
        self.crear_tab_venta_inventario()
        
        self.tab_remision = ttk.Frame(notebook)
        notebook.add(self.tab_remision, text="📋 REMISIÓN")
        self.crear_tab_remision()
        
        self.tab_historial = ttk.Frame(notebook)
        notebook.add(self.tab_historial, text="📜 HISTORIAL")
        self.crear_tab_historial()
        
        self.tab_gastos = ttk.Frame(notebook)
        notebook.add(self.tab_gastos, text="💰 GASTOS")
        self.crear_tab_gastos()
        
        self.tab_metricas = ttk.Frame(notebook)
        notebook.add(self.tab_metricas, text="📈 MÉTRICAS")
        self.crear_tab_metricas()
        
        self.tab_remisiones = ttk.Frame(notebook)
        notebook.add(self.tab_remisiones, text="📋 REMISIONES")
        self.crear_tab_remisiones_guardadas()
        
        self.tab_frecuencia = ttk.Frame(notebook)
        notebook.add(self.tab_frecuencia, text="📊 FRECUENCIA CLIENTES")
        self.crear_tab_frecuencia_clientes()
    
    # ==================== TAB CLIENTES ====================
    
    def crear_tab_clientes(self):
        frame_form = ttk.LabelFrame(self.tab_clientes, text="Registrar Cliente")
        frame_form.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_form, text="Nombre:").grid(row=0, column=0, padx=4, pady=4)
        self.entry_nombre = ttk.Entry(frame_form, width=25)
        self.entry_nombre.grid(row=0, column=1, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Teléfono:").grid(row=0, column=2, padx=4, pady=4)
        self.entry_telefono = ttk.Entry(frame_form, width=18)
        self.entry_telefono.grid(row=0, column=3, padx=4, pady=4)
        
        ttk.Button(frame_form, text="Agregar Cliente", command=self.agregar_cliente).grid(row=0, column=4, padx=8, pady=4)
        
        frame_lista = ttk.LabelFrame(self.tab_clientes, text="Clientes Registrados")
        frame_lista.pack(pady=8, padx=8, fill='both', expand=True)
        
        frame_botones_clientes = ttk.Frame(frame_lista)
        frame_botones_clientes.pack(fill='x', pady=5)
        
        self.seleccionar_todos_clientes = tk.BooleanVar(value=False)
        chk_todos = ttk.Checkbutton(frame_botones_clientes, text="☑️ Seleccionar Todos", 
                                    variable=self.seleccionar_todos_clientes,
                                    command=self.toggle_seleccion_todos_clientes)
        chk_todos.pack(side='left', padx=5)
        
        ttk.Button(frame_botones_clientes, text="✏️ Editar Cliente", command=self.editar_cliente).pack(side='left', padx=5)
        ttk.Button(frame_botones_clientes, text="🗑️ Eliminar Seleccionados", 
                  command=self.eliminar_clientes_seleccionados).pack(side='left', padx=5)
        ttk.Button(frame_botones_clientes, text="🔄 Actualizar Lista", command=self.actualizar_lista_clientes).pack(side='left', padx=5)
        
        self.tree_clientes = ttk.Treeview(frame_lista, columns=("ID", "Nombre", "Teléfono"), show='headings', height=12)
        self.tree_clientes.heading("ID", text="ID")
        self.tree_clientes.heading("Nombre", text="Nombre")
        self.tree_clientes.heading("Teléfono", text="Teléfono")
        self.tree_clientes.pack(fill='both', expand=True)
        
        self.tree_clientes.bind('<<TreeviewSelect>>', self.on_cliente_seleccionado)
        
        self.actualizar_lista_clientes()
    
    def on_cliente_seleccionado(self, event):
        pass
    
    def toggle_seleccion_todos_clientes(self):
        seleccionar = self.seleccionar_todos_clientes.get()
        for item in self.tree_clientes.get_children():
            if seleccionar:
                self.tree_clientes.selection_add(item)
            else:
                self.tree_clientes.selection_remove(item)
    
    def eliminar_clientes_seleccionados(self):
        seleccion = self.tree_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos un cliente para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(seleccion)} cliente(s) seleccionado(s)?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        clientes_a_eliminar = []
        for item in seleccion:
            valores = self.tree_clientes.item(item)['values']
            cliente_id = int(valores[0])
            cliente_nombre = valores[1]
            clientes_a_eliminar.append((cliente_id, cliente_nombre))
        
        ids_a_eliminar = [id for id, _ in clientes_a_eliminar]
        self.clientes = [c for c in self.clientes if c['id'] not in ids_a_eliminar]
        
        for _, nombre in clientes_a_eliminar:
            if nombre in self.frecuencia_clientes:
                del self.frecuencia_clientes[nombre]
            if nombre in self.visitas_clientes:
                del self.visitas_clientes[nombre]
        
        self.guardar_datos()
        self.actualizar_lista_clientes()
        self.actualizar_combo_clientes()
        self.actualizar_frecuencia_clientes()
        self.seleccionar_todos_clientes.set(False)
        
        messagebox.showinfo("Éxito", f"✅ {len(clientes_a_eliminar)} cliente(s) eliminado(s) correctamente")
    
    def agregar_cliente(self):
        nombre = self.entry_nombre.get().strip()
        telefono = self.entry_telefono.get().strip()
        if nombre:
            cliente_id = len(self.clientes) + 1
            self.clientes.append({"id": cliente_id, "nombre": nombre, "telefono": telefono})
            self.guardar_datos()
            self.actualizar_lista_clientes()
            self.entry_nombre.delete(0, tk.END)
            self.entry_telefono.delete(0, tk.END)
            messagebox.showinfo("Éxito", "Cliente agregado")
        else:
            messagebox.showwarning("Error", "El nombre es obligatorio")
    
    def editar_cliente(self):
        seleccion = self.tree_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un cliente para editar")
            return
        
        item = seleccion[0]
        item_data = self.tree_clientes.item(item)
        valores = item_data['values']
        cliente_id = int(valores[0])
        nombre_actual = valores[1]
        telefono_actual = valores[2] if len(valores) > 2 else ""
        
        nuevo_nombre = simpledialog.askstring("Editar Cliente", "Nuevo nombre:", initialvalue=nombre_actual)
        if nuevo_nombre is None:
            return
        nuevo_nombre = nuevo_nombre.strip()
        if not nuevo_nombre:
            messagebox.showwarning("Error", "El nombre no puede estar vacío")
            return
        
        nuevo_telefono = simpledialog.askstring("Editar Cliente", "Nuevo teléfono:", initialvalue=telefono_actual)
        if nuevo_telefono is None:
            return
        
        for cliente in self.clientes:
            if cliente['id'] == cliente_id:
                cliente['nombre'] = nuevo_nombre
                cliente['telefono'] = nuevo_telefono or ""
                break
        
        self.guardar_datos()
        self.actualizar_lista_clientes()
        self.actualizar_combo_clientes()
        self.actualizar_frecuencia_clientes()
        messagebox.showinfo("Éxito", f"Cliente '{nuevo_nombre}' actualizado correctamente")
    
    def eliminar_cliente(self):
        seleccion = self.tree_clientes.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un cliente para eliminar")
            return
        
        item = seleccion[0]
        item_data = self.tree_clientes.item(item)
        valores = item_data['values']
        cliente_id = int(valores[0])
        nombre = valores[1]
        
        tiene_ventas = any(v.get('cliente') == nombre for v in self.ventas)
        tiene_remisiones = any(r.get('cliente') == nombre for r in self.remisiones_generadas)
        
        mensaje = f"⚠️ ¿Eliminar al cliente '{nombre}'?\n\n"
        if tiene_ventas:
            mensaje += f"⚠️ Este cliente tiene {len([v for v in self.ventas if v.get('cliente') == nombre])} ventas registradas.\n"
        if tiene_remisiones:
            mensaje += f"⚠️ Este cliente tiene {len([r for r in self.remisiones_generadas if r.get('cliente') == nombre])} remisiones registradas.\n"
        mensaje += "\nLos datos históricos no se eliminarán, solo el cliente de la lista.\n"
        mensaje += "¿Desea continuar?"
        
        if not messagebox.askyesno("Confirmar Eliminación", mensaje):
            return
        
        self.clientes = [c for c in self.clientes if c['id'] != cliente_id]
        
        if nombre in self.frecuencia_clientes:
            del self.frecuencia_clientes[nombre]
        if nombre in self.visitas_clientes:
            del self.visitas_clientes[nombre]
        
        self.guardar_datos()
        self.actualizar_lista_clientes()
        self.actualizar_combo_clientes()
        self.actualizar_frecuencia_clientes()
        messagebox.showinfo("Éxito", f"Cliente '{nombre}' eliminado correctamente")
    
    def actualizar_combo_clientes(self):
        nombres = [c['nombre'] for c in self.clientes]
        
        if hasattr(self, 'venta_cliente_combo'):
            self.venta_cliente_combo['values'] = nombres
        
        if hasattr(self, 'remision_cliente_combo'):
            self.remision_cliente_combo['values'] = nombres
        
        if hasattr(self, 'frecuencia_cliente_combo'):
            self.frecuencia_cliente_combo['values'] = nombres
    
    def actualizar_lista_clientes(self):
        for item in self.tree_clientes.get_children():
            self.tree_clientes.delete(item)
        for c in self.clientes:
            self.tree_clientes.insert("", "end", values=(c['id'], c['nombre'], c['telefono']))
        self.actualizar_combo_clientes()
        self.seleccionar_todos_clientes.set(False)
    
    # ==================== TAB FRECUENCIA DE CLIENTES ====================
    
    def crear_tab_frecuencia_clientes(self):
        frame_filtro = ttk.LabelFrame(self.tab_frecuencia, text="🔍 Filtrar por Cliente")
        frame_filtro.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_filtro, text="Cliente:").pack(side='left', padx=5)
        self.frecuencia_cliente_combo = ttk.Combobox(frame_filtro, width=25)
        self.frecuencia_cliente_combo.pack(side='left', padx=5)
        self.frecuencia_cliente_combo.bind('<<ComboboxSelected>>', self.filtrar_frecuencia_cliente)
        
        ttk.Button(frame_filtro, text="Mostrar Todos", command=self.actualizar_frecuencia_clientes).pack(side='left', padx=5)
        ttk.Button(frame_filtro, text="🔄 Actualizar", command=self.actualizar_frecuencia_clientes).pack(side='left', padx=5)
        
        frame_resumen = ttk.LabelFrame(self.tab_frecuencia, text="📊 Resumen de Frecuencia")
        frame_resumen.pack(pady=8, padx=8, fill='x')
        
        self.label_total_clientes = ttk.Label(frame_resumen, text="👥 Total de Clientes: 0", font=("Arial", 11))
        self.label_total_clientes.pack(side='left', padx=15, pady=5)
        
        self.label_total_visitas = ttk.Label(frame_resumen, text="📋 Total de Visitas: 0", font=("Arial", 11))
        self.label_total_visitas.pack(side='left', padx=15, pady=5)
        
        self.label_cliente_mas_frecuente = ttk.Label(frame_resumen, text="🏆 Cliente más frecuente: Ninguno", font=("Arial", 11))
        self.label_cliente_mas_frecuente.pack(side='left', padx=15, pady=5)
        
        frame_tabla = ttk.LabelFrame(self.tab_frecuencia, text="📋 Frecuencia de Visitas por Cliente")
        frame_tabla.pack(pady=8, padx=8, fill='both', expand=True)
        
        self.tree_frecuencia = ttk.Treeview(frame_tabla, 
            columns=("Cliente", "Total Visitas", "Última Visita", "Materiales", "Total kg"), 
            show='headings', height=15)
        self.tree_frecuencia.heading("Cliente", text="Cliente")
        self.tree_frecuencia.heading("Total Visitas", text="Total Visitas")
        self.tree_frecuencia.heading("Última Visita", text="Última Visita")
        self.tree_frecuencia.heading("Materiales", text="Materiales Traídos")
        self.tree_frecuencia.heading("Total kg", text="Total kg")
        
        self.tree_frecuencia.column("Cliente", width=200)
        self.tree_frecuencia.column("Total Visitas", width=100, anchor='center')
        self.tree_frecuencia.column("Última Visita", width=150, anchor='center')
        self.tree_frecuencia.column("Materiales", width=200)
        self.tree_frecuencia.column("Total kg", width=100, anchor='center')
        self.tree_frecuencia.pack(fill='both', expand=True, padx=5, pady=5)
        
        frame_detalle = ttk.LabelFrame(self.tab_frecuencia, text="📝 Historial de Visitas del Cliente Seleccionado")
        frame_detalle.pack(pady=8, padx=8, fill='x')
        
        self.tree_visitas_cliente = ttk.Treeview(frame_detalle, 
            columns=("Fecha", "Material", "Cantidad", "Total"), 
            show='headings', height=5)
        self.tree_visitas_cliente.heading("Fecha", text="Fecha")
        self.tree_visitas_cliente.heading("Material", text="Material")
        self.tree_visitas_cliente.heading("Cantidad", text="Cantidad (kg)")
        self.tree_visitas_cliente.heading("Total", text="Total ($)")
        
        self.tree_visitas_cliente.column("Fecha", width=150)
        self.tree_visitas_cliente.column("Material", width=150)
        self.tree_visitas_cliente.column("Cantidad", width=100, anchor='center')
        self.tree_visitas_cliente.column("Total", width=100, anchor='center')
        self.tree_visitas_cliente.pack(fill='x', padx=5, pady=5)
        
        self.actualizar_combo_clientes()
        self.actualizar_frecuencia_clientes()
    
    def actualizar_frecuencia_clientes(self):
        self.frecuencia_clientes = {}
        
        for venta in self.ventas:
            cliente = venta.get('cliente')
            if not cliente:
                continue
            
            if cliente not in self.frecuencia_clientes:
                self.frecuencia_clientes[cliente] = {
                    "total_visitas": 0,
                    "ultima_visita": "",
                    "materiales": {},
                    "total_kg": 0
                }
            
            self.frecuencia_clientes[cliente]["total_visitas"] += 1
            
            fecha = venta.get('fecha', '')
            if fecha and (not self.frecuencia_clientes[cliente]["ultima_visita"] or fecha > self.frecuencia_clientes[cliente]["ultima_visita"]):
                self.frecuencia_clientes[cliente]["ultima_visita"] = fecha[:16]
            
            material = venta.get('material', '')
            cantidad = venta.get('cantidad', 0)
            
            if material:
                self.frecuencia_clientes[cliente]["materiales"][material] = self.frecuencia_clientes[cliente]["materiales"].get(material, 0) + cantidad
            
            self.frecuencia_clientes[cliente]["total_kg"] += cantidad
        
        clientes_ordenados = sorted(
            self.frecuencia_clientes.items(),
            key=lambda x: x[1]["total_visitas"],
            reverse=True
        )
        
        for item in self.tree_frecuencia.get_children():
            self.tree_frecuencia.delete(item)
        
        total_visitas = 0
        total_clientes = len(self.frecuencia_clientes)
        cliente_mas_frecuente = "Ninguno"
        max_visitas = 0
        
        for cliente, datos in clientes_ordenados:
            visitas = datos.get("total_visitas", 0)
            total_visitas += visitas
            
            if visitas > max_visitas:
                max_visitas = visitas
                cliente_mas_frecuente = cliente
            
            materiales_str = ", ".join([f"{m}({c:.2f}kg)" for m, c in datos.get("materiales", {}).items()])
            if len(materiales_str) > 50:
                materiales_str = materiales_str[:47] + "..."
            
            self.tree_frecuencia.insert("", "end", values=(
                cliente,
                visitas,
                datos.get("ultima_visita", "Sin visitas"),
                materiales_str or "Ninguno",
                f"{datos.get('total_kg', 0):.2f}"
            ))
        
        self.label_total_clientes.config(text=f"👥 Total de Clientes: {total_clientes}")
        self.label_total_visitas.config(text=f"📋 Total de Visitas: {total_visitas}")
        self.label_cliente_mas_frecuente.config(
            text=f"🏆 Cliente más frecuente: {cliente_mas_frecuente} ({max_visitas} visitas)" if cliente_mas_frecuente != "Ninguno" else "🏆 Cliente más frecuente: Ninguno"
        )
    
    def filtrar_frecuencia_cliente(self, event=None):
        cliente = self.frecuencia_cliente_combo.get()
        
        if not cliente:
            self.actualizar_frecuencia_clientes()
            return
        
        for item in self.tree_frecuencia.get_children():
            valores = self.tree_frecuencia.item(item)['values']
            if valores and valores[0] == cliente:
                self.tree_frecuencia.item(item, tags=('visible',))
            else:
                self.tree_frecuencia.item(item, tags=('oculto',))
        
        for item in self.tree_frecuencia.get_children():
            tags = self.tree_frecuencia.item(item)['tags']
            if 'oculto' in tags:
                self.tree_frecuencia.detach(item)
            else:
                self.tree_frecuencia.reattach(item, '', 'end')
        
        self.mostrar_historial_cliente(cliente)
    
    def mostrar_historial_cliente(self, cliente):
        for item in self.tree_visitas_cliente.get_children():
            self.tree_visitas_cliente.delete(item)
        
        ventas_cliente = [v for v in self.ventas if v.get('cliente') == cliente]
        ventas_cliente.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        for venta in ventas_cliente[:20]:
            self.tree_visitas_cliente.insert("", "end", values=(
                venta.get('fecha', '')[:16],
                venta.get('material', ''),
                f"{venta.get('cantidad', 0):.2f}",
                f"{venta.get('total', 0):.2f}"
            ))
        
        self.tree_visitas_cliente.master.config(text=f"📝 Historial de Visitas - {cliente}")
    
    # ==================== TAB MATERIALES CON EMPRESA ====================
    
    def crear_tab_materiales(self, parent, tipo):
        frame_form = ttk.LabelFrame(parent, text=f"Gestionar {tipo.upper()}")
        frame_form.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_form, text="Material:").grid(row=0, column=0, padx=4, pady=4)
        entry_material = ttk.Entry(frame_form, width=18)
        entry_material.grid(row=0, column=1, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Precio Venta ($):").grid(row=0, column=2, padx=4, pady=4)
        entry_precio_venta = ttk.Entry(frame_form, width=12)
        entry_precio_venta.grid(row=0, column=3, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Empresa:").grid(row=0, column=4, padx=4, pady=4)
        entry_empresa = ttk.Combobox(frame_form, values=EMPRESAS_DISPONIBLES, width=20)
        entry_empresa.grid(row=0, column=5, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Precio Cliente:").grid(row=1, column=0, padx=4, pady=4)
        label_precio_cliente = ttk.Label(frame_form, text="$0.00", font=("Arial", 10, "bold"), foreground="blue")
        label_precio_cliente.grid(row=1, column=1, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Ganancia:").grid(row=1, column=2, padx=4, pady=4)
        label_ganancia = ttk.Label(frame_form, text="0%", font=("Arial", 9), foreground="red")
        label_ganancia.grid(row=1, column=3, padx=4, pady=4)
        
        def actualizar_precio_cliente(*args):
            try:
                nombre = entry_material.get().strip()
                precio = float(entry_precio_venta.get())
                precio_cliente = self.calcular_precio_cliente(nombre, precio)
                ganancia = self.calcular_ganancia(nombre, precio)
                porcentaje = self.obtener_porcentaje_ganancia(nombre) * 100
                label_precio_cliente.config(text=f"${precio_cliente:.2f}")
                label_ganancia.config(text=f"${ganancia:.2f} ({porcentaje:.1f}%)", 
                                    foreground="red" if porcentaje == 5 else "green")
            except:
                label_precio_cliente.config(text="$0.00")
                label_ganancia.config(text="0%")
        
        entry_precio_venta.bind('<KeyRelease>', actualizar_precio_cliente)
        entry_material.bind('<KeyRelease>', actualizar_precio_cliente)
        
        def agregar():
            nombre = entry_material.get().strip()
            try:
                precio_venta = float(entry_precio_venta.get())
                precio_venta = self.redondear(precio_venta)
                empresa = entry_empresa.get().strip() or "Sin asignar"
                
                self.materiales[tipo].append({
                    "nombre": nombre,
                    "precio_venta": precio_venta,
                    "empresa": empresa
                })
                self.ordenar_materiales_alfabeticamente()
                self.guardar_datos()
                self.sincronizar_precios_inventario(nombre, precio_venta, tipo, empresa)
                self.actualizar_tabla_materiales(tree, tipo)
                entry_material.delete(0, tk.END)
                entry_precio_venta.delete(0, tk.END)
                entry_empresa.set("")
                label_precio_cliente.config(text="$0.00")
                label_ganancia.config(text="0%")
                messagebox.showinfo("Éxito", "Material agregado y sincronizado con inventario")
            except:
                messagebox.showwarning("Error", "Precio válido requerido")
        
        def editar():
            seleccion = tree.selection()
            if seleccion:
                item = tree.item(seleccion)
                valores = item['values']
                nuevo_nombre = simpledialog.askstring("Editar", "Nuevo nombre:", initialvalue=valores[0])
                nuevo_precio = simpledialog.askfloat("Editar", "Nuevo precio venta:", initialvalue=float(valores[1]) if valores[1] else 0)
                nueva_empresa = simpledialog.askstring("Editar", "Nueva empresa:", initialvalue=valores[4] if len(valores) > 4 else "Sin asignar")
                if nuevo_nombre and nuevo_precio:
                    nuevo_precio = self.redondear(nuevo_precio)
                    for m in self.materiales[tipo]:
                        if m['nombre'] == valores[0]:
                            m['nombre'] = nuevo_nombre
                            m['precio_venta'] = nuevo_precio
                            m['empresa'] = nueva_empresa or "Sin asignar"
                            break
                    self.ordenar_materiales_alfabeticamente()
                    self.guardar_datos()
                    self.sincronizar_precios_inventario(nuevo_nombre, nuevo_precio, tipo, nueva_empresa)
                    self.actualizar_tabla_materiales(tree, tipo)
                    self.actualizar_tabla_inventario()
                    messagebox.showinfo("Éxito", "Material actualizado y sincronizado con inventario")
        
        def eliminar():
            seleccion = tree.selection()
            if seleccion:
                item = tree.item(seleccion)
                valores = item['values']
                if messagebox.askyesno("Confirmar", f"¿Eliminar {valores[0]}?"):
                    self.materiales[tipo] = [m for m in self.materiales[tipo] if m['nombre'] != valores[0]]
                    self.ordenar_materiales_alfabeticamente()
                    self.guardar_datos()
                    self.actualizar_tabla_materiales(tree, tipo)
        
        def actualizar_tabla():
            self.actualizar_tabla_materiales(tree, tipo)
        
        ttk.Button(frame_form, text="Agregar", command=agregar).grid(row=2, column=0, padx=4, pady=4)
        ttk.Button(frame_form, text="Editar", command=editar).grid(row=2, column=1, padx=4, pady=4)
        ttk.Button(frame_form, text="Eliminar", command=eliminar).grid(row=2, column=2, padx=4, pady=4)
        ttk.Button(frame_form, text="🔄 Sincronizar Precios", 
                  command=lambda: self.sincronizar_todos_precios(tipo)).grid(row=2, column=3, padx=4, pady=4)
        ttk.Button(frame_form, text="📊 Actualizar Lista", 
                  command=actualizar_tabla).grid(row=2, column=4, padx=4, pady=4)
        
        frame_tabla = ttk.LabelFrame(parent, text="Lista de Materiales")
        frame_tabla.pack(pady=8, padx=8, fill='both', expand=True)
        
        tree = ttk.Treeview(frame_tabla, columns=("Material", "Venta", "Cliente", "Ganancia", "Empresa"), show='headings', height=10)
        tree.heading("Material", text="Material")
        tree.heading("Venta", text="Venta ($)")
        tree.heading("Cliente", text="Cliente ($)")
        tree.heading("Ganancia", text="Ganancia")
        tree.heading("Empresa", text="Empresa")
        
        tree.column("Material", width=160)
        tree.column("Venta", width=90)
        tree.column("Cliente", width=100)
        tree.column("Ganancia", width=120)
        tree.column("Empresa", width=180)
        tree.pack(fill='both', expand=True)
        
        self.trees_materiales[tipo] = tree
        
        self.actualizar_tabla_materiales(tree, tipo)
    
    def sincronizar_precios_inventario(self, nombre_material, precio_venta, seccion, empresa=""):
        if nombre_material in self.inventario:
            self.inventario[nombre_material]["precio_venta"] = self.redondear(precio_venta)
            self.inventario[nombre_material]["seccion"] = seccion
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_lista_venta()
            return True
        return False
    
    def sincronizar_todos_precios(self, seccion):
        if seccion not in self.materiales:
            return
        
        actualizados = 0
        for material in self.materiales[seccion]:
            nombre = material["nombre"]
            precio = self.redondear(material["precio_venta"])
            if nombre in self.inventario:
                self.inventario[nombre]["precio_venta"] = precio
                self.inventario[nombre]["seccion"] = seccion
                actualizados += 1
        
        if actualizados > 0:
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_lista_venta()
            self.actualizar_todas_tablas_materiales()
            messagebox.showinfo("Éxito", 
                f"✅ {actualizados} precios sincronizados en la sección {seccion.upper()}")
        else:
            messagebox.showinfo("Información", 
                f"No hay materiales de la sección {seccion.upper()} en el inventario")
    
    # ==================== TAB POS VENTA ====================
    
    def crear_tab_pos_venta(self):
        frame_simulacion = ttk.LabelFrame(self.tab_pos_venta, text="📊 Simular Venta a Empresa")
        frame_simulacion.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_simulacion, text="Empresa:").grid(row=0, column=0, padx=4, pady=4)
        self.pos_venta_empresa_combo = ttk.Combobox(frame_simulacion, values=EMPRESAS_POS_VENTA, width=25)
        self.pos_venta_empresa_combo.grid(row=0, column=1, padx=4, pady=4)
        
        ttk.Label(frame_simulacion, text="Material:").grid(row=0, column=2, padx=4, pady=4)
        self.pos_venta_material_combo = ttk.Combobox(frame_simulacion, width=25)
        self.pos_venta_material_combo.grid(row=0, column=3, padx=4, pady=4)
        self.pos_venta_material_combo.bind('<<ComboboxSelected>>', self.actualizar_info_pos_venta)
        
        ttk.Label(frame_simulacion, text="Cantidad (kg):").grid(row=0, column=4, padx=4, pady=4)
        self.pos_venta_cantidad_entry = ttk.Entry(frame_simulacion, width=12)
        self.pos_venta_cantidad_entry.grid(row=0, column=5, padx=4, pady=4)
        
        self.pos_venta_info_label = ttk.Label(frame_simulacion, text="", font=("Arial", 9))
        self.pos_venta_info_label.grid(row=1, column=0, columnspan=6, padx=4, pady=4, sticky='w')
        
        self.pos_venta_total_label = ttk.Label(frame_simulacion, text="💰 Total estimado: $0.00", 
                                              font=("Arial", 11, "bold"), foreground="blue")
        self.pos_venta_total_label.grid(row=2, column=0, columnspan=6, padx=4, pady=4)
        
        ttk.Button(frame_simulacion, text="✅ Registrar Venta Simulada", 
                  command=self.registrar_pos_venta).grid(row=3, column=0, columnspan=6, pady=8)
        
        frame_lista = ttk.LabelFrame(self.tab_pos_venta, text="📋 Ventas Simuladas Realizadas")
        frame_lista.pack(pady=8, padx=8, fill='both', expand=True)
        
        self.tree_ventas_simuladas = ttk.Treeview(frame_lista, 
            columns=("ID", "Fecha", "Empresa", "Material", "Cantidad", "Precio", "Total", "Stock Actual", "Stock Restante"), 
            show='headings', height=12)
        self.tree_ventas_simuladas.heading("ID", text="ID")
        self.tree_ventas_simuladas.heading("Fecha", text="Fecha")
        self.tree_ventas_simuladas.heading("Empresa", text="Empresa")
        self.tree_ventas_simuladas.heading("Material", text="Material")
        self.tree_ventas_simuladas.heading("Cantidad", text="Cantidad (kg)")
        self.tree_ventas_simuladas.heading("Precio", text="Precio ($/kg)")
        self.tree_ventas_simuladas.heading("Total", text="Total ($)")
        self.tree_ventas_simuladas.heading("Stock Actual", text="Stock Actual (kg)")
        self.tree_ventas_simuladas.heading("Stock Restante", text="Stock Restante (kg)")
        
        self.tree_ventas_simuladas.column("ID", width=40)
        self.tree_ventas_simuladas.column("Fecha", width=130)
        self.tree_ventas_simuladas.column("Empresa", width=150)
        self.tree_ventas_simuladas.column("Material", width=140)
        self.tree_ventas_simuladas.column("Cantidad", width=80)
        self.tree_ventas_simuladas.column("Precio", width=80)
        self.tree_ventas_simuladas.column("Total", width=90)
        self.tree_ventas_simuladas.column("Stock Actual", width=90)
        self.tree_ventas_simuladas.column("Stock Restante", width=90)
        self.tree_ventas_simuladas.pack(fill='both', expand=True)
        
        frame_botones_pos = ttk.Frame(self.tab_pos_venta)
        frame_botones_pos.pack(pady=5, fill='x')
        
        ttk.Button(frame_botones_pos, text="🗑️ Eliminar Venta Simulada", 
                  command=self.eliminar_pos_venta).pack(side='left', padx=5)
        ttk.Button(frame_botones_pos, text="🔄 Actualizar", 
                  command=self.actualizar_lista_ventas_simuladas).pack(side='left', padx=5)
        ttk.Button(frame_botones_pos, text="📊 Calcular Total", 
                  command=self.mostrar_resumen_pos_venta).pack(side='left', padx=5)
        
        self.pos_venta_resumen_label = ttk.Label(self.tab_pos_venta, 
                                                 text="💰 Total de Ventas Simuladas: $0.00 | 📦 Total Materiales: 0",
                                                 font=("Arial", 10, "bold"), foreground="green")
        self.pos_venta_resumen_label.pack(pady=5)
        
        self.cargar_materiales_pos_venta()
        self.actualizar_lista_ventas_simuladas()
        self.actualizar_resumen_pos_venta()
    
    def cargar_materiales_pos_venta(self):
        materiales = []
        if 'pos_venta' in self.materiales:
            for m in self.materiales['pos_venta']:
                materiales.append(m['nombre'])
        self.pos_venta_material_combo['values'] = materiales
    
    def actualizar_info_pos_venta(self, event=None):
        material = self.pos_venta_material_combo.get()
        if not material:
            return
        
        precio = 0
        for m in self.materiales.get('pos_venta', []):
            if m['nombre'] == material:
                precio = m.get('precio_venta', 0)
                break
        
        stock = 0
        if material in self.inventario:
            stock = self.inventario[material].get('stock', 0)
        
        self.pos_venta_info_label.config(
            text=f"💰 Precio: ${precio:.2f}/kg | 📦 Stock en inventario: {stock:.2f} kg"
        )
        
        self.actualizar_total_pos_venta()
    
    def actualizar_total_pos_venta(self, event=None):
        material = self.pos_venta_material_combo.get()
        if not material:
            self.pos_venta_total_label.config(text="💰 Total estimado: $0.00")
            return
        
        try:
            cantidad = float(self.pos_venta_cantidad_entry.get())
            if cantidad <= 0:
                self.pos_venta_total_label.config(text="💰 Total estimado: $0.00")
                return
        except:
            self.pos_venta_total_label.config(text="💰 Total estimado: $0.00")
            return
        
        precio = 0
        for m in self.materiales.get('pos_venta', []):
            if m['nombre'] == material:
                precio = m.get('precio_venta', 0)
                break
        
        total = self.redondear(cantidad * precio)
        self.pos_venta_total_label.config(text=f"💰 Total estimado: ${total:.2f}")
    
    def registrar_pos_venta(self):
        empresa = self.pos_venta_empresa_combo.get()
        material = self.pos_venta_material_combo.get()
        
        if not empresa:
            messagebox.showwarning("Error", "Seleccione una empresa")
            return
        
        if not material:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        try:
            cantidad = float(self.pos_venta_cantidad_entry.get())
            if cantidad <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Error", "Ingrese una cantidad válida")
            return
        
        resultado = self.registrar_venta_simulada(empresa, material, cantidad)
        
        if resultado.get('success'):
            messagebox.showinfo("Éxito", resultado.get('message'))
            self.pos_venta_cantidad_entry.delete(0, tk.END)
            self.pos_venta_total_label.config(text="💰 Total estimado: $0.00")
            self.actualizar_lista_ventas_simuladas()
            self.actualizar_resumen_pos_venta()
            self.actualizar_tabla_inventario()
            self.actualizar_metricas()
        else:
            messagebox.showerror("Error", resultado.get('message', 'Error al registrar la venta simulada'))
    
    def eliminar_pos_venta(self):
        seleccion = self.tree_ventas_simuladas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una venta simulada para eliminar")
            return
        
        item = self.tree_ventas_simuladas.item(seleccion)
        valores = item['values']
        venta_id = int(valores[0])
        
        if messagebox.askyesno("Confirmar", 
            f"⚠️ ¿Eliminar la venta simulada #{venta_id}?\n\n"
            f"Esta acción no se puede deshacer."):
            
            resultado = self.eliminar_venta_simulada(venta_id)
            if resultado.get('success'):
                messagebox.showinfo("Éxito", resultado.get('message'))
                self.actualizar_lista_ventas_simuladas()
                self.actualizar_resumen_pos_venta()
                self.actualizar_tabla_inventario()
                self.actualizar_metricas()
            else:
                messagebox.showerror("Error", resultado.get('message', 'Error al eliminar la venta simulada'))
    
    def mostrar_resumen_pos_venta(self):
        if not self.ventas_simuladas:
            messagebox.showinfo("Resumen", "No hay ventas simuladas registradas")
            return
        
        total_general = sum(v.get('total', 0) for v in self.ventas_simuladas)
        total_materiales = sum(v.get('cantidad', 0) for v in self.ventas_simuladas)
        
        por_empresa = defaultdict(lambda: {"total": 0, "cantidad": 0})
        for v in self.ventas_simuladas:
            empresa = v.get('empresa', 'Sin empresa')
            por_empresa[empresa]["total"] += v.get('total', 0)
            por_empresa[empresa]["cantidad"] += v.get('cantidad', 0)
        
        por_material = defaultdict(lambda: {"total": 0, "cantidad": 0})
        for v in self.ventas_simuladas:
            material = v.get('material', 'Sin material')
            por_material[material]["total"] += v.get('total', 0)
            por_material[material]["cantidad"] += v.get('cantidad', 0)
        
        mensaje = f"📊 RESUMEN DE VENTAS SIMULADAS\n"
        mensaje += f"{'='*40}\n\n"
        mensaje += f"💰 Total General: ${total_general:.2f}\n"
        mensaje += f"📦 Total Materiales: {total_materiales:.2f} kg\n"
        mensaje += f"📋 Total Transacciones: {len(self.ventas_simuladas)}\n\n"
        
        mensaje += f"📋 POR EMPRESA:\n"
        for empresa, datos in sorted(por_empresa.items(), key=lambda x: x[1]["total"], reverse=True):
            mensaje += f"   • {empresa}: ${datos['total']:.2f} ({datos['cantidad']:.2f} kg)\n"
        
        mensaje += f"\n📋 POR MATERIAL:\n"
        for material, datos in sorted(por_material.items(), key=lambda x: x[1]["total"], reverse=True):
            mensaje += f"   • {material}: ${datos['total']:.2f} ({datos['cantidad']:.2f} kg)\n"
        
        messagebox.showinfo("Resumen de Pos Venta", mensaje)
    
    def actualizar_resumen_pos_venta(self):
        total = sum(v.get('total', 0) for v in self.ventas_simuladas)
        cantidad = sum(v.get('cantidad', 0) for v in self.ventas_simuladas)
        self.pos_venta_resumen_label.config(
            text=f"💰 Total de Ventas Simuladas: ${total:.2f} | 📦 Total Materiales: {cantidad:.2f} kg | 📋 Registros: {len(self.ventas_simuladas)}"
        )
    
    # ==================== TAB INVENTARIO ====================
    
    def crear_tab_inventario(self):
        main_frame = ttk.Frame(self.tab_inventario)
        main_frame.pack(fill='both', expand=True)
        
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        frame_resumen = ttk.LabelFrame(scrollable_frame, text="📊 RESUMEN DE STOCK E INVERSIÓN POR CATEGORÍA")
        frame_resumen.pack(pady=5, padx=8, fill='x')
        
        categorias = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"]
        colores = {
            "ferrosos": "#2c3e50",
            "plasticos": "#27ae60",
            "electronicos": "#2980b9",
            "papel": "#f39c12",
            "por_pieza": "#8e44ad",
            "pos_venta": "#e74c3c"
        }
        iconos = {
            "ferrosos": "⚙️",
            "plasticos": "🧴",
            "electronicos": "💻",
            "papel": "📄",
            "por_pieza": "🔩",
            "pos_venta": "📊"
        }
        
        self.labels_categoria = {}
        
        for i, categoria in enumerate(categorias):
            frame_cat = ttk.Frame(frame_resumen, relief='ridge', borderwidth=2)
            frame_cat.grid(row=0, column=i, padx=8, pady=8, sticky='nsew')
            
            ttk.Label(frame_cat, text=f"{iconos[categoria]} {categoria.upper()}", 
                     font=("Arial", 10, "bold"), foreground=colores[categoria]).pack(pady=3)
            
            label_stock = ttk.Label(frame_cat, text="Stock: 0.00 kg", font=("Arial", 9))
            label_stock.pack(pady=1)
            self.labels_categoria[f"{categoria}_stock"] = label_stock
            
            label_inversion = ttk.Label(frame_cat, text="💰 Inversión: $0.00", font=("Arial", 9, "bold"), foreground="blue")
            label_inversion.pack(pady=1)
            self.labels_categoria[f"{categoria}_inversion"] = label_inversion
            
            label_cantidad = ttk.Label(frame_cat, text="Materiales: 0", font=("Arial", 8))
            label_cantidad.pack(pady=1)
            self.labels_categoria[f"{categoria}_cantidad"] = label_cantidad
            
            label_valor = ttk.Label(frame_cat, text="Valor: $0.00", font=("Arial", 8), foreground="green")
            label_valor.pack(pady=1)
            self.labels_categoria[f"{categoria}_valor"] = label_valor
        
        frame_resumen.grid_columnconfigure(0, weight=1)
        frame_resumen.grid_columnconfigure(1, weight=1)
        frame_resumen.grid_columnconfigure(2, weight=1)
        frame_resumen.grid_columnconfigure(3, weight=1)
        frame_resumen.grid_columnconfigure(4, weight=1)
        frame_resumen.grid_columnconfigure(5, weight=1)
        
        frame_registro = ttk.LabelFrame(scrollable_frame, text="➕ Agregar/Editar Material en Inventario")
        frame_registro.pack(pady=5, padx=8, fill='x')
        
        ttk.Label(frame_registro, text="Material:").grid(row=0, column=0, padx=3, pady=2)
        self.entry_inv_nombre = ttk.Entry(frame_registro, width=18)
        self.entry_inv_nombre.grid(row=0, column=1, padx=3, pady=2)
        
        ttk.Label(frame_registro, text="Sección:").grid(row=0, column=2, padx=3, pady=2)
        self.combo_inv_seccion = ttk.Combobox(frame_registro, 
            values=["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"], width=12)
        self.combo_inv_seccion.grid(row=0, column=3, padx=3, pady=2)
        
        ttk.Label(frame_registro, text="Stock:").grid(row=0, column=4, padx=3, pady=2)
        self.entry_inv_stock = ttk.Entry(frame_registro, width=10)
        self.entry_inv_stock.grid(row=0, column=5, padx=3, pady=2)
        
        ttk.Label(frame_registro, text="Precio Venta:").grid(row=1, column=0, padx=3, pady=2)
        self.entry_inv_precio_venta = ttk.Entry(frame_registro, width=10)
        self.entry_inv_precio_venta.grid(row=1, column=1, padx=3, pady=2)
        
        ttk.Label(frame_registro, text="Precio Cliente:").grid(row=1, column=2, padx=3, pady=2)
        self.entry_inv_precio_cliente = ttk.Entry(frame_registro, width=10)
        self.entry_inv_precio_cliente.grid(row=1, column=3, padx=3, pady=2)
        
        self.label_inv_ganancia = ttk.Label(frame_registro, text="", font=("Arial", 9))
        self.label_inv_ganancia.grid(row=1, column=4, columnspan=2, padx=3, pady=2)
        
        def actualizar_precio_cliente_inv(*args):
            try:
                nombre = self.entry_inv_nombre.get().strip()
                precio = float(self.entry_inv_precio_venta.get()) if self.entry_inv_precio_venta.get() else 0
                precio_cliente = self.calcular_precio_cliente(nombre, precio)
                ganancia = self.calcular_ganancia(nombre, precio)
                porcentaje = self.obtener_porcentaje_ganancia(nombre) * 100
                self.entry_inv_precio_cliente.delete(0, tk.END)
                self.entry_inv_precio_cliente.insert(0, f"{precio_cliente:.2f}")
                
                if precio > 0:
                    self.label_inv_ganancia.config(
                        text=f"💰 Ganancia: ${ganancia:.2f}/kg ({porcentaje:.1f}%)",
                        foreground="red" if porcentaje == 5 else "green"
                    )
                else:
                    self.label_inv_ganancia.config(text="")
            except:
                pass
        
        self.entry_inv_precio_venta.bind('<KeyRelease>', actualizar_precio_cliente_inv)
        self.entry_inv_nombre.bind('<KeyRelease>', actualizar_precio_cliente_inv)
        
        ttk.Label(frame_registro, text="Descripción:").grid(row=2, column=0, padx=3, pady=2)
        self.entry_inv_desc = ttk.Entry(frame_registro, width=45)
        self.entry_inv_desc.grid(row=2, column=1, columnspan=3, padx=3, pady=2, sticky='we')
        
        frame_botones_form = ttk.Frame(frame_registro)
        frame_botones_form.grid(row=2, column=4, columnspan=2, padx=3, pady=2)
        
        ttk.Button(frame_botones_form, text="➕ Agregar", command=self.agregar_material_inventario).pack(side='left', padx=2)
        ttk.Button(frame_botones_form, text="🔄 Sincronizar", command=self.sincronizar_todos_los_precios).pack(side='left', padx=2)
        
        frame_tabla = ttk.LabelFrame(scrollable_frame, text="📦 INVENTARIO COMPLETO")
        frame_tabla.pack(pady=5, padx=8, fill='both', expand=True)
        
        tabla_frame = ttk.Frame(frame_tabla)
        tabla_frame.pack(fill='both', expand=True)
        
        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(tabla_frame, orient="horizontal")
        
        self.tree_inventario = ttk.Treeview(tabla_frame, 
            columns=("Material", "Sección", "Stock", "Precio Venta", "Precio Cliente", "Ganancia", "Costo Promedio", "Valor Potencial", "Ganancia Potencial", "Inversión Total", "Total Comprado"), 
            show='headings', height=10,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set)
        
        scroll_y.config(command=self.tree_inventario.yview)
        scroll_x.config(command=self.tree_inventario.xview)
        
        self.tree_inventario.heading("Material", text="Material")
        self.tree_inventario.heading("Sección", text="Sección")
        self.tree_inventario.heading("Stock", text="Stock (kg)")
        self.tree_inventario.heading("Precio Venta", text="Precio Venta ($/kg)")
        self.tree_inventario.heading("Precio Cliente", text="Precio Cliente ($/kg)")
        self.tree_inventario.heading("Ganancia", text="Ganancia ($/kg)")
        self.tree_inventario.heading("Costo Promedio", text="Costo Promedio ($/kg)")
        self.tree_inventario.heading("Valor Potencial", text="Valor Potencial ($)")
        self.tree_inventario.heading("Ganancia Potencial", text="💰 Ganancia Potencial ($)")
        self.tree_inventario.heading("Inversión Total", text="Inversión Total ($)")
        self.tree_inventario.heading("Total Comprado", text="Total Comprado (kg)")
        
        self.tree_inventario.column("Material", width=140)
        self.tree_inventario.column("Sección", width=80)
        self.tree_inventario.column("Stock", width=70, anchor='center')
        self.tree_inventario.column("Precio Venta", width=90, anchor='center')
        self.tree_inventario.column("Precio Cliente", width=90, anchor='center')
        self.tree_inventario.column("Ganancia", width=90, anchor='center')
        self.tree_inventario.column("Costo Promedio", width=90, anchor='center')
        self.tree_inventario.column("Valor Potencial", width=100, anchor='center')
        self.tree_inventario.column("Ganancia Potencial", width=110, anchor='center')
        self.tree_inventario.column("Inversión Total", width=100, anchor='center')
        self.tree_inventario.column("Total Comprado", width=90, anchor='center')
        
        self.tree_inventario.pack(side='left', fill='both', expand=True)
        scroll_y.pack(side='right', fill='y')
        scroll_x.pack(side='bottom', fill='x')
        
        frame_botones_inv = ttk.Frame(scrollable_frame)
        frame_botones_inv.pack(pady=5, padx=8, fill='x')
        
        self.seleccionar_todos_inventario = tk.BooleanVar(value=False)
        chk_todos_inv = ttk.Checkbutton(frame_botones_inv, text="☑️ Seleccionar Todos", 
                                       variable=self.seleccionar_todos_inventario,
                                       command=self.toggle_seleccion_todos_inventario)
        chk_todos_inv.pack(side='left', padx=2)
        
        botones_inv = [
            ("✏️ Editar", self.editar_material_inventario),
            ("🗑️ Eliminar Sel.", self.eliminar_materiales_seleccionados),
            ("➕ Aumentar Stock", self.aumentar_stock_inventario),
            ("➖ Reducir Stock", self.reducir_stock_inventario),
            ("🔄 Actualizar Remisiones", self.actualizar_inventario_desde_compras),
            ("📊 Actualizar", self.actualizar_tabla_inventario),
            ("🔧 Resetear Inversión", self.resetear_inversion_a_cero),
            ("📋 Ver Remisiones", self.mostrar_remisiones_guardadas)
        ]
        
        for texto, comando in botones_inv:
            btn = ttk.Button(frame_botones_inv, text=texto, command=comando)
            btn.pack(side='left', padx=2, pady=2)
        
        self.tree_inventario.bind('<<TreeviewSelect>>', self.on_inventario_seleccionado)
        
        self.actualizar_tabla_inventario()
    
    def on_inventario_seleccionado(self, event):
        pass
    
    def toggle_seleccion_todos_inventario(self):
        seleccionar = self.seleccionar_todos_inventario.get()
        for item in self.tree_inventario.get_children():
            valores = self.tree_inventario.item(item)['values']
            if valores and not str(valores[0]).startswith("=== TOTALES"):
                if seleccionar:
                    self.tree_inventario.selection_add(item)
                else:
                    self.tree_inventario.selection_remove(item)
    
    def eliminar_materiales_seleccionados(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos un material para eliminar")
            return
        
        materiales_a_eliminar = []
        for item in seleccion:
            valores = self.tree_inventario.item(item)['values']
            nombre = valores[0]
            if not str(nombre).startswith("=== TOTALES"):
                materiales_a_eliminar.append(nombre)
        
        if not materiales_a_eliminar:
            messagebox.showwarning("Error", "No hay materiales seleccionados para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(materiales_a_eliminar)} material(es) del inventario?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        for nombre in materiales_a_eliminar:
            if nombre in self.inventario:
                del self.inventario[nombre]
        
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        self.actualizar_lista_venta()
        self.cargar_materiales_pos_venta()
        self.seleccionar_todos_inventario.set(False)
        
        messagebox.showinfo("Éxito", f"✅ {len(materiales_a_eliminar)} material(es) eliminado(s) correctamente")
    
    def sincronizar_todos_los_precios(self):
        secciones = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"]
        total_actualizados = 0
        
        for seccion in secciones:
            if seccion in self.materiales:
                for material in self.materiales[seccion]:
                    nombre = material["nombre"]
                    precio = self.redondear(material["precio_venta"])
                    if nombre in self.inventario:
                        self.inventario[nombre]["precio_venta"] = precio
                        self.inventario[nombre]["seccion"] = seccion
                        total_actualizados += 1
        
        if total_actualizados > 0:
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_lista_venta()
            self.actualizar_todas_tablas_materiales()
            messagebox.showinfo("Éxito", f"✅ {total_actualizados} precios sincronizados desde todas las secciones")
        else:
            messagebox.showinfo("Información", "No hay materiales para sincronizar")
    
    def actualizar_tabla_inventario(self):
        for item in self.tree_inventario.get_children():
            self.tree_inventario.delete(item)
        
        resumen = {
            "ferrosos": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0},
            "plasticos": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0},
            "electronicos": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0},
            "papel": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0},
            "por_pieza": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0},
            "pos_venta": {"stock": 0, "cantidad": 0, "valor": 0, "ganancia": 0, "inversion": 0}
        }
        
        for material, datos in sorted(self.inventario.items()):
            seccion = datos.get("seccion", "inventario")
            stock = datos.get("stock", 0)
            precio_venta = self.redondear(datos.get("precio_venta", 0))
            precio_cliente = self.calcular_precio_cliente(material, precio_venta)
            ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
            costo_promedio = self.redondear(datos.get("inversion_promedio", 0))
            inversion_total = self.redondear(datos.get("inversion_total", 0))
            total_comprado = self.redondear(datos.get("total_comprado", 0))
            porcentaje = self.obtener_porcentaje_ganancia(material) * 100
            
            valor_total = self.redondear(stock * precio_venta)
            ganancia_potencial = self.redondear(stock * ganancia_por_kg) if stock > 0 else 0
            
            if stock == 0 and inversion_total > 0:
                inversion_total = 0
                datos["inversion_total"] = 0
                datos["inversion_promedio"] = 0
            
            if stock > 0 or precio_venta > 0 or inversion_total > 0:
                if stock == 0:
                    color = "red"
                elif stock < 10:
                    color = "orange"
                else:
                    color = "green"
                
                if ganancia_potencial > 0:
                    ganancia_color = "ganancia_positiva"
                elif ganancia_potencial < 0:
                    ganancia_color = "ganancia_negativa"
                else:
                    ganancia_color = "ganancia_cero"
                
                ganancia_text = f"{ganancia_por_kg:.2f} ({porcentaje:.1f}%)"
                
                self.tree_inventario.insert("", "end", values=(
                    material,
                    seccion.capitalize(),
                    f"{stock:.2f}",
                    f"{precio_venta:.2f}",
                    f"{precio_cliente:.2f}",
                    ganancia_text,
                    f"{costo_promedio:.2f}",
                    f"{valor_total:.2f}",
                    f"{ganancia_potencial:.2f}",
                    f"{inversion_total:.2f}",
                    f"{total_comprado:.2f}"
                ), tags=(color, ganancia_color))
            
            if seccion in resumen:
                resumen[seccion]["stock"] += stock
                resumen[seccion]["cantidad"] += 1 if stock > 0 or precio_venta > 0 else 0
                resumen[seccion]["valor"] += valor_total
                resumen[seccion]["ganancia"] += ganancia_potencial
        
        for categoria in resumen:
            inv_total = 0
            for material, datos in self.inventario.items():
                if datos.get("seccion") == categoria:
                    inv_total += datos.get("inversion_total", 0)
            resumen[categoria]["inversion"] = self.redondear(inv_total)
        
        self.tree_inventario.tag_configure('red', foreground='red')
        self.tree_inventario.tag_configure('orange', foreground='orange')
        self.tree_inventario.tag_configure('green', foreground='darkgreen')
        self.tree_inventario.tag_configure('ganancia_positiva', foreground='green')
        self.tree_inventario.tag_configure('ganancia_negativa', foreground='red')
        self.tree_inventario.tag_configure('ganancia_cero', foreground='gray')
        
        total_stock = sum(r["stock"] for r in resumen.values())
        total_valor = sum(r["valor"] for r in resumen.values())
        total_materiales = sum(r["cantidad"] for r in resumen.values())
        total_inversion = sum(r["inversion"] for r in resumen.values())
        total_ganancia = sum(r["ganancia"] for r in resumen.values())
        
        self.tree_inventario.insert("", "end", values=(
            "=== TOTALES ===",
            "",
            f"{total_stock:.2f}",
            "",
            "",
            "",
            "",
            f"{total_valor:.2f}",
            f"{total_ganancia:.2f}",
            f"{total_inversion:.2f}",
            ""
        ), tags=('total',))
        self.tree_inventario.tag_configure('total', font=('Arial', 10, 'bold'))
        
        for categoria in resumen:
            self.labels_categoria[f"{categoria}_stock"].config(
                text=f"Stock: {resumen[categoria]['stock']:.2f} kg"
            )
            self.labels_categoria[f"{categoria}_inversion"].config(
                text=f"💰 Inversión: ${resumen[categoria]['inversion']:.2f}"
            )
            self.labels_categoria[f"{categoria}_cantidad"].config(
                text=f"Materiales: {resumen[categoria]['cantidad']}"
            )
            self.labels_categoria[f"{categoria}_valor"].config(
                text=f"Valor: ${resumen[categoria]['valor']:.2f}"
            )
        
        self.seleccionar_todos_inventario.set(False)
    
    def resetear_inversion_a_cero(self):
        if not messagebox.askyesno("Confirmar", 
            "⚠️ Esta acción reseteará a $0.00 la inversión de todos los materiales que tengan stock 0.\n\n"
            "¿Está seguro de continuar?"):
            return
        
        materiales_reseteados = []
        for material, datos in self.inventario.items():
            if datos.get("stock", 0) == 0 and datos.get("inversion_total", 0) > 0:
                datos["inversion_total"] = 0
                datos["inversion_promedio"] = 0
                datos["total_comprado"] = 0
                materiales_reseteados.append(material)
        
        if not materiales_reseteados:
            messagebox.showinfo("Información", "No hay materiales con stock 0 que necesiten resetear su inversión.")
            return
        
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        
        mensaje = f"✅ Inversión reseteada a cero para {len(materiales_reseteados)} materiales:\n\n"
        for m in materiales_reseteados[:15]:
            mensaje += f"• {m}\n"
        if len(materiales_reseteados) > 15:
            mensaje += f"\n... y {len(materiales_reseteados) - 15} materiales más"
        
        messagebox.showinfo("Éxito", mensaje)
    
    def agregar_material_inventario(self):
        nombre = self.entry_inv_nombre.get().strip()
        seccion = self.combo_inv_seccion.get()
        
        if not nombre:
            messagebox.showwarning("Error", "El nombre del material es obligatorio")
            return
        
        if not seccion:
            messagebox.showwarning("Error", "Seleccione una sección")
            return
        
        try:
            stock = float(self.entry_inv_stock.get()) if self.entry_inv_stock.get() else 0
            precio_venta = float(self.entry_inv_precio_venta.get()) if self.entry_inv_precio_venta.get() else 0
            precio_cliente = float(self.entry_inv_precio_cliente.get()) if self.entry_inv_precio_cliente.get() else 0
            
            stock = self.redondear(stock, 3)
            precio_venta = self.redondear(precio_venta)
            precio_cliente = self.redondear(precio_cliente)
            
            if stock < 0 or precio_venta < 0 or precio_cliente < 0:
                raise ValueError
        except:
            messagebox.showwarning("Error", "Stock y precios válidos requeridos")
            return
        
        descripcion = self.entry_inv_desc.get().strip()
        
        if nombre in self.inventario:
            if messagebox.askyesno("Confirmar", f"El material '{nombre}' ya existe en inventario.\n"
                                       f"Stock actual: {self.inventario[nombre]['stock']:.2f} kg\n"
                                       f"Inversión actual: ${self.inventario[nombre].get('inversion_total', 0):.2f}\n\n"
                                       f"¿Desea actualizar sus datos?"):
                self.inventario[nombre]["stock"] = stock
                self.inventario[nombre]["precio_venta"] = precio_venta
                self.inventario[nombre]["precio_compra_cliente"] = precio_cliente
                self.inventario[nombre]["seccion"] = seccion
                self.inventario[nombre]["descripcion"] = descripcion
                messagebox.showinfo("Éxito", f"Material '{nombre}' actualizado en inventario")
        else:
            self.inventario[nombre] = {
                "stock": stock,
                "precio_venta": precio_venta,
                "precio_compra_cliente": precio_cliente,
                "seccion": seccion,
                "descripcion": descripcion,
                "inversion_total": 0,
                "inversion_promedio": 0,
                "total_comprado": 0
            }
            messagebox.showinfo("Éxito", f"Material '{nombre}' agregado al inventario")
        
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        self.actualizar_lista_venta()
        self.cargar_materiales_pos_venta()
        
        self.entry_inv_nombre.delete(0, tk.END)
        self.entry_inv_stock.delete(0, tk.END)
        self.entry_inv_precio_venta.delete(0, tk.END)
        self.entry_inv_precio_cliente.delete(0, tk.END)
        self.entry_inv_desc.delete(0, tk.END)
        self.combo_inv_seccion.set("")
    
    def actualizar_inventario_desde_compras(self):
        compras_procesar = []
        
        for compra in self.compras:
            if compra.get('tipo_precio') == 'cliente' and 'remision_id' in compra:
                if not compra.get('procesada_inventario', False):
                    compras_procesar.append(compra)
        
        if not compras_procesar:
            messagebox.showinfo("Inventario", "No hay compras nuevas para procesar")
            return
        
        materiales_actualizados = []
        
        for compra in compras_procesar:
            material = compra.get('material')
            seccion = compra.get('seccion')
            cantidad = compra.get('cantidad', 0.0)
            precio_unitario = compra.get('precio_unitario', 0.0)
            tipo_precio = compra.get('tipo_precio', 'cliente')
            
            if not material:
                continue
            
            precio_venta = 0.0
            precio_cliente = 0.0
            
            if seccion in self.materiales:
                for m in self.materiales[seccion]:
                    if m['nombre'] == material:
                        precio_venta = self.redondear(m.get('precio_venta', 0.0))
                        precio_cliente = self.calcular_precio_cliente(material, precio_venta)
                        break
            
            costo_compra = self.redondear(cantidad * precio_unitario)
            
            if material in self.inventario:
                stock_anterior = self.inventario[material]["stock"]
                inversion_anterior = self.inventario[material].get("inversion_total", 0)
                total_comprado_anterior = self.inventario[material].get("total_comprado", 0)
                
                self.inventario[material]["stock"] = self.redondear(stock_anterior + cantidad)
                
                if stock_anterior == 0:
                    self.inventario[material]["inversion_total"] = costo_compra
                else:
                    nueva_inversion = self.redondear(inversion_anterior + costo_compra)
                    self.inventario[material]["inversion_total"] = nueva_inversion
                
                nuevo_total_comprado = self.redondear(total_comprado_anterior + cantidad)
                self.inventario[material]["total_comprado"] = nuevo_total_comprado
                
                if nuevo_total_comprado > 0:
                    costo_promedio = self.redondear(self.inventario[material]["inversion_total"] / nuevo_total_comprado)
                    self.inventario[material]["inversion_promedio"] = costo_promedio
                
                if precio_venta > self.inventario[material].get("precio_venta", 0):
                    self.inventario[material]["precio_venta"] = precio_venta
                
                if precio_cliente > 0:
                    self.inventario[material]["precio_compra_cliente"] = precio_cliente
                
                if seccion and not self.inventario[material].get("seccion"):
                    self.inventario[material]["seccion"] = seccion
                
                materiales_actualizados.append(
                    f"{material} ({seccion}): "
                    f"Stock: {stock_anterior:.2f} → {self.inventario[material]['stock']:.2f} kg | "
                    f"Inversión: ${inversion_anterior:.2f} → ${self.inventario[material]['inversion_total']:.2f}"
                )
            else:
                self.inventario[material] = {
                    "stock": self.redondear(cantidad),
                    "precio_venta": precio_venta,
                    "precio_compra_cliente": precio_cliente,
                    "seccion": seccion or "inventario",
                    "descripcion": f"Agregado desde remisión",
                    "inversion_total": costo_compra,
                    "inversion_promedio": self.redondear(precio_unitario),
                    "total_comprado": cantidad
                }
                materiales_actualizados.append(
                    f"{material} ({seccion}): "
                    f"Stock: 0.00 → {cantidad:.2f} kg | "
                    f"Inversión: $0.00 → ${costo_compra:.2f} (nuevo)"
                )
            
            compra['procesada_inventario'] = True
        
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        self.actualizar_lista_venta()
        self.cargar_materiales_pos_venta()
        
        mensaje = f"✅ Inventario actualizado desde {len(compras_procesar)} compras:\n\n"
        for item in materiales_actualizados[:10]:
            mensaje += f"• {item}\n"
        if len(materiales_actualizados) > 10:
            mensaje += f"\n... y {len(materiales_actualizados) - 10} materiales más"
        
        messagebox.showinfo("Éxito", mensaje)
    
    def editar_material_inventario(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        item = seleccion[0]
        item_data = self.tree_inventario.item(item)
        valores = item_data['values']
        nombre_original = valores[0]
        
        if nombre_original.startswith("=== TOTALES"):
            messagebox.showwarning("Error", "No puede editar la fila de totales")
            return
        
        if nombre_original not in self.inventario:
            messagebox.showwarning("Error", "Material no encontrado")
            return
        
        datos = self.inventario[nombre_original]
        
        ventana_editar = tk.Toplevel(self.root)
        ventana_editar.title(f"Editar Material: {nombre_original}")
        ventana_editar.geometry("450x600")
        ventana_editar.transient(self.root)
        ventana_editar.grab_set()
        
        ttk.Label(ventana_editar, text="Nombre:").pack(pady=3)
        nombre_entry = ttk.Entry(ventana_editar, width=30)
        nombre_entry.insert(0, nombre_original)
        nombre_entry.pack(pady=3)
        
        ttk.Label(ventana_editar, text="Sección:").pack(pady=3)
        seccion_combo = ttk.Combobox(ventana_editar, 
            values=["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"], width=25)
        seccion_combo.set(datos.get("seccion", ""))
        seccion_combo.pack(pady=3)
        
        ttk.Label(ventana_editar, text="Stock (kg):").pack(pady=3)
        stock_entry = ttk.Entry(ventana_editar, width=15)
        stock_entry.insert(0, str(datos.get("stock", 0)))
        stock_entry.pack(pady=3)
        
        ttk.Label(ventana_editar, text="Precio Venta ($/kg):").pack(pady=3)
        precio_venta_entry = ttk.Entry(ventana_editar, width=15)
        precio_venta_entry.insert(0, str(datos.get("precio_venta", 0)))
        precio_venta_entry.pack(pady=3)
        
        ttk.Label(ventana_editar, text="Precio Cliente:").pack(pady=3)
        precio_cliente_entry = ttk.Entry(ventana_editar, width=15)
        precio_cliente_entry.insert(0, str(datos.get("precio_compra_cliente", 0)))
        precio_cliente_entry.pack(pady=3)
        
        ttk.Label(ventana_editar, text="Empresa:").pack(pady=3)
        empresa_combo = ttk.Combobox(ventana_editar, values=EMPRESAS_DISPONIBLES, width=25)
        empresa_actual = "Sin asignar"
        for seccion, items in self.materiales.items():
            for m in items:
                if m['nombre'] == nombre_original:
                    empresa_actual = m.get('empresa', 'Sin asignar')
                    break
        empresa_combo.set(empresa_actual)
        empresa_combo.pack(pady=3)
        
        ganancia_label = ttk.Label(ventana_editar, text="", font=("Arial", 10))
        ganancia_label.pack(pady=3)
        
        def actualizar_ganancia(*args):
            nombre = nombre_entry.get().strip()
            precio = float(precio_venta_entry.get()) if precio_venta_entry.get() else 0
            ganancia = self.calcular_ganancia(nombre, precio)
            porcentaje = self.obtener_porcentaje_ganancia(nombre) * 100
            if precio > 0:
                ganancia_label.config(
                    text=f"💰 Ganancia: ${ganancia:.2f}/kg ({porcentaje:.1f}%)",
                    foreground="red" if porcentaje == 5 else "green"
                )
            else:
                ganancia_label.config(text="")
        
        nombre_entry.bind('<KeyRelease>', actualizar_ganancia)
        precio_venta_entry.bind('<KeyRelease>', actualizar_ganancia)
        actualizar_ganancia()
        
        frame_info = ttk.LabelFrame(ventana_editar, text="📊 Información de Inversión")
        frame_info.pack(pady=5, padx=10, fill='x')
        
        ttk.Label(frame_info, text=f"Inversión Total: ${datos.get('inversion_total', 0):.2f}").pack(pady=1)
        ttk.Label(frame_info, text=f"Costo Promedio: ${datos.get('inversion_promedio', 0):.2f}/kg").pack(pady=1)
        ttk.Label(frame_info, text=f"Total Comprado: {datos.get('total_comprado', 0):.2f} kg").pack(pady=1)
        
        stock = datos.get('stock', 0)
        precio_venta = datos.get('precio_venta', 0)
        costo_promedio = datos.get('inversion_promedio', 0)
        ganancia = self.redondear(stock * self.calcular_ganancia(nombre_original, precio_venta)) if costo_promedio > 0 else 0
        ttk.Label(frame_info, text=f"Ganancia Potencial: ${ganancia:.2f}", font=("Arial", 10, "bold"), foreground="green" if ganancia > 0 else "red").pack(pady=1)
        
        ttk.Label(ventana_editar, text="Descripción:").pack(pady=3)
        desc_entry = ttk.Entry(ventana_editar, width=40)
        desc_entry.insert(0, datos.get("descripcion", ""))
        desc_entry.pack(pady=3)
        
        def guardar_cambios():
            nuevo_nombre = nombre_entry.get().strip()
            nueva_seccion = seccion_combo.get()
            nueva_empresa = empresa_combo.get().strip() or "Sin asignar"
            
            try:
                nuevo_stock = float(stock_entry.get())
                nuevo_precio_venta = float(precio_venta_entry.get())
                nuevo_precio_cliente = float(precio_cliente_entry.get())
                
                nuevo_stock = self.redondear(nuevo_stock, 3)
                nuevo_precio_venta = self.redondear(nuevo_precio_venta)
                nuevo_precio_cliente = self.redondear(nuevo_precio_cliente)
                
                if nuevo_stock < 0 or nuevo_precio_venta < 0 or nuevo_precio_cliente < 0:
                    raise ValueError
            except:
                messagebox.showwarning("Error", "Valores numéricos válidos requeridos")
                return
            
            if not nuevo_nombre:
                messagebox.showwarning("Error", "El nombre es obligatorio")
                return
            
            if not nueva_seccion:
                messagebox.showwarning("Error", "Seleccione una sección")
                return
            
            inversion_total = datos.get("inversion_total", 0)
            inversion_promedio = datos.get("inversion_promedio", 0)
            total_comprado = datos.get("total_comprado", 0)
            
            if nuevo_nombre != nombre_original:
                del self.inventario[nombre_original]
            
            self.inventario[nuevo_nombre] = {
                "stock": nuevo_stock,
                "precio_venta": nuevo_precio_venta,
                "precio_compra_cliente": nuevo_precio_cliente,
                "seccion": nueva_seccion,
                "descripcion": desc_entry.get().strip(),
                "inversion_total": inversion_total,
                "inversion_promedio": inversion_promedio,
                "total_comprado": total_comprado
            }
            
            for seccion, items in self.materiales.items():
                for m in items:
                    if m['nombre'] == nombre_original:
                        m['nombre'] = nuevo_nombre
                        m['precio_venta'] = nuevo_precio_venta
                        m['empresa'] = nueva_empresa
                        break
            
            self.ordenar_materiales_alfabeticamente()
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_lista_venta()
            self.actualizar_todas_tablas_materiales()
            self.cargar_materiales_pos_venta()
            ventana_editar.destroy()
            messagebox.showinfo("Éxito", "Material actualizado")
        
        ttk.Button(ventana_editar, text="Guardar Cambios", command=guardar_cambios).pack(pady=10)
    
    def eliminar_material_inventario(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        item = seleccion[0]
        item_data = self.tree_inventario.item(item)
        valores = item_data['values']
        nombre = valores[0]
        
        if nombre.startswith("=== TOTALES"):
            messagebox.showwarning("Error", "No puede eliminar la fila de totales")
            return
        
        datos = self.inventario.get(nombre, {})
        if messagebox.askyesno("Confirmar", 
            f"⚠️ ¿Eliminar el material '{nombre}' del inventario?\n\n"
            f"📊 Stock actual: {datos.get('stock', 0):.2f} kg\n"
            f"💰 Inversión total: ${datos.get('inversion_total', 0):.2f}\n"
            f"📦 Total comprado: {datos.get('total_comprado', 0):.2f} kg\n\n"
            f"Esta acción no se puede deshacer."):
            if nombre in self.inventario:
                del self.inventario[nombre]
                self.guardar_datos()
                self.actualizar_tabla_inventario()
                self.actualizar_lista_venta()
                self.cargar_materiales_pos_venta()
                messagebox.showinfo("Éxito", "Material eliminado del inventario")
    
    def aumentar_stock_inventario(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        item = seleccion[0]
        item_data = self.tree_inventario.item(item)
        valores = item_data['values']
        nombre = valores[0]
        
        if nombre.startswith("=== TOTALES"):
            messagebox.showwarning("Error", "No puede modificar la fila de totales")
            return
        
        if nombre not in self.inventario:
            messagebox.showwarning("Error", "Material no encontrado")
            return
        
        stock_actual = self.inventario[nombre]["stock"]
        precio_compra = self.inventario[nombre]["precio_compra_cliente"]
        
        if precio_compra == 0:
            precio_venta = self.inventario[nombre]["precio_venta"]
            precio_compra = self.calcular_precio_cliente(nombre, precio_venta)
        
        cantidad = simpledialog.askfloat("Aumentar Stock", 
            f"📦 Material: {nombre}\n"
            f"📊 Stock actual: {stock_actual:.2f} kg\n"
            f"💰 Precio compra: ${precio_compra:.2f}/kg\n"
            f"💰 Ganancia para cliente: ${self.calcular_ganancia(nombre, precio_compra):.2f}/kg\n\n"
            f"¿Cuántos kg quiere agregar?",
            minvalue=0.01)
        
        if cantidad and cantidad > 0:
            cantidad = self.redondear(cantidad)
            stock_anterior = self.inventario[nombre]["stock"]
            costo_compra = self.redondear(cantidad * precio_compra)
            
            self.inventario[nombre]["stock"] = self.redondear(stock_anterior + cantidad)
            
            if stock_anterior == 0:
                self.inventario[nombre]["inversion_total"] = costo_compra
                self.inventario[nombre]["inversion_promedio"] = self.redondear(precio_compra)
                self.inventario[nombre]["total_comprado"] = cantidad
            else:
                inversion_anterior = self.inventario[nombre].get("inversion_total", 0)
                total_comprado_anterior = self.inventario[nombre].get("total_comprado", 0)
                
                nueva_inversion = self.redondear(inversion_anterior + costo_compra)
                nuevo_total_comprado = self.redondear(total_comprado_anterior + cantidad)
                
                self.inventario[nombre]["inversion_total"] = nueva_inversion
                self.inventario[nombre]["total_comprado"] = nuevo_total_comprado
                
                if nuevo_total_comprado > 0:
                    costo_promedio = self.redondear(nueva_inversion / nuevo_total_comprado)
                    self.inventario[nombre]["inversion_promedio"] = costo_promedio
            
            nuevo_id = max([c.get('id', 0) for c in self.compras] + [c.get('id', 0) for c in self.compras_mayoreo]) + 1 if (self.compras or self.compras_mayoreo) else 1
            compra = {
                "id": nuevo_id,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cliente": "COMPRA_DIRECTA_INVENTARIO",
                "seccion": self.inventario[nombre]["seccion"],
                "material": nombre,
                "cantidad": cantidad,
                "precio_unitario": self.redondear(precio_compra),
                "total": costo_compra,
                "tipo_precio": "compra_inventario",
                "procesada_inventario": True
            }
            self.compras.append(compra)
            
            self.caja_general = self.redondear(self.caja_general - costo_compra)
            self.registrar_movimiento_caja("egreso", f"Compra stock - {nombre}", costo_compra)
            
            remision_id = max([r.get('id', 0) for r in self.remisiones_generadas]) + 1 if self.remisiones_generadas else 1
            remision = {
                "id": remision_id,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cliente": "COMPRA DIRECTA",
                "usuario": self.usuario_actual,
                "items": [{
                    "material": nombre,
                    "cantidad": cantidad,
                    "precio": precio_compra,
                    "total": costo_compra,
                    "seccion": self.inventario[nombre]["seccion"]
                }],
                "total": costo_compra,
                "tipo": "compra"
            }
            
            qr_base64 = self.generar_qr_remision(remision)
            remision["qr_base64"] = qr_base64
            self.remisiones_generadas.append(remision)
            
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.actualizar_metricas()
            self.cargar_materiales_pos_venta()
            
            self.enviar_correo_remision_completa("COMPRA DIRECTA", remision_id, remision["fecha"], remision["items"], costo_compra, es_venta=False)
            
            nuevo_costo_promedio = self.inventario[nombre]["inversion_promedio"]
            nuevo_stock = self.inventario[nombre]["stock"]
            nuevo_precio = self.inventario[nombre]["precio_venta"]
            nueva_ganancia = self.redondear(nuevo_stock * self.calcular_ganancia(nombre, nuevo_precio))
            
            messagebox.showinfo("Éxito", 
                f"✅ Stock aumentado exitosamente\n\n"
                f"📦 Material: {nombre}\n"
                f"📊 Stock anterior: {stock_anterior:.2f} kg\n"
                f"➕ Agregado: {cantidad:.2f} kg\n"
                f"📊 Stock actual: {self.inventario[nombre]['stock']:.2f} kg\n"
                f"💰 Costo: ${costo_compra:.2f}\n"
                f"💰 Inversión total: ${self.inventario[nombre]['inversion_total']:.2f}\n"
                f"💰 Ganancia potencial: ${nueva_ganancia:.2f}\n"
                f"📋 Remisión generada: #{remision_id}")
    
    def reducir_stock_inventario(self):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        item = seleccion[0]
        item_data = self.tree_inventario.item(item)
        valores = item_data['values']
        nombre = valores[0]
        
        if nombre.startswith("=== TOTALES"):
            messagebox.showwarning("Error", "No puede modificar la fila de totales")
            return
        
        if nombre not in self.inventario:
            messagebox.showwarning("Error", "Material no encontrado")
            return
        
        stock_actual = self.inventario[nombre]["stock"]
        if stock_actual <= 0:
            messagebox.showwarning("Error", f"El material '{nombre}' no tiene stock disponible")
            return
        
        cantidad = simpledialog.askfloat("Reducir Stock", 
            f"📦 Material: {nombre}\n"
            f"📊 Stock actual: {stock_actual:.2f} kg\n\n"
            f"¿Cuántos kg quiere reducir?",
            minvalue=0.01, maxvalue=stock_actual)
        
        if cantidad and cantidad > 0:
            cantidad = self.redondear(cantidad)
            stock_anterior = self.inventario[nombre]["stock"]
            nuevo_stock = self.redondear(stock_anterior - cantidad)
            self.inventario[nombre]["stock"] = nuevo_stock
            
            if nuevo_stock == 0:
                self.inventario[nombre]["inversion_total"] = 0
                self.inventario[nombre]["inversion_promedio"] = 0
                
                if messagebox.askyesno("Stock Agotado", 
                    f"⚠️ El material '{nombre}' se ha agotado.\n\n"
                    f"Stock restante: 0.00 kg\n"
                    f"Inversión reseteada a: $0.00\n\n"
                    f"¿Desea eliminarlo del inventario?"):
                    del self.inventario[nombre]
            
            self.guardar_datos()
            self.actualizar_tabla_inventario()
            self.cargar_materiales_pos_venta()
            
            messagebox.showinfo("Éxito", 
                f"✅ Stock reducido exitosamente\n\n"
                f"📦 Material: {nombre}\n"
                f"📊 Stock anterior: {stock_anterior:.2f} kg\n"
                f"➖ Reducido: {cantidad:.2f} kg\n"
                f"📊 Stock actual: {nuevo_stock:.2f} kg")
    
    def verificar_stock_material(self, material):
        if material in self.inventario:
            return self.inventario[material].get("stock", 0)
        return 0
    
    # ==================== TAB REMISIONES GUARDADAS ====================
    
    def crear_tab_remisiones_guardadas(self):
        frame_filtros = ttk.Frame(self.tab_remisiones)
        frame_filtros.pack(pady=5, padx=8, fill='x')
        
        ttk.Label(frame_filtros, text="Filtrar por tipo:").pack(side='left', padx=5)
        self.remisiones_tipo_combo = ttk.Combobox(frame_filtros, 
            values=["Todas", "remision", "venta", "compra"], 
            width=15)
        self.remisiones_tipo_combo.set("Todas")
        self.remisiones_tipo_combo.bind('<<ComboboxSelected>>', self.filtrar_remisiones)
        
        self.seleccionar_todos_remisiones = tk.BooleanVar(value=False)
        chk_todos_rem = ttk.Checkbutton(frame_filtros, text="☑️ Seleccionar Todos", 
                                       variable=self.seleccionar_todos_remisiones,
                                       command=self.toggle_seleccion_todos_remisiones)
        chk_todos_rem.pack(side='left', padx=5)
        
        ttk.Button(frame_filtros, text="🔄 Actualizar", command=self.actualizar_lista_remisiones).pack(side='left', padx=5)
        ttk.Button(frame_filtros, text="📥 Descargar Seleccionada", command=self.descargar_remision_seleccionada).pack(side='left', padx=5)
        ttk.Button(frame_filtros, text="🗑️ Borrar Seleccionadas", command=self.eliminar_remisiones_seleccionadas).pack(side='left', padx=5)
        
        frame_tabla = ttk.LabelFrame(self.tab_remisiones, text="📋 Remisiones Generadas")
        frame_tabla.pack(pady=5, padx=8, fill='both', expand=True)
        
        self.tree_remisiones = ttk.Treeview(frame_tabla, 
            columns=("ID", "Fecha", "Cliente", "Tipo", "Items", "Total", "Ganancia"), 
            show='headings', height=15)
        self.tree_remisiones.heading("ID", text="ID")
        self.tree_remisiones.heading("Fecha", text="Fecha")
        self.tree_remisiones.heading("Cliente", text="Cliente")
        self.tree_remisiones.heading("Tipo", text="Tipo")
        self.tree_remisiones.heading("Items", text="Items")
        self.tree_remisiones.heading("Total", text="Total ($)")
        self.tree_remisiones.heading("Ganancia", text="Ganancia")
        
        self.tree_remisiones.column("ID", width=60)
        self.tree_remisiones.column("Fecha", width=150)
        self.tree_remisiones.column("Cliente", width=150)
        self.tree_remisiones.column("Tipo", width=80)
        self.tree_remisiones.column("Items", width=80)
        self.tree_remisiones.column("Total", width=100)
        self.tree_remisiones.column("Ganancia", width=100)
        self.tree_remisiones.pack(fill='both', expand=True)
        
        self.tree_remisiones.bind('<<TreeviewSelect>>', self.on_remision_seleccionado)
        
        self.actualizar_lista_remisiones()
    
    def on_remision_seleccionado(self, event):
        pass
    
    def toggle_seleccion_todos_remisiones(self):
        seleccionar = self.seleccionar_todos_remisiones.get()
        for item in self.tree_remisiones.get_children():
            if seleccionar:
                self.tree_remisiones.selection_add(item)
            else:
                self.tree_remisiones.selection_remove(item)
    
    def eliminar_remisiones_seleccionadas(self):
        seleccion = self.tree_remisiones.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos una remisión para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(seleccion)} remisión(es) seleccionada(s)?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        remisiones_a_eliminar = []
        for item in seleccion:
            valores = self.tree_remisiones.item(item)['values']
            remision_id = int(valores[0])
            remisiones_a_eliminar.append(remision_id)
        
        for remision_id in remisiones_a_eliminar:
            remision = None
            for r in self.remisiones_generadas:
                if r.get('id') == remision_id:
                    remision = r
                    break
            
            if remision:
                tipo = remision.get('tipo', 'remision')
                afecta_caja = tipo in ['venta', 'compra']
                
                if afecta_caja:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d")
                    if fecha_actual in self.caja_diaria:
                        registro = self.caja_diaria[fecha_actual]
                        movimientos_originales = registro.get("movimientos", [])
                        
                        movimientos_a_eliminar = []
                        for mov in movimientos_originales:
                            concepto = mov.get("concepto", "")
                            if tipo == 'venta' and f"Venta remisión #{remision_id}" in concepto:
                                movimientos_a_eliminar.append(mov)
                            elif tipo == 'compra' and f"Compra remisión #{remision_id}" in concepto:
                                movimientos_a_eliminar.append(mov)
                        
                        if movimientos_a_eliminar:
                            for mov in movimientos_a_eliminar:
                                monto = mov.get("monto", 0)
                                tipo_mov = mov.get("tipo", "")
                                
                                if tipo_mov == "ingreso":
                                    registro["total_ingresos"] = self.redondear(registro.get("total_ingresos", 0) - monto)
                                else:
                                    registro["total_egresos"] = self.redondear(registro.get("total_egresos", 0) - monto)
                                
                                if tipo_mov == "ingreso":
                                    self.caja_general = self.redondear(self.caja_general - monto)
                                else:
                                    self.caja_general = self.redondear(self.caja_general + monto)
                            
                            registro["movimientos"] = [m for m in movimientos_originales if m not in movimientos_a_eliminar]
                            self.guardar_caja_diaria()
        
        self.remisiones_generadas = [r for r in self.remisiones_generadas if r.get('id') not in remisiones_a_eliminar]
        self.compras = [c for c in self.compras if c.get('remision_id') not in remisiones_a_eliminar]
        self.compras_mayoreo = [c for c in self.compras_mayoreo if c.get('remision_id') not in remisiones_a_eliminar]
        
        self.guardar_datos()
        self.actualizar_lista_remisiones()
        self.actualizar_historial()
        self.actualizar_metricas()
        self.actualizar_tabla_inventario()
        
        if hasattr(self, 'tree_remisiones_guardadas'):
            self.actualizar_remisiones_guardadas()
        
        self.seleccionar_todos_remisiones.set(False)
        messagebox.showinfo("Éxito", f"✅ {len(remisiones_a_eliminar)} remisión(es) eliminada(s) correctamente")
    
    def actualizar_lista_remisiones(self):
        for item in self.tree_remisiones.get_children():
            self.tree_remisiones.delete(item)
        
        for remision in sorted(self.remisiones_generadas, key=lambda x: x.get('id', 0), reverse=True):
            tipo = remision.get('tipo', 'remision')
            tipo_mostrar = {
                'remision': '📋 Remisión',
                'venta': '🛒 Venta',
                'compra': '📦 Compra'
            }.get(tipo, '📋 Remisión')
            
            ganancia_total = 0
            for item in remision.get('items', []):
                ganancia_total += item.get('ganancia', 0)
            ganancia_total = self.redondear(ganancia_total)
            
            self.tree_remisiones.insert("", "end", values=(
                remision.get('id', ''),
                remision.get('fecha', '')[:16],
                remision.get('cliente', ''),
                tipo_mostrar,
                len(remision.get('items', [])),
                f"{remision.get('total', 0):.2f}",
                f"{ganancia_total:.2f}" if ganancia_total > 0 else "0.00"
            ))
        
        self.seleccionar_todos_remisiones.set(False)
    
    def filtrar_remisiones(self, event=None):
        tipo_filtro = self.remisiones_tipo_combo.get()
        
        for item in self.tree_remisiones.get_children():
            valores = self.tree_remisiones.item(item)['values']
            tipo_item = valores[3] if len(valores) > 3 else ''
            
            if tipo_filtro == "Todas":
                self.tree_remisiones.item(item, tags=('visible',))
            else:
                tipo_buscar = {
                    'remision': '📋 Remisión',
                    'venta': '🛒 Venta',
                    'compra': '📦 Compra'
                }.get(tipo_filtro, '')
                
                if tipo_item == tipo_buscar:
                    self.tree_remisiones.item(item, tags=('visible',))
                else:
                    self.tree_remisiones.item(item, tags=('oculto',))
        
        for item in self.tree_remisiones.get_children():
            tags = self.tree_remisiones.item(item)['tags']
            if 'oculto' in tags:
                self.tree_remisiones.detach(item)
            else:
                self.tree_remisiones.reattach(item, '', 'end')
        
        self.seleccionar_todos_remisiones.set(False)
    
    def descargar_remision_seleccionada(self):
        seleccion = self.tree_remisiones.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una remisión para descargar")
            return
        
        item = seleccion[0]
        item_data = self.tree_remisiones.item(item)
        valores = item_data['values']
        remision_id = int(valores[0])
        
        self.descargar_remision(remision_id)
    
    def mostrar_remisiones_guardadas(self):
        ventana = tk.Toplevel(self.root)
        ventana.title("📋 Remisiones Guardadas")
        ventana.geometry("800x400")
        ventana.transient(self.root)
        
        frame = ttk.Frame(ventana)
        frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tree_remisiones_guardadas = ttk.Treeview(frame, 
            columns=("ID", "Fecha", "Cliente", "Tipo", "Total", "Ganancia"), 
            show='headings', height=15)
        self.tree_remisiones_guardadas.heading("ID", text="ID")
        self.tree_remisiones_guardadas.heading("Fecha", text="Fecha")
        self.tree_remisiones_guardadas.heading("Cliente", text="Cliente")
        self.tree_remisiones_guardadas.heading("Tipo", text="Tipo")
        self.tree_remisiones_guardadas.heading("Total", text="Total ($)")
        self.tree_remisiones_guardadas.heading("Ganancia", text="Ganancia")
        
        self.tree_remisiones_guardadas.column("ID", width=60)
        self.tree_remisiones_guardadas.column("Fecha", width=150)
        self.tree_remisiones_guardadas.column("Cliente", width=150)
        self.tree_remisiones_guardadas.column("Tipo", width=80)
        self.tree_remisiones_guardadas.column("Total", width=100)
        self.tree_remisiones_guardadas.column("Ganancia", width=100)
        self.tree_remisiones_guardadas.pack(fill='both', expand=True)
        
        self.actualizar_remisiones_guardadas()
        
        frame_botones = ttk.Frame(ventana)
        frame_botones.pack(pady=5)
        
        self.seleccionar_todos_remisiones_guardadas = tk.BooleanVar(value=False)
        chk_todos_guard = ttk.Checkbutton(frame_botones, text="☑️ Seleccionar Todos", 
                                         variable=self.seleccionar_todos_remisiones_guardadas,
                                         command=self.toggle_seleccion_todos_remisiones_guardadas)
        chk_todos_guard.pack(side='left', padx=5)
        
        ttk.Button(frame_botones, text="📥 Descargar Seleccionada", 
                  command=self.descargar_remision_guardada_seleccionada).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🗑️ Eliminar Seleccionadas", 
                  command=self.eliminar_remisiones_guardadas_seleccionadas).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🔄 Actualizar", 
                  command=self.actualizar_remisiones_guardadas).pack(side='left', padx=5)
    
    def toggle_seleccion_todos_remisiones_guardadas(self):
        seleccionar = self.seleccionar_todos_remisiones_guardadas.get()
        for item in self.tree_remisiones_guardadas.get_children():
            if seleccionar:
                self.tree_remisiones_guardadas.selection_add(item)
            else:
                self.tree_remisiones_guardadas.selection_remove(item)
    
    def descargar_remision_guardada_seleccionada(self):
        seleccion = self.tree_remisiones_guardadas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una remisión para descargar")
            return
        
        item = seleccion[0]
        item_data = self.tree_remisiones_guardadas.item(item)
        valores = item_data['values']
        remision_id = int(valores[0])
        self.descargar_remision(remision_id)
    
    def eliminar_remisiones_guardadas_seleccionadas(self):
        seleccion = self.tree_remisiones_guardadas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos una remisión para eliminar")
            return
        
        remisiones_a_eliminar = []
        for item in seleccion:
            valores = self.tree_remisiones_guardadas.item(item)['values']
            remision_id = int(valores[0])
            remisiones_a_eliminar.append(remision_id)
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(remisiones_a_eliminar)} remisión(es) seleccionada(s)?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        for remision_id in remisiones_a_eliminar:
            self.remisiones_generadas = [r for r in self.remisiones_generadas if r.get('id') != remision_id]
            self.compras = [c for c in self.compras if c.get('remision_id') != remision_id]
            self.compras_mayoreo = [c for c in self.compras_mayoreo if c.get('remision_id') != remision_id]
        
        self.guardar_datos()
        self.actualizar_remisiones_guardadas()
        self.actualizar_lista_remisiones()
        self.actualizar_historial()
        self.actualizar_metricas()
        
        self.seleccionar_todos_remisiones_guardadas.set(False)
        messagebox.showinfo("Éxito", f"✅ {len(remisiones_a_eliminar)} remisión(es) eliminada(s) correctamente")
    
    def actualizar_remisiones_guardadas(self):
        if not hasattr(self, 'tree_remisiones_guardadas'):
            return
        
        for item in self.tree_remisiones_guardadas.get_children():
            self.tree_remisiones_guardadas.delete(item)
        
        for remision in sorted(self.remisiones_generadas, key=lambda x: x.get('id', 0), reverse=True):
            tipo = remision.get('tipo', 'remision')
            tipo_mostrar = {
                'remision': '📋 Remisión',
                'venta': '🛒 Venta',
                'compra': '📦 Compra'
            }.get(tipo, '📋 Remisión')
            
            ganancia_total = 0
            for item in remision.get('items', []):
                ganancia_total += item.get('ganancia', 0)
            ganancia_total = self.redondear(ganancia_total)
            
            self.tree_remisiones_guardadas.insert("", "end", values=(
                remision.get('id', ''),
                remision.get('fecha', '')[:16],
                remision.get('cliente', ''),
                tipo_mostrar,
                f"{remision.get('total', 0):.2f}",
                f"{ganancia_total:.2f}" if ganancia_total > 0 else "0.00"
            ))
        
        self.seleccionar_todos_remisiones_guardadas.set(False)
    
    # ==================== TAB CAJA ====================
    
    def crear_tab_caja(self):
        frame_info = ttk.LabelFrame(self.tab_caja, text="📊 Estado de Caja")
        frame_info.pack(pady=8, padx=8, fill='x')
        
        self.label_estado_caja = ttk.Label(frame_info, text="Estado: 🔒 Cerrada", font=("Arial", 11, "bold"))
        self.label_estado_caja.grid(row=0, column=0, padx=15, pady=5)
        
        self.label_apertura_caja = ttk.Label(frame_info, text="Apertura: $0.00", font=("Arial", 11))
        self.label_apertura_caja.grid(row=0, column=1, padx=15, pady=5)
        
        self.label_ingresos_caja = ttk.Label(frame_info, text="Ingresos: $0.00", font=("Arial", 11), foreground="green")
        self.label_ingresos_caja.grid(row=0, column=2, padx=15, pady=5)
        
        self.label_egresos_caja = ttk.Label(frame_info, text="Egresos: $0.00", font=("Arial", 11), foreground="red")
        self.label_egresos_caja.grid(row=0, column=3, padx=15, pady=5)
        
        self.label_saldo_caja = ttk.Label(frame_info, text="Saldo: $0.00", font=("Arial", 11, "bold"), foreground="blue")
        self.label_saldo_caja.grid(row=0, column=4, padx=15, pady=5)
        
        frame_botones = ttk.Frame(self.tab_caja)
        frame_botones.pack(pady=8, padx=8, fill='x')
        
        ttk.Button(frame_botones, text="🔓 Abrir Caja", command=self.abrir_caja).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🔒 Cerrar Caja", command=self.cerrar_caja).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🔄 Actualizar", command=self.actualizar_info_caja).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="📋 Actualizar desde Remisión", command=self.actualizar_caja_desde_remision).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🗑️ Borrar Movimiento Seleccionado", command=self.borrar_movimiento_seleccionado).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🗑️ Borrar Todos los Movimientos", command=self.borrar_todos_movimientos_dia).pack(side='left', padx=5)
        
        frame_movimientos = ttk.LabelFrame(self.tab_caja, text="📋 Movimientos del Día")
        frame_movimientos.pack(pady=8, padx=8, fill='both', expand=True)
        
        self.tree_movimientos = ttk.Treeview(frame_movimientos, columns=("Hora", "Tipo", "Concepto", "Monto", "Usuario"), show='headings', height=10)
        self.tree_movimientos.heading("Hora", text="Hora")
        self.tree_movimientos.heading("Tipo", text="Tipo")
        self.tree_movimientos.heading("Concepto", text="Concepto")
        self.tree_movimientos.heading("Monto", text="Monto ($)")
        self.tree_movimientos.heading("Usuario", text="Usuario")
        
        self.tree_movimientos.column("Hora", width=80)
        self.tree_movimientos.column("Tipo", width=80)
        self.tree_movimientos.column("Concepto", width=250)
        self.tree_movimientos.column("Monto", width=100)
        self.tree_movimientos.column("Usuario", width=100)
        self.tree_movimientos.pack(fill='both', expand=True, padx=5, pady=5)
        
        frame_historial = ttk.LabelFrame(self.tab_caja, text="📊 Historial de Caja")
        frame_historial.pack(pady=8, padx=8, fill='x')
        
        self.tree_historial_caja = ttk.Treeview(frame_historial, columns=("Fecha", "Apertura", "Cierre", "Ingresos", "Egresos", "Saldo", "Usuario"), show='headings', height=5)
        self.tree_historial_caja.heading("Fecha", text="Fecha")
        self.tree_historial_caja.heading("Apertura", text="Apertura ($)")
        self.tree_historial_caja.heading("Cierre", text="Cierre ($)")
        self.tree_historial_caja.heading("Ingresos", text="Ingresos ($)")
        self.tree_historial_caja.heading("Egresos", text="Egresos ($)")
        self.tree_historial_caja.heading("Saldo", text="Saldo ($)")
        self.tree_historial_caja.heading("Usuario", text="Usuario")
        
        self.tree_historial_caja.column("Fecha", width=100)
        self.tree_historial_caja.column("Apertura", width=90)
        self.tree_historial_caja.column("Cierre", width=90)
        self.tree_historial_caja.column("Ingresos", width=90)
        self.tree_historial_caja.column("Egresos", width=90)
        self.tree_historial_caja.column("Saldo", width=90)
        self.tree_historial_caja.column("Usuario", width=100)
        self.tree_historial_caja.pack(fill='x', padx=5, pady=5)
        
        self.actualizar_info_caja()
        self.actualizar_historial_caja()
    
    # ==================== BORRAR TODOS LOS MOVIMIENTOS DEL DÍA ====================
    
    def borrar_todos_movimientos_dia(self):
        try:
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            
            if fecha_actual not in self.caja_diaria:
                messagebox.showwarning("Caja", "No hay una caja abierta para hoy.")
                return
            
            registro = self.caja_diaria[fecha_actual]
            
            if not registro.get("abierta", False):
                messagebox.showwarning("Caja", "La caja ya está cerrada. No se pueden borrar movimientos.")
                return
            
            movimientos = registro.get("movimientos", [])
            
            if not movimientos:
                messagebox.showinfo("Caja", "No hay movimientos registrados para hoy.")
                return
            
            total_ingresos_borrar = registro.get("total_ingresos", 0)
            total_egresos_borrar = registro.get("total_egresos", 0)
            
            mensaje = f"⚠️ ¿BORRAR TODOS LOS MOVIMIENTOS DEL DÍA?\n\n"
            mensaje += f"📅 Fecha: {fecha_actual}\n"
            mensaje += f"📋 Movimientos a eliminar: {len(movimientos)}\n"
            mensaje += f"💰 Ingresos a revertir: ${total_ingresos_borrar:.2f}\n"
            mensaje += f"💰 Egresos a revertir: ${total_egresos_borrar:.2f}\n"
            mensaje += f"💰 Saldo actual en caja: ${self.caja_general:.2f}\n\n"
            
            mensaje += f"📋 Movimientos a eliminar:\n"
            for mov in movimientos[:10]:
                tipo_icono = "💰" if mov.get("tipo") == "ingreso" else "💸"
                mensaje += f"   {tipo_icono} {mov.get('hora')} - {mov.get('concepto')} - ${mov.get('monto', 0):.2f}\n"
            if len(movimientos) > 10:
                mensaje += f"   ... y {len(movimientos) - 10} movimientos más\n"
            
            mensaje += f"\n💰 Saldo después de borrar: ${self.caja_general - total_ingresos_borrar + total_egresos_borrar:.2f}\n\n"
            mensaje += f"⚠️ Esta acción NO se puede deshacer.\n"
            mensaje += f"¿Está seguro de continuar?"
            
            if not messagebox.askyesno("Confirmar Borrado", mensaje):
                return
            
            password = simpledialog.askstring("Confirmación de Seguridad", 
                "Ingrese la contraseña de administrador para confirmar:", 
                show="•")
            
            if password != "admin123":
                messagebox.showerror("Error", "Contraseña incorrecta. Operación cancelada.")
                return
            
            self.caja_general = self.redondear(self.caja_general - total_ingresos_borrar + total_egresos_borrar)
            
            registro["movimientos"] = []
            registro["total_ingresos"] = 0
            registro["total_egresos"] = 0
            
            self.guardar_caja_diaria()
            self.guardar_datos()
            
            self.actualizar_info_caja()
            self.actualizar_movimientos_caja()
            self.actualizar_historial_caja()
            self.actualizar_metricas()
            
            messagebox.showinfo("Éxito", 
                f"✅ Movimientos del día eliminados correctamente.\n\n"
                f"📋 Movimientos eliminados: {len(movimientos)}\n"
                f"💰 Ingresos revertidos: ${total_ingresos_borrar:.2f}\n"
                f"💰 Egresos revertidos: ${total_egresos_borrar:.2f}\n"
                f"💰 Saldo actual en caja: ${self.caja_general:.2f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al borrar movimientos:\n{str(e)}")
    
    # ==================== TAB VENTA INVENTARIO ====================
    
    def crear_tab_venta_inventario(self):
        frame_nueva_venta = ttk.LabelFrame(self.tab_venta_inventario, text="🛒 Registrar Nueva Venta")
        frame_nueva_venta.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_nueva_venta, text="Cliente:").grid(row=0, column=0, padx=4, pady=4)
        self.venta_cliente_combo = ttk.Combobox(frame_nueva_venta, values=[c['nombre'] for c in self.clientes], width=25)
        self.venta_cliente_combo.grid(row=0, column=1, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Material:").grid(row=0, column=2, padx=4, pady=4)
        self.venta_material_combo = ttk.Combobox(frame_nueva_venta, width=25)
        self.venta_material_combo.grid(row=0, column=3, padx=4, pady=4)
        self.venta_material_combo.bind('<<ComboboxSelected>>', self.actualizar_info_venta)
        
        ttk.Label(frame_nueva_venta, text="Cantidad (kg):").grid(row=1, column=0, padx=4, pady=4)
        self.venta_cantidad_entry = ttk.Entry(frame_nueva_venta, width=15)
        self.venta_cantidad_entry.grid(row=1, column=1, padx=4, pady=4)
        self.venta_cantidad_entry.bind('<KeyRelease>', self.actualizar_total_venta)
        
        self.label_stock_info = ttk.Label(frame_nueva_venta, text="", font=("Arial", 9))
        self.label_stock_info.grid(row=1, column=2, columnspan=2, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Precio Venta:").grid(row=2, column=0, padx=4, pady=4)
        self.label_precio_venta_mostrar = ttk.Label(frame_nueva_venta, text="$0.00/kg", font=("Arial", 10, "bold"), foreground="green")
        self.label_precio_venta_mostrar.grid(row=2, column=1, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Precio Cliente:").grid(row=2, column=2, padx=4, pady=4)
        self.label_precio_cliente_mostrar = ttk.Label(frame_nueva_venta, text="$0.00/kg", font=("Arial", 10, "bold"), foreground="blue")
        self.label_precio_cliente_mostrar.grid(row=2, column=3, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Ganancia:").grid(row=3, column=0, padx=4, pady=4)
        self.label_ganancia_mostrar = ttk.Label(frame_nueva_venta, text="$0.00/kg", font=("Arial", 10, "bold"), foreground="red")
        self.label_ganancia_mostrar.grid(row=3, column=1, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Total Venta:").grid(row=3, column=2, padx=4, pady=4)
        self.label_total_venta = ttk.Label(frame_nueva_venta, text="$0.00", font=("Arial", 12, "bold"), foreground="blue")
        self.label_total_venta.grid(row=3, column=3, padx=4, pady=4)
        
        ttk.Label(frame_nueva_venta, text="Distribución:").grid(row=4, column=0, padx=4, pady=4)
        self.label_distribucion = ttk.Label(frame_nueva_venta, text="", font=("Arial", 9))
        self.label_distribucion.grid(row=4, column=1, columnspan=3, padx=4, pady=4, sticky='w')
        
        ttk.Button(frame_nueva_venta, text="✅ Registrar Venta", command=self.registrar_venta_inventario).grid(row=5, column=0, columnspan=4, pady=10)
        
        frame_lista_ventas = ttk.LabelFrame(self.tab_venta_inventario, text="📜 Historial de Ventas")
        frame_lista_ventas.pack(pady=8, padx=8, fill='both', expand=True)
        
        self.tree_ventas = ttk.Treeview(frame_lista_ventas, 
            columns=("ID", "Fecha", "Cliente", "Material", "Cantidad", "Precio", "Precio Cliente", "Ganancia", "Total", "Stock Anterior", "Stock Actual"), 
            show='headings', height=10)
        self.tree_ventas.heading("ID", text="ID")
        self.tree_ventas.heading("Fecha", text="Fecha")
        self.tree_ventas.heading("Cliente", text="Cliente")
        self.tree_ventas.heading("Material", text="Material")
        self.tree_ventas.heading("Cantidad", text="Cantidad (kg)")
        self.tree_ventas.heading("Precio", text="Precio ($/kg)")
        self.tree_ventas.heading("Precio Cliente", text="Precio Cliente ($/kg)")
        self.tree_ventas.heading("Ganancia", text="Ganancia")
        self.tree_ventas.heading("Total", text="Total ($)")
        self.tree_ventas.heading("Stock Anterior", text="Stock Anterior (kg)")
        self.tree_ventas.heading("Stock Actual", text="Stock Actual (kg)")
        
        self.tree_ventas.column("ID", width=40)
        self.tree_ventas.column("Fecha", width=120)
        self.tree_ventas.column("Cliente", width=100)
        self.tree_ventas.column("Material", width=120)
        self.tree_ventas.column("Cantidad", width=70)
        self.tree_ventas.column("Precio", width=70)
        self.tree_ventas.column("Precio Cliente", width=90)
        self.tree_ventas.column("Ganancia", width=80)
        self.tree_ventas.column("Total", width=80)
        self.tree_ventas.column("Stock Anterior", width=90)
        self.tree_ventas.column("Stock Actual", width=90)
        self.tree_ventas.pack(fill='both', expand=True)
        
        frame_botones_ventas = ttk.Frame(self.tab_venta_inventario)
        frame_botones_ventas.pack(pady=8, fill='x')
        
        self.seleccionar_todos_ventas = tk.BooleanVar(value=False)
        chk_todos_ventas = ttk.Checkbutton(frame_botones_ventas, text="☑️ Seleccionar Todos", 
                                          variable=self.seleccionar_todos_ventas,
                                          command=self.toggle_seleccion_todos_ventas)
        chk_todos_ventas.pack(side='left', padx=5)
        
        ttk.Button(frame_botones_ventas, text="✏️ Editar Venta", command=self.editar_venta).pack(side='left', padx=5)
        ttk.Button(frame_botones_ventas, text="🗑️ Eliminar Seleccionadas", command=self.eliminar_ventas_seleccionadas).pack(side='left', padx=5)
        ttk.Button(frame_botones_ventas, text="🔄 Actualizar Lista", command=self.actualizar_lista_ventas).pack(side='left', padx=5)
        ttk.Button(frame_botones_ventas, text="📋 Ver Remisiones", command=self.mostrar_remisiones_guardadas).pack(side='left', padx=5)
        
        self.tree_ventas.bind('<<TreeviewSelect>>', self.on_venta_seleccionado)
        
        self.actualizar_lista_venta()
        self.actualizar_lista_ventas()
    
    def on_venta_seleccionado(self, event):
        pass
    
    def toggle_seleccion_todos_ventas(self):
        seleccionar = self.seleccionar_todos_ventas.get()
        for item in self.tree_ventas.get_children():
            if seleccionar:
                self.tree_ventas.selection_add(item)
            else:
                self.tree_ventas.selection_remove(item)
    
    def eliminar_ventas_seleccionadas(self):
        seleccion = self.tree_ventas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos una venta para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(seleccion)} venta(s) seleccionada(s)?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        ventas_a_eliminar = []
        for item in seleccion:
            valores = self.tree_ventas.item(item)['values']
            venta_id = int(valores[0])
            ventas_a_eliminar.append(venta_id)
        
        self.ventas = [v for v in self.ventas if v.get('id') not in ventas_a_eliminar]
        self.compras = [c for c in self.compras if not (c.get('id') in ventas_a_eliminar and c.get('tipo_precio') == 'venta_inventario')]
        
        self.guardar_datos()
        self.actualizar_lista_ventas()
        self.seleccionar_todos_ventas.set(False)
        messagebox.showinfo("Éxito", f"✅ {len(ventas_a_eliminar)} venta(s) eliminada(s) correctamente")
    
    def actualizar_lista_venta(self):
        materiales_con_stock = [m for m, d in self.inventario.items() if d["stock"] > 0 and d.get("precio_venta", 0) > 0]
        self.venta_material_combo['values'] = materiales_con_stock
        if not materiales_con_stock:
            self.venta_material_combo.set('')
            self.label_stock_info.config(text="⚠️ No hay materiales con stock disponible", foreground="red")
    
    def actualizar_info_venta(self, event=None):
        material = self.venta_material_combo.get()
        if material and material in self.inventario:
            datos = self.inventario[material]
            stock = datos.get("stock", 0)
            precio = datos.get("precio_venta", 0)
            precio_cliente = self.calcular_precio_cliente(material, precio)
            ganancia_por_kg = self.calcular_ganancia(material, precio)
            porcentaje = self.obtener_porcentaje_ganancia(material) * 100
            
            if stock > 0:
                self.label_stock_info.config(
                    text=f"✅ Stock disponible: {stock:.2f} kg", 
                    foreground="darkgreen"
                )
            else:
                self.label_stock_info.config(
                    text=f"⚠️ Stock agotado: 0.00 kg", 
                    foreground="red"
                )
            
            self.label_precio_venta_mostrar.config(text=f"${precio:.2f}/kg")
            self.label_precio_cliente_mostrar.config(text=f"${precio_cliente:.2f}/kg")
            self.label_ganancia_mostrar.config(
                text=f"${ganancia_por_kg:.2f}/kg ({porcentaje:.1f}%)",
                foreground="red" if porcentaje == 5 else "green"
            )
            
            self.venta_cantidad_entry.delete(0, tk.END)
            self.label_total_venta.config(text="$0.00")
            self.label_distribucion.config(text="")
            
            if stock <= 0:
                self.venta_cantidad_entry.config(state='disabled')
                self.label_total_venta.config(text="⚠️ Sin stock", foreground="red")
            else:
                self.venta_cantidad_entry.config(state='normal')
        else:
            self.label_stock_info.config(text="Material no encontrado", foreground="red")
            self.venta_cantidad_entry.config(state='normal')
            self.label_precio_venta_mostrar.config(text="$0.00/kg")
            self.label_precio_cliente_mostrar.config(text="$0.00/kg")
            self.label_ganancia_mostrar.config(text="$0.00/kg")
    
    def actualizar_total_venta(self, event=None):
        material = self.venta_material_combo.get()
        if not material or material not in self.inventario:
            return
        
        try:
            cantidad = float(self.venta_cantidad_entry.get())
            if cantidad <= 0:
                raise ValueError
        except:
            self.label_total_venta.config(text="$0.00")
            self.label_distribucion.config(text="")
            return
        
        datos = self.inventario[material]
        stock = datos.get("stock", 0)
        
        if cantidad > stock:
            self.label_total_venta.config(text=f"⚠️ Stock insuficiente (máx: {stock:.2f} kg)", foreground="red")
            self.label_distribucion.config(text="")
            return
        
        precio_venta = datos.get("precio_venta", 0)
        precio_cliente = self.calcular_precio_cliente(material, precio_venta)
        ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
        ganancia_total = self.redondear(cantidad * ganancia_por_kg)
        total = self.redondear(cantidad * precio_cliente)
        salarios = self.redondear(total * 0.10)
        caja = self.redondear(total)
        porcentaje = self.obtener_porcentaje_ganancia(material) * 100
        
        self.label_total_venta.config(text=f"${total:.2f}", foreground="blue")
        self.label_ganancia_mostrar.config(
            text=f"${ganancia_por_kg:.2f}/kg ({porcentaje:.1f}%)",
            foreground="red" if porcentaje == 5 else "green"
        )
        self.label_distribucion.config(
            text=f"💰 Caja General: ${caja:.2f} | 👥 Fondo Salarios (10%): ${salarios:.2f} | 💰 Ganancia: ${ganancia_total:.2f} ({porcentaje:.1f}%)",
            foreground="darkgreen"
        )
    
    def registrar_venta_inventario(self):
        cliente = self.venta_cliente_combo.get()
        if not cliente:
            messagebox.showwarning("Error", "Seleccione un cliente")
            return
        
        material = self.venta_material_combo.get()
        if not material:
            messagebox.showwarning("Error", "Seleccione un material")
            return
        
        if material not in self.inventario:
            messagebox.showwarning("Error", "Material no encontrado en inventario")
            return
        
        try:
            cantidad = float(self.venta_cantidad_entry.get())
            if cantidad <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Error", "Cantidad válida requerida")
            return
        
        datos = self.inventario[material]
        stock_disponible = datos.get("stock", 0)
        
        if cantidad > stock_disponible:
            messagebox.showwarning("Error", 
                f"❌ Stock insuficiente para '{material}'.\n\n"
                f"📊 Stock disponible: {stock_disponible:.2f} kg\n"
                f"📦 Cantidad solicitada: {cantidad:.2f} kg\n"
                f"⚠️ Falta: {cantidad - stock_disponible:.2f} kg")
            return
        
        precio_venta = datos.get("precio_venta", 0)
        if precio_venta <= 0:
            messagebox.showwarning("Error", "El material no tiene precio de venta configurado")
            return
        
        precio_cliente = self.calcular_precio_cliente(material, precio_venta)
        ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
        ganancia_total = self.redondear(cantidad * ganancia_por_kg)
        total_venta = self.redondear(cantidad * precio_cliente)
        salarios = self.redondear(total_venta * 0.10)
        caja = self.redondear(total_venta)
        porcentaje = self.obtener_porcentaje_ganancia(material) * 100
        
        costo_promedio = datos.get("inversion_promedio", precio_venta * 0.90)
        if costo_promedio == 0:
            costo_promedio = datos.get("precio_compra_cliente", precio_venta * 0.90)
        
        reduccion_inversion = self.redondear(cantidad * costo_promedio)
        inversion_actual = datos.get("inversion_total", 0)
        
        if reduccion_inversion > inversion_actual:
            reduccion_inversion = inversion_actual
        
        nueva_inversion = self.redondear(max(0, inversion_actual - reduccion_inversion))
        
        stock_despues = self.redondear(stock_disponible - cantidad)
        mensaje_confirmacion = (
            f"📋 DETALLE DE VENTA\n\n"
            f"👤 Cliente: {cliente}\n"
            f"📦 Material: {material}\n"
            f"📊 Cantidad: {cantidad:.2f} kg\n"
            f"💰 Precio Venta: ${precio_venta:.2f}/kg\n"
            f"💰 Precio Cliente: ${precio_cliente:.2f}/kg\n"
            f"💰 Ganancia: ${ganancia_total:.2f} ({porcentaje:.1f}%)\n"
            f"💵 Total: ${total_venta:.2f}\n\n"
            f"📌 Stock actual: {stock_disponible:.2f} kg\n"
            f"📌 Stock después: {stock_despues:.2f} kg\n\n"
            f"💰 Inversión actual: ${inversion_actual:.2f}\n"
        )
        
        if stock_despues == 0:
            mensaje_confirmacion += f"💰 Inversión después: $0.00 (se resetea a cero)\n\n"
        else:
            mensaje_confirmacion += (
                f"💰 Reducción: ${reduccion_inversion:.2f}\n"
                f"💰 Inversión después: ${nueva_inversion:.2f}\n\n"
            )
        
        mensaje_confirmacion += (
            f"💵 Distribución:\n"
            f"   • Caja General (+): ${caja:.2f}\n"
            f"   • Fondo Salarios (+): ${salarios:.2f}\n"
            f"   • Ganancia ({porcentaje:.1f}%): ${ganancia_total:.2f}\n\n"
            f"¿Confirmar la venta?"
        )
        
        if not messagebox.askyesno("Confirmar Venta", mensaje_confirmacion):
            return
        
        stock_anterior = stock_disponible
        nuevo_stock = self.redondear(stock_anterior - cantidad)
        datos["stock"] = nuevo_stock
        
        if nuevo_stock == 0:
            datos["inversion_total"] = 0
            datos["inversion_promedio"] = 0
            datos["total_comprado"] = 0
            reduccion_inversion = inversion_actual
            nueva_inversion = 0
        else:
            datos["inversion_total"] = nueva_inversion
            if nuevo_stock > 0:
                datos["inversion_promedio"] = self.redondear(nueva_inversion / nuevo_stock)
        
        material_eliminado = False
        if nuevo_stock == 0:
            if messagebox.askyesno("Stock Agotado", 
                f"⚠️ El material '{material}' se ha agotado.\n\n"
                f"Stock restante: 0.00 kg\n"
                f"Inversión reseteada a: $0.00\n\n"
                f"¿Desea eliminarlo del inventario?"):
                del self.inventario[material]
                material_eliminado = True
        
        self.caja_general = self.redondear(self.caja_general + caja)
        self.fondo_salarios = self.redondear(self.fondo_salarios + salarios)
        
        concepto = f"Venta - {material} ({cliente})"
        if ganancia_total > 0:
            concepto += f" (ganancia: ${ganancia_total:.2f} - {porcentaje:.1f}%)"
        self.registrar_movimiento_caja("ingreso", concepto, caja)
        
        venta_id = max([v.get('id', 0) for v in self.ventas]) + 1 if self.ventas else 1
        venta = {
            "id": venta_id,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cliente": cliente,
            "material": material,
            "cantidad": cantidad,
            "precio_unitario": precio_venta,
            "precio_cliente": precio_cliente,
            "ganancia": ganancia_total,
            "porcentaje_ganancia": porcentaje,
            "total": total_venta,
            "caja_asignada": caja,
            "salarios_asignados": salarios,
            "seccion": datos.get("seccion", "inventario"),
            "stock_anterior": stock_anterior,
            "stock_actual": 0 if material_eliminado else nuevo_stock,
            "inversion_anterior": inversion_actual,
            "inversion_actual": 0 if material_eliminado else nueva_inversion,
            "reduccion_inversion": reduccion_inversion
        }
        self.ventas.append(venta)
        
        remision_existente = None
        for r in self.remisiones_generadas:
            if r.get('cliente') == cliente and r.get('tipo') == 'venta' and r.get('fecha', '')[:10] == datetime.now().strftime("%Y-%m-%d"):
                remision_existente = r
                break
        
        if remision_existente:
            remision_existente['items'].append({
                "material": material,
                "cantidad": cantidad,
                "precio": precio_cliente,
                "precio_original": precio_venta,
                "ganancia": ganancia_total,
                "porcentaje_ganancia": porcentaje,
                "total": total_venta,
                "seccion": datos.get("seccion", "inventario")
            })
            remision_existente['total'] = self.redondear(remision_existente['total'] + total_venta)
            remision_existente['ganancia_total'] = self.redondear(remision_existente.get('ganancia_total', 0) + ganancia_total)
            remision_existente['qr_base64'] = self.generar_qr_remision(remision_existente)
            remision_id = remision_existente['id']
        else:
            remision_id = max([r.get('id', 0) for r in self.remisiones_generadas]) + 1 if self.remisiones_generadas else 1
            remision = {
                "id": remision_id,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cliente": cliente,
                "usuario": self.usuario_actual,
                "items": [{
                    "material": material,
                    "cantidad": cantidad,
                    "precio": precio_cliente,
                    "precio_original": precio_venta,
                    "ganancia": ganancia_total,
                    "porcentaje_ganancia": porcentaje,
                    "total": total_venta,
                    "seccion": datos.get("seccion", "inventario")
                }],
                "total": total_venta,
                "ganancia_total": ganancia_total,
                "tipo": "venta",
                "venta_id": venta_id
            }
            qr_base64 = self.generar_qr_remision(remision)
            remision["qr_base64"] = qr_base64
            self.remisiones_generadas.append(remision)
        
        nuevo_id = max([c.get('id', 0) for c in self.compras] + [c.get('id', 0) for c in self.compras_mayoreo]) + 1 if (self.compras or self.compras_mayoreo) else 1
        registro_historial = {
            "id": nuevo_id,
            "fecha": venta["fecha"],
            "cliente": cliente,
            "seccion": datos.get("seccion", "inventario"),
            "material": material,
            "cantidad": cantidad,
            "precio_unitario": precio_venta,
            "precio_cliente": precio_cliente,
            "ganancia": ganancia_total,
            "porcentaje_ganancia": porcentaje,
            "total": total_venta,
            "tipo_precio": "venta_inventario",
            "caja_asignada": caja,
            "salarios_asignados": salarios,
            "stock_anterior": stock_anterior,
            "stock_actual": 0 if material_eliminado else nuevo_stock,
            "inversion_anterior": inversion_actual,
            "inversion_actual": 0 if material_eliminado else nueva_inversion,
            "reduccion_inversion": reduccion_inversion,
            "remision_id": remision_id
        }
        self.compras.append(registro_historial)
        
        self.guardar_datos()
        self.actualizar_tabla_inventario()
        self.actualizar_lista_venta()
        self.actualizar_lista_ventas()
        self.actualizar_metricas()
        self.actualizar_info_caja()
        self.actualizar_movimientos_caja()
        self.actualizar_lista_remisiones()
        self.cargar_materiales_pos_venta()
        self.actualizar_frecuencia_clientes()
        
        self.enviar_correo_remision_completa(cliente, remision_id, venta["fecha"], 
                                            self.remisiones_generadas[-1]['items'] if remision_existente else remision['items'], 
                                            self.remisiones_generadas[-1]['total'] if remision_existente else total_venta, 
                                            es_venta=True)
        
        self.venta_cliente_combo.set("")
        self.venta_material_combo.set("")
        self.venta_cantidad_entry.delete(0, tk.END)
        self.label_total_venta.config(text="$0.00")
        self.label_distribucion.config(text="")
        self.label_stock_info.config(text="")
        
        stock_restante = 0 if material_eliminado else nuevo_stock
        inversion_restante = 0 if material_eliminado else nueva_inversion
        
        mensaje_exito = (
            f"✅ Venta registrada exitosamente!\n\n"
            f"👤 Cliente: {cliente}\n"
            f"📦 Material: {material}\n"
            f"📊 Cantidad: {cantidad:.2f} kg\n"
            f"💰 Precio Venta: ${precio_venta:.2f}/kg\n"
            f"💰 Precio Cliente: ${precio_cliente:.2f}/kg\n"
            f"💰 Ganancia: ${ganancia_total:.2f} ({porcentaje:.1f}%)\n"
            f"💰 Total: ${total_venta:.2f}\n"
            f"📋 Remisión generada: #{remision_id}\n\n"
            f"📊 Stock actualizado:\n"
            f"   • Stock anterior: {stock_anterior:.2f} kg\n"
            f"   • Stock actual: {stock_restante:.2f} kg\n\n"
            f"💰 Inversión actualizada:\n"
            f"   • Inversión anterior: ${inversion_actual:.2f}\n"
            f"   • Reducción: ${reduccion_inversion:.2f}\n"
            f"   • Inversión actual: ${inversion_restante:.2f}\n\n"
            f"💵 Distribución:\n"
            f"   • Caja General (+): ${caja:.2f}\n"
            f"   • Fondo Salarios (+): ${salarios:.2f}\n\n"
            f"📊 Nuevos saldos:\n"
            f"   • Caja General: ${self.caja_general:.2f}\n"
            f"   • Fondo Salarios: ${self.fondo_salarios:.2f}\n\n"
            f"📧 Se ha enviado un correo con la remisión."
        )
        
        if stock_restante == 0:
            mensaje_exito += "\n\n⚠️ Material agotado - Inversión reseteada a $0.00"
        
        messagebox.showinfo("Éxito", mensaje_exito)
    
    def actualizar_lista_ventas(self):
        for item in self.tree_ventas.get_children():
            self.tree_ventas.delete(item)
        
        for venta in sorted(self.ventas, key=lambda x: x.get('fecha', ''), reverse=True)[:50]:
            ganancia_text = f"{venta.get('ganancia', 0):.2f} ({venta.get('porcentaje_ganancia', 10):.1f}%)"
            
            self.tree_ventas.insert("", "end", values=(
                venta.get('id', ''),
                venta.get('fecha', '')[:16],
                venta.get('cliente', ''),
                venta.get('material', ''),
                f"{venta.get('cantidad', 0):.2f}",
                f"{venta.get('precio_unitario', 0):.2f}",
                f"{venta.get('precio_cliente', 0):.2f}",
                ganancia_text,
                f"{venta.get('total', 0):.2f}",
                f"{venta.get('stock_anterior', 0):.2f}",
                f"{venta.get('stock_actual', 0):.2f}"
            ))
        
        self.seleccionar_todos_ventas.set(False)
    
    def editar_venta(self):
        seleccion = self.tree_ventas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una venta para editar")
            return
        
        item = seleccion[0]
        item_data = self.tree_ventas.item(item)
        valores = item_data['values']
        venta_id = int(valores[0])
        
        venta = None
        for v in self.ventas:
            if v.get('id') == venta_id:
                venta = v
                break
        
        if not venta:
            messagebox.showwarning("Error", "Venta no encontrada")
            return
        
        ventana_editar = tk.Toplevel(self.root)
        ventana_editar.title(f"Editar Venta #{venta_id}")
        ventana_editar.geometry("400x450")
        ventana_editar.transient(self.root)
        ventana_editar.grab_set()
        
        ttk.Label(ventana_editar, text=f"Editando Venta #{venta_id}").pack(pady=10)
        ttk.Label(ventana_editar, text=f"Fecha: {venta.get('fecha', '')}").pack()
        
        ttk.Label(ventana_editar, text="Cliente:").pack(pady=5)
        cliente_entry = ttk.Entry(ventana_editar, width=30)
        cliente_entry.insert(0, venta.get('cliente', ''))
        cliente_entry.pack()
        
        ttk.Label(ventana_editar, text="Material:").pack(pady=5)
        material_entry = ttk.Entry(ventana_editar, width=30)
        material_entry.insert(0, venta.get('material', ''))
        material_entry.pack()
        
        ttk.Label(ventana_editar, text="Cantidad (kg):").pack(pady=5)
        cantidad_entry = ttk.Entry(ventana_editar, width=15)
        cantidad_entry.insert(0, str(venta.get('cantidad', 0)))
        cantidad_entry.pack()
        
        ttk.Label(ventana_editar, text="Precio Unitario ($/kg):").pack(pady=5)
        precio_entry = ttk.Entry(ventana_editar, width=15)
        precio_entry.insert(0, str(venta.get('precio_unitario', 0)))
        precio_entry.pack()
        
        def guardar_cambios():
            try:
                nuevo_cliente = cliente_entry.get().strip()
                nuevo_material = material_entry.get().strip()
                nueva_cantidad = float(cantidad_entry.get())
                nuevo_precio = float(precio_entry.get())
                
                if not nuevo_cliente or not nuevo_material:
                    messagebox.showwarning("Error", "Cliente y material son obligatorios")
                    return
                
                if nueva_cantidad <= 0 or nuevo_precio <= 0:
                    messagebox.showwarning("Error", "Cantidad y precio deben ser positivos")
                    return
                
                nuevo_precio_cliente = self.calcular_precio_cliente(nuevo_material, nuevo_precio)
                nueva_ganancia = self.calcular_ganancia(nuevo_material, nuevo_precio) * nueva_cantidad
                nuevo_total = self.redondear(nueva_cantidad * nuevo_precio_cliente)
                porcentaje = self.obtener_porcentaje_ganancia(nuevo_material) * 100
                
                venta['cliente'] = nuevo_cliente
                venta['material'] = nuevo_material
                venta['cantidad'] = nueva_cantidad
                venta['precio_unitario'] = nuevo_precio
                venta['precio_cliente'] = nuevo_precio_cliente
                venta['ganancia'] = nueva_ganancia
                venta['porcentaje_ganancia'] = porcentaje
                venta['total'] = nuevo_total
                
                for compra in self.compras:
                    if compra.get('id') == venta_id and compra.get('tipo_precio') == 'venta_inventario':
                        compra['cliente'] = nuevo_cliente
                        compra['material'] = nuevo_material
                        compra['cantidad'] = nueva_cantidad
                        compra['precio_unitario'] = nuevo_precio
                        compra['precio_cliente'] = nuevo_precio_cliente
                        compra['ganancia'] = nueva_ganancia
                        compra['porcentaje_ganancia'] = porcentaje
                        compra['total'] = nuevo_total
                        break
                
                self.guardar_datos()
                self.actualizar_lista_ventas()
                ventana_editar.destroy()
                messagebox.showinfo("Éxito", "Venta actualizada correctamente")
                
            except ValueError:
                messagebox.showwarning("Error", "Ingrese valores numéricos válidos")
        
        ttk.Button(ventana_editar, text="Guardar Cambios", command=guardar_cambios).pack(pady=20)
        ttk.Button(ventana_editar, text="Cancelar", command=ventana_editar.destroy).pack()
    
    def eliminar_venta(self):
        seleccion = self.tree_ventas.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una venta para eliminar")
            return
        
        item = seleccion[0]
        item_data = self.tree_ventas.item(item)
        valores = item_data['values']
        venta_id = int(valores[0])
        
        if messagebox.askyesno("Confirmar", f"¿Eliminar la venta #{venta_id}?\n\nEsta acción no se puede deshacer."):
            self.ventas = [v for v in self.ventas if v.get('id') != venta_id]
            self.compras = [c for c in self.compras if not (c.get('id') == venta_id and c.get('tipo_precio') == 'venta_inventario')]
            
            self.guardar_datos()
            self.actualizar_lista_ventas()
            messagebox.showinfo("Éxito", "Venta eliminada correctamente")
    
    # ==================== TAB REMISIÓN ====================
    
    def crear_tab_remision(self):
        frame_cliente = ttk.LabelFrame(self.tab_remision, text="👤 Seleccionar Cliente")
        frame_cliente.pack(pady=5, padx=8, fill='x')
        
        ttk.Label(frame_cliente, text="Cliente:").grid(row=0, column=0, padx=4, pady=4)
        self.remision_cliente_combo = ttk.Combobox(frame_cliente, values=[c['nombre'] for c in self.clientes], width=30)
        self.remision_cliente_combo.grid(row=0, column=1, padx=4, pady=4)
        self.remision_cliente_combo.bind('<<ComboboxSelected>>', self.actualizar_historial_remisiones_cliente)
        
        ttk.Button(frame_cliente, text="➕ Nuevo Cliente", 
                  command=self.agregar_cliente_desde_remision).grid(row=0, column=2, padx=4, pady=4)
        
        frame_material = ttk.LabelFrame(self.tab_remision, text="📦 Agregar Material")
        frame_material.pack(pady=5, padx=8, fill='x')
        
        ttk.Label(frame_material, text="Sección:").grid(row=0, column=0, padx=4, pady=4)
        self.remision_seccion_combo = ttk.Combobox(frame_material, 
            values=["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"], width=12)
        self.remision_seccion_combo.grid(row=0, column=1, padx=4, pady=4)
        self.remision_seccion_combo.bind('<<ComboboxSelected>>', self.actualizar_materiales_remision)
        
        ttk.Label(frame_material, text="Material:").grid(row=0, column=2, padx=4, pady=4)
        self.remision_material_combo = ttk.Combobox(frame_material, width=20)
        self.remision_material_combo.grid(row=0, column=3, padx=4, pady=4)
        self.remision_material_combo.bind('<<ComboboxSelected>>', self.mostrar_precio_remision)
        
        ttk.Label(frame_material, text="Cantidad (kg):").grid(row=0, column=4, padx=4, pady=4)
        self.remision_cantidad_entry = ttk.Entry(frame_material, width=10)
        self.remision_cantidad_entry.grid(row=0, column=5, padx=4, pady=4)
        
        ttk.Label(frame_material, text="Precio $/kg:").grid(row=1, column=0, padx=4, pady=4)
        self.remision_precio_entry = ttk.Entry(frame_material, width=12)
        self.remision_precio_entry.grid(row=1, column=1, padx=4, pady=4)
        
        self.label_precio_sugerido = ttk.Label(frame_material, text="", font=("Arial", 9), foreground="blue")
        self.label_precio_sugerido.grid(row=1, column=2, columnspan=2, padx=4, pady=4)
        
        self.label_ganancia_remision = ttk.Label(frame_material, text="", font=("Arial", 9))
        self.label_ganancia_remision.grid(row=1, column=4, columnspan=2, padx=4, pady=4)
        
        frame_botones_carrito = ttk.Frame(frame_material)
        frame_botones_carrito.grid(row=2, column=0, columnspan=6, pady=8)
        
        ttk.Button(frame_botones_carrito, text="➕ Agregar al Carrito", 
                  command=self.agregar_al_carrito).pack(side='left', padx=5)
        ttk.Button(frame_botones_carrito, text="🗑️ Eliminar Selección", 
                  command=self.eliminar_del_carrito).pack(side='left', padx=5)
        ttk.Button(frame_botones_carrito, text="🧹 Limpiar Carrito", 
                  command=self.limpiar_carrito).pack(side='left', padx=5)
        ttk.Button(frame_botones_carrito, text="📋 Finalizar Remisión", 
                  command=self.finalizar_remision).pack(side='left', padx=5)
        ttk.Button(frame_botones_carrito, text="📥 Ver Remisiones", 
                  command=self.mostrar_remisiones_guardadas).pack(side='left', padx=5)
        
        frame_carrito = ttk.LabelFrame(self.tab_remision, text="🛒 Carrito de Compras")
        frame_carrito.pack(pady=5, padx=8, fill='both', expand=True)
        
        self.tree_carrito = ttk.Treeview(frame_carrito, 
            columns=("Sección", "Material", "Cantidad", "Precio", "Ganancia", "Total"), 
            show='headings', height=8)
        self.tree_carrito.heading("Sección", text="Sección")
        self.tree_carrito.heading("Material", text="Material")
        self.tree_carrito.heading("Cantidad", text="Cantidad (kg)")
        self.tree_carrito.heading("Precio", text="Precio ($/kg)")
        self.tree_carrito.heading("Ganancia", text="Ganancia")
        self.tree_carrito.heading("Total", text="Total ($)")
        
        self.tree_carrito.column("Sección", width=100)
        self.tree_carrito.column("Material", width=150)
        self.tree_carrito.column("Cantidad", width=80)
        self.tree_carrito.column("Precio", width=80)
        self.tree_carrito.column("Ganancia", width=80)
        self.tree_carrito.column("Total", width=100)
        self.tree_carrito.pack(fill='both', expand=True, padx=5, pady=5)
        
        frame_totales = ttk.Frame(self.tab_remision)
        frame_totales.pack(pady=5, padx=8, fill='x')
        
        self.label_total_carrito = ttk.Label(frame_totales, text="💰 Total: $0.00", 
                                            font=("Arial", 12, "bold"), foreground="green")
        self.label_total_carrito.pack(side='left', padx=10)
        
        self.label_ganancia_carrito = ttk.Label(frame_totales, text="💰 Ganancia Total: $0.00", 
                                               font=("Arial", 10), foreground="red")
        self.label_ganancia_carrito.pack(side='left', padx=10)
        
        ttk.Label(frame_totales, text=f"📋 Remisiones del Cliente:").pack(side='left', padx=20)
        
        self.tree_historial_remisiones = ttk.Treeview(frame_totales, 
            columns=("ID", "Fecha", "Total"), show='headings', height=4)
        self.tree_historial_remisiones.heading("ID", text="ID")
        self.tree_historial_remisiones.heading("Fecha", text="Fecha")
        self.tree_historial_remisiones.heading("Total", text="Total ($)")
        self.tree_historial_remisiones.column("ID", width=60)
        self.tree_historial_remisiones.column("Fecha", width=120)
        self.tree_historial_remisiones.column("Total", width=80)
        self.tree_historial_remisiones.pack(side='left', fill='x', expand=True, padx=10)
    
    def agregar_cliente_desde_remision(self):
        nombre = simpledialog.askstring("Nuevo Cliente", "Ingrese el nombre del cliente:")
        if nombre and nombre.strip():
            telefono = simpledialog.askstring("Teléfono", "Ingrese el teléfono (opcional):")
            cliente_id = len(self.clientes) + 1
            self.clientes.append({"id": cliente_id, "nombre": nombre.strip(), "telefono": telefono or ""})
            self.guardar_datos()
            self.actualizar_lista_clientes()
            self.actualizar_combo_clientes()
            self.remision_cliente_combo.set(nombre.strip())
            messagebox.showinfo("Éxito", "Cliente agregado correctamente")
    
    def actualizar_materiales_remision(self, event=None):
        seccion = self.remision_seccion_combo.get()
        if seccion in self.materiales:
            materiales = [m['nombre'] for m in self.materiales[seccion]]
            self.remision_material_combo['values'] = materiales
            self.remision_material_combo.set('')
            self.label_precio_sugerido.config(text="")
            self.label_ganancia_remision.config(text="")
            self.remision_precio_entry.delete(0, tk.END)
    
    def mostrar_precio_remision(self, event=None):
        seccion = self.remision_seccion_combo.get()
        material = self.remision_material_combo.get()
        
        if seccion and material:
            precio = self.obtener_precio_material(seccion, material)
            if precio is not None:
                precio_cliente = self.calcular_precio_cliente(material, precio)
                ganancia = self.calcular_ganancia(material, precio)
                porcentaje = self.obtener_porcentaje_ganancia(material) * 100
                self.remision_precio_entry.delete(0, tk.END)
                self.remision_precio_entry.insert(0, f"{precio_cliente:.2f}")
                self.label_precio_sugerido.config(text=f"💡 Precio Venta: ${precio:.2f}/kg")
                self.label_ganancia_remision.config(
                    text=f"💰 Ganancia: ${ganancia:.2f}/kg ({porcentaje:.1f}%)",
                    foreground="red" if porcentaje == 5 else "green"
                )
            else:
                self.label_precio_sugerido.config(text="⚠️ Material no encontrado")
                self.label_ganancia_remision.config(text="")
    
    def obtener_precio_material(self, seccion, material_nombre):
        if seccion in self.materiales:
            for m in self.materiales[seccion]:
                if m['nombre'] == material_nombre:
                    return self.redondear(m.get('precio_venta', 0))
        return None
    
    def agregar_al_carrito(self):
        seccion = self.remision_seccion_combo.get()
        material = self.remision_material_combo.get()
        
        if not seccion or not material:
            messagebox.showwarning("Error", "Seleccione sección y material")
            return
        
        try:
            cantidad = float(self.remision_cantidad_entry.get())
            precio = float(self.remision_precio_entry.get())
            
            if cantidad <= 0 or precio <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Error", "Cantidad y precio válidos requeridos")
            return
        
        precio_venta = self.obtener_precio_material(seccion, material)
        ganancia_por_kg = self.calcular_ganancia(material, precio_venta) if precio_venta else 0
        ganancia_total = self.redondear(cantidad * ganancia_por_kg)
        total = self.redondear(cantidad * precio)
        porcentaje = self.obtener_porcentaje_ganancia(material) * 100
        
        for item in self.carrito_compras:
            if item['material'] == material:
                if messagebox.askyesno("Confirmar", 
                    f"El material '{material}' ya está en el carrito.\n"
                    f"Cantidad actual: {item['cantidad']:.2f} kg\n"
                    f"¿Desea agregar más cantidad?"):
                    item['cantidad'] = self.redondear(item['cantidad'] + cantidad)
                    item['ganancia_total'] = self.redondear(item['ganancia_total'] + ganancia_total)
                    item['total'] = self.redondear(item['cantidad'] * item['precio'])
                    self.actualizar_carrito()
                    return
                else:
                    return
        
        self.carrito_compras.append({
            "seccion": seccion,
            "material": material,
            "cantidad": cantidad,
            "precio": precio,
            "ganancia_total": ganancia_total,
            "porcentaje_ganancia": porcentaje,
            "total": total
        })
        
        self.actualizar_carrito()
        self.remision_cantidad_entry.delete(0, tk.END)
        
        mensaje = f"✅ {material} agregado al carrito\nTotal: ${total:.2f}"
        if ganancia_total > 0:
            mensaje += f"\nGanancia ({porcentaje:.1f}%): ${ganancia_total:.2f}"
        messagebox.showinfo("Éxito", mensaje)
    
    def eliminar_del_carrito(self):
        seleccion = self.tree_carrito.selection()
        if seleccion:
            indices = [self.tree_carrito.index(item) for item in seleccion]
            for idx in sorted(indices, reverse=True):
                if idx < len(self.carrito_compras):
                    del self.carrito_compras[idx]
            self.actualizar_carrito()
    
    def limpiar_carrito(self):
        if self.carrito_compras and messagebox.askyesno("Confirmar", "¿Eliminar todos los items del carrito?"):
            self.carrito_compras = []
            self.actualizar_carrito()
    
    def actualizar_carrito(self):
        for item in self.tree_carrito.get_children():
            self.tree_carrito.delete(item)
        
        total_general = 0
        ganancia_general = 0
        for item in self.carrito_compras:
            ganancia_text = f"{item.get('ganancia_total', 0):.2f} ({item.get('porcentaje_ganancia', 10):.1f}%)"
            self.tree_carrito.insert("", "end", values=(
                item['seccion'],
                item['material'],
                f"{item['cantidad']:.2f}",
                f"{item['precio']:.2f}",
                ganancia_text,
                f"{item['total']:.2f}"
            ))
            total_general += item['total']
            ganancia_general += item.get('ganancia_total', 0)
        
        self.label_total_carrito.config(text=f"💰 Total: ${total_general:.2f}")
        self.label_ganancia_carrito.config(text=f"💰 Ganancia Total: ${ganancia_general:.2f}", 
                                          foreground="red" if ganancia_general > 0 else "green")
    
    def finalizar_remision(self):
        if not self.carrito_compras:
            messagebox.showwarning("Error", "El carrito está vacío")
            return
        
        cliente = self.remision_cliente_combo.get()
        if not cliente:
            if messagebox.askyesno("Cliente", "No hay cliente seleccionado. ¿Desea seleccionar uno ahora?"):
                cliente = simpledialog.askstring("Cliente", "Ingrese el nombre del cliente:")
                if cliente:
                    self.remision_cliente_combo.set(cliente)
                else:
                    return
            else:
                return
        
        cliente_existente = False
        for c in self.clientes:
            if c['nombre'] == cliente:
                cliente_existente = True
                break
        
        if not cliente_existente:
            if messagebox.askyesno("Nuevo Cliente", f"El cliente '{cliente}' no está registrado.\n¿Desea registrarlo ahora?"):
                self.clientes.append({"id": len(self.clientes) + 1, "nombre": cliente, "telefono": ""})
                self.guardar_datos()
                self.actualizar_lista_clientes()
                self.actualizar_combo_clientes()
            else:
                return
        
        total_general = sum(item['total'] for item in self.carrito_compras)
        ganancia_general = sum(item.get('ganancia_total', 0) for item in self.carrito_compras)
        
        if not messagebox.askyesno("Confirmar Remisión", 
            f"📋 Remisión para: {cliente}\n"
            f"📦 Items: {len(self.carrito_compras)}\n"
            f"💰 Total: ${total_general:.2f}\n"
            f"💰 Ganancia Total: ${ganancia_general:.2f}\n\n"
            f"¿Confirmar la remisión?"):
            return
        
        total_egresos_remision = total_general
        
        remision_id = max([r.get('id', 0) for r in self.remisiones_generadas]) + 1 if self.remisiones_generadas else 1
        
        remision_data = {
            "id": remision_id,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cliente": cliente,
            "usuario": self.usuario_actual,
            "items": self.carrito_compras.copy(),
            "total": total_general,
            "ganancia_total": ganancia_general,
            "tipo": "remision"
        }
        
        qr_base64 = self.generar_qr_remision(remision_data)
        remision_data["qr_base64"] = qr_base64
        
        self.remisiones_generadas.append(remision_data)
        
        for item in self.carrito_compras:
            compra = {
                "id": len(self.compras) + 1,
                "remision_id": remision_id,
                "fecha": remision_data["fecha"],
                "cliente": cliente,
                "seccion": item['seccion'],
                "material": item['material'],
                "cantidad": item['cantidad'],
                "precio_unitario": item['precio'],
                "ganancia": item.get('ganancia_total', 0),
                "porcentaje_ganancia": item.get('porcentaje_ganancia', 10),
                "total": item['total'],
                "tipo_precio": "cliente",
                "procesada_inventario": False
            }
            self.compras.append(compra)
        
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        caja_registrada = False
        
        if fecha_actual in self.caja_diaria and self.caja_diaria[fecha_actual].get("abierta", False):
            if total_egresos_remision > 0:
                concepto_egreso = f"Compra remisión #{remision_id} - {cliente}"
                if ganancia_general > 0:
                    concepto_egreso += f" (ganancia: ${ganancia_general:.2f})"
                self.registrar_movimiento_caja("egreso", concepto_egreso, total_egresos_remision)
                self.caja_general = self.redondear(self.caja_general - total_egresos_remision)
                caja_registrada = True
        
        if not caja_registrada and total_egresos_remision > 0:
            self.caja_general = self.redondear(self.caja_general - total_egresos_remision)
        
        self.guardar_datos()
        self.actualizar_lista_remisiones()
        
        self.enviar_correo_remision_completa(cliente, remision_id, remision_data["fecha"], remision_data["items"], total_general, es_venta=False)
        
        self.descargar_remision(remision_id)
        
        self.carrito_compras = []
        self.actualizar_carrito()
        
        self.actualizar_info_caja()
        self.actualizar_movimientos_caja()
        self.actualizar_historial_caja()
        self.actualizar_metricas()
        self.actualizar_tabla_inventario()
        self.actualizar_historial()
        self.cargar_materiales_pos_venta()
        self.actualizar_frecuencia_clientes()
        
        mensaje_final = (
            f"✅ Remisión #{remision_id} completada exitosamente!\n\n"
            f"👤 Cliente: {cliente}\n"
            f"📦 Items: {len(remision_data['items'])}\n"
            f"💰 Total: ${total_general:.2f}\n"
            f"💰 Ganancia Total: ${ganancia_general:.2f}\n"
            f"📄 La remisión se ha descargado automáticamente.\n"
            f"📧 Se ha enviado un correo con la remisión.\n\n"
            f"📊 Saldo actual en caja: ${self.caja_general:.2f}"
        )
        
        messagebox.showinfo("Éxito", mensaje_final)
        
        self.actualizar_historial_remisiones_cliente()
    
    def actualizar_historial_remisiones_cliente(self, event=None):
        for item in self.tree_historial_remisiones.get_children():
            self.tree_historial_remisiones.delete(item)
        
        cliente = self.remision_cliente_combo.get()
        if not cliente:
            return
        
        remisiones = []
        for remision in self.remisiones_generadas:
            if remision.get('cliente') == cliente:
                remisiones.append({
                    'id': remision.get('id'),
                    'fecha': remision.get('fecha', '')[:16],
                    'total': remision.get('total', 0)
                })
        
        for r in sorted(remisiones, key=lambda x: x['id'], reverse=True)[:10]:
            self.tree_historial_remisiones.insert("", "end", values=(r['id'], r['fecha'], f"{r['total']:.2f}"))
    
    # ==================== TAB HISTORIAL ====================
    
    def crear_tab_historial(self):
        frame_filtros = ttk.Frame(self.tab_historial)
        frame_filtros.pack(pady=5, padx=8, fill='x')
        
        ttk.Label(frame_filtros, text="Buscar:").pack(side='left', padx=5)
        self.historial_buscar_entry = ttk.Entry(frame_filtros, width=30)
        self.historial_buscar_entry.pack(side='left', padx=5)
        self.historial_buscar_entry.bind('<KeyRelease>', self.filtrar_historial)
        
        ttk.Label(frame_filtros, text="Filtrar por tipo:").pack(side='left', padx=5)
        self.historial_tipo_combo = ttk.Combobox(frame_filtros, 
            values=["Todos", "cliente", "compra_inventario", "venta_inventario"], 
            width=15)
        self.historial_tipo_combo.set("Todos")
        self.historial_tipo_combo.bind('<<ComboboxSelected>>', self.filtrar_historial)
        
        ttk.Button(frame_filtros, text="🔄 Actualizar", command=self.actualizar_historial).pack(side='left', padx=10)
        
        frame_tabla = ttk.LabelFrame(self.tab_historial, text="📜 Historial de Transacciones")
        frame_tabla.pack(pady=5, padx=8, fill='both', expand=True)
        
        self.tree_historial = ttk.Treeview(frame_tabla, 
            columns=("ID", "Fecha", "Cliente", "Sección", "Material", "Cantidad", "Precio", "Ganancia", "Total", "Tipo"), 
            show='headings', height=15)
        self.tree_historial.heading("ID", text="ID")
        self.tree_historial.heading("Fecha", text="Fecha")
        self.tree_historial.heading("Cliente", text="Cliente")
        self.tree_historial.heading("Sección", text="Sección")
        self.tree_historial.heading("Material", text="Material")
        self.tree_historial.heading("Cantidad", text="Cantidad (kg)")
        self.tree_historial.heading("Precio", text="Precio ($/kg)")
        self.tree_historial.heading("Ganancia", text="Ganancia")
        self.tree_historial.heading("Total", text="Total ($)")
        self.tree_historial.heading("Tipo", text="Tipo")
        
        self.tree_historial.column("ID", width=50)
        self.tree_historial.column("Fecha", width=130)
        self.tree_historial.column("Cliente", width=120)
        self.tree_historial.column("Sección", width=80)
        self.tree_historial.column("Material", width=150)
        self.tree_historial.column("Cantidad", width=80)
        self.tree_historial.column("Precio", width=80)
        self.tree_historial.column("Ganancia", width=80)
        self.tree_historial.column("Total", width=90)
        self.tree_historial.column("Tipo", width=100)
        self.tree_historial.pack(fill='both', expand=True)
        
        frame_botones = ttk.Frame(self.tab_historial)
        frame_botones.pack(pady=5, fill='x')
        
        ttk.Button(frame_botones, text="✏️ Editar", command=self.editar_compra).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="🗑️ Eliminar", command=self.eliminar_compra).pack(side='left', padx=5)
        ttk.Button(frame_botones, text="📄 Exportar", command=self.exportar_historial).pack(side='left', padx=5)
        
        self.actualizar_historial()
    
    def actualizar_historial(self):
        for item in self.tree_historial.get_children():
            self.tree_historial.delete(item)
        
        transacciones = []
        for c in self.compras:
            c['tipo_mostrar'] = c.get('tipo_precio', 'cliente')
            transacciones.append(c)
        for c in self.compras_mayoreo:
            c['tipo_mostrar'] = c.get('tipo_precio', 'mayoreo')
            transacciones.append(c)
        
        transacciones.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        for t in transacciones[:100]:
            tipo = t.get('tipo_mostrar', 'desconocido')
            tipo_mostrar = {
                'cliente': 'Cliente',
                'mayoreo': 'Mayoreo',
                'compra_inventario': 'Compra Inv',
                'venta_inventario': 'Venta Inv'
            }.get(tipo, tipo)
            
            ganancia = t.get('ganancia', 0)
            porcentaje = t.get('porcentaje_ganancia', 10)
            ganancia_text = f"{ganancia:.2f} ({porcentaje:.1f}%)" if ganancia > 0 else "0.00"
            
            self.tree_historial.insert("", "end", values=(
                t.get('id', ''),
                t.get('fecha', '')[:16],
                t.get('cliente', ''),
                t.get('seccion', ''),
                t.get('material', ''),
                f"{t.get('cantidad', 0):.2f}",
                f"{t.get('precio_unitario', 0):.2f}",
                ganancia_text,
                f"{t.get('total', 0):.2f}",
                tipo_mostrar
            ))
    
    def filtrar_historial(self, event=None):
        buscar = self.historial_buscar_entry.get().lower()
        tipo = self.historial_tipo_combo.get()
        
        for item in self.tree_historial.get_children():
            valores = self.tree_historial.item(item)['values']
            texto = " ".join(str(v) for v in valores).lower()
            coincide_buscar = buscar in texto if buscar else True
            
            coincide_tipo = True
            if tipo != "Todos":
                tipo_valor = valores[9] if len(valores) > 9 else ""
                coincide_tipo = tipo_valor.lower() == tipo.lower()
            
            if coincide_buscar and coincide_tipo:
                self.tree_historial.item(item, tags=('visible',))
            else:
                self.tree_historial.item(item, tags=('oculto',))
        
        for item in self.tree_historial.get_children():
            tags = self.tree_historial.item(item)['tags']
            if 'oculto' in tags:
                self.tree_historial.detach(item)
            else:
                self.tree_historial.reattach(item, '', 'end')
    
    def editar_compra(self):
        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una transacción para editar")
            return
        
        item = seleccion[0]
        item_data = self.tree_historial.item(item)
        valores = item_data['values']
        compra_id = int(valores[0])
        tipo = valores[9].lower()
        
        compra = None
        lista = self.compras if tipo in ['cliente', 'compra inv'] else self.compras_mayoreo
        for c in lista:
            if c.get('id') == compra_id:
                compra = c
                break
        
        if not compra:
            messagebox.showwarning("Error", "Transacción no encontrada")
            return
        
        ventana_editar = tk.Toplevel(self.root)
        ventana_editar.title(f"Editar Transacción #{compra_id}")
        ventana_editar.geometry("400x450")
        ventana_editar.transient(self.root)
        ventana_editar.grab_set()
        
        ttk.Label(ventana_editar, text=f"Editando Transacción #{compra_id}").pack(pady=10)
        ttk.Label(ventana_editar, text=f"Tipo: {tipo.upper()}").pack()
        
        ttk.Label(ventana_editar, text="Cliente:").pack(pady=5)
        cliente_entry = ttk.Entry(ventana_editar, width=30)
        cliente_entry.insert(0, compra.get('cliente', ''))
        cliente_entry.pack()
        
        ttk.Label(ventana_editar, text="Material:").pack(pady=5)
        material_entry = ttk.Entry(ventana_editar, width=30)
        material_entry.insert(0, compra.get('material', ''))
        material_entry.pack()
        
        ttk.Label(ventana_editar, text="Cantidad (kg):").pack(pady=5)
        cantidad_entry = ttk.Entry(ventana_editar, width=15)
        cantidad_entry.insert(0, str(compra.get('cantidad', 0)))
        cantidad_entry.pack()
        
        ttk.Label(ventana_editar, text="Precio Unitario ($/kg):").pack(pady=5)
        precio_entry = ttk.Entry(ventana_editar, width=15)
        precio_entry.insert(0, str(compra.get('precio_unitario', 0)))
        precio_entry.pack()
        
        def guardar_cambios():
            try:
                nuevo_cliente = cliente_entry.get().strip()
                nuevo_material = material_entry.get().strip()
                nueva_cantidad = float(cantidad_entry.get())
                nuevo_precio = float(precio_entry.get())
                
                if not nuevo_cliente or not nuevo_material:
                    messagebox.showwarning("Error", "Cliente y material son obligatorios")
                    return
                
                if nueva_cantidad <= 0 or nuevo_precio <= 0:
                    messagebox.showwarning("Error", "Cantidad y precio deben ser positivos")
                    return
                
                compra['cliente'] = nuevo_cliente
                compra['material'] = nuevo_material
                compra['cantidad'] = nueva_cantidad
                compra['precio_unitario'] = nuevo_precio
                compra['total'] = self.redondear(nueva_cantidad * nuevo_precio)
                
                self.guardar_datos()
                self.actualizar_historial()
                ventana_editar.destroy()
                messagebox.showinfo("Éxito", "Transacción actualizada correctamente")
                
            except ValueError:
                messagebox.showwarning("Error", "Ingrese valores numéricos válidos")
        
        ttk.Button(ventana_editar, text="Guardar Cambios", command=guardar_cambios).pack(pady=20)
        ttk.Button(ventana_editar, text="Cancelar", command=ventana_editar.destroy).pack()
    
    def eliminar_compra(self):
        seleccion = self.tree_historial.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione una transacción para eliminar")
            return
        
        item = seleccion[0]
        item_data = self.tree_historial.item(item)
        valores = item_data['values']
        compra_id = int(valores[0])
        tipo = valores[9].lower()
        
        if not messagebox.askyesno("Confirmar", f"¿Eliminar la transacción #{compra_id}?\n\nEsta acción no se puede deshacer."):
            return
        
        if tipo in ['cliente', 'compra inv']:
            self.compras = [c for c in self.compras if c.get('id') != compra_id]
        else:
            self.compras_mayoreo = [c for c in self.compras_mayoreo if c.get('id') != compra_id]
        
        self.guardar_datos()
        self.actualizar_historial()
        messagebox.showinfo("Éxito", "Transacción eliminada correctamente")
    
    def exportar_historial(self):
        archivo = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Exportar Historial"
        )
        
        if archivo:
            try:
                import csv
                with open(archivo, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["ID", "Fecha", "Cliente", "Sección", "Material", "Cantidad (kg)", "Precio ($/kg)", "Ganancia", "Total ($)", "Tipo"])
                    
                    for item in self.tree_historial.get_children():
                        valores = self.tree_historial.item(item)['values']
                        writer.writerow(valores)
                
                messagebox.showinfo("Éxito", f"Historial exportado a:\n{archivo}")
            except Exception as e:
                messagebox.showerror("Error", f"Error al exportar: {str(e)}")
    
    # ==================== TAB GASTOS ====================
    
    def crear_tab_gastos(self):
        frame_form = ttk.LabelFrame(self.tab_gastos, text="💰 Registrar Gasto")
        frame_form.pack(pady=8, padx=8, fill='x')
        
        ttk.Label(frame_form, text="Concepto:").grid(row=0, column=0, padx=4, pady=4)
        self.gasto_concepto_entry = ttk.Entry(frame_form, width=30)
        self.gasto_concepto_entry.grid(row=0, column=1, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Monto ($):").grid(row=0, column=2, padx=4, pady=4)
        self.gasto_monto_entry = ttk.Entry(frame_form, width=12)
        self.gasto_monto_entry.grid(row=0, column=3, padx=4, pady=4)
        
        ttk.Label(frame_form, text="Categoría:").grid(row=0, column=4, padx=4, pady=4)
        self.gasto_categoria_combo = ttk.Combobox(frame_form, 
            values=["Operativos", "Salarios", "Compras", "Mantenimiento", "Servicios", "Otros"], 
            width=12)
        self.gasto_categoria_combo.set("Otros")
        self.gasto_categoria_combo.grid(row=0, column=5, padx=4, pady=4)
        
        ttk.Button(frame_form, text="Registrar Gasto", command=self.registrar_gasto).grid(row=0, column=6, padx=8, pady=4)
        
        frame_lista = ttk.LabelFrame(self.tab_gastos, text="📋 Historial de Gastos")
        frame_lista.pack(pady=8, padx=8, fill='both', expand=True)
        
        self.tree_gastos = ttk.Treeview(frame_lista, 
            columns=("ID", "Fecha", "Concepto", "Monto", "Categoría", "Usuario"), 
            show='headings', height=12)
        self.tree_gastos.heading("ID", text="ID")
        self.tree_gastos.heading("Fecha", text="Fecha")
        self.tree_gastos.heading("Concepto", text="Concepto")
        self.tree_gastos.heading("Monto", text="Monto ($)")
        self.tree_gastos.heading("Categoría", text="Categoría")
        self.tree_gastos.heading("Usuario", text="Usuario")
        
        self.tree_gastos.column("ID", width=50)
        self.tree_gastos.column("Fecha", width=130)
        self.tree_gastos.column("Concepto", width=250)
        self.tree_gastos.column("Monto", width=100)
        self.tree_gastos.column("Categoría", width=120)
        self.tree_gastos.column("Usuario", width=100)
        self.tree_gastos.pack(fill='both', expand=True)
        
        frame_botones_gastos = ttk.Frame(self.tab_gastos)
        frame_botones_gastos.pack(pady=5, fill='x')
        
        self.seleccionar_todos_gastos = tk.BooleanVar(value=False)
        chk_todos_gastos = ttk.Checkbutton(frame_botones_gastos, text="☑️ Seleccionar Todos", 
                                          variable=self.seleccionar_todos_gastos,
                                          command=self.toggle_seleccion_todos_gastos)
        chk_todos_gastos.pack(side='left', padx=5)
        
        ttk.Button(frame_botones_gastos, text="🗑️ Eliminar Seleccionados", command=self.eliminar_gastos_seleccionados).pack(side='left', padx=5)
        ttk.Button(frame_botones_gastos, text="🔄 Actualizar", command=self.actualizar_lista_gastos).pack(side='left', padx=5)
        
        self.tree_gastos.bind('<<TreeviewSelect>>', self.on_gasto_seleccionado)
        
        self.actualizar_lista_gastos()
    
    def on_gasto_seleccionado(self, event):
        pass
    
    def toggle_seleccion_todos_gastos(self):
        seleccionar = self.seleccionar_todos_gastos.get()
        for item in self.tree_gastos.get_children():
            if seleccionar:
                self.tree_gastos.selection_add(item)
            else:
                self.tree_gastos.selection_remove(item)
    
    def eliminar_gastos_seleccionados(self):
        seleccion = self.tree_gastos.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione al menos un gasto para eliminar")
            return
        
        if not messagebox.askyesno("Confirmar Eliminación", 
            f"⚠️ ¿Eliminar {len(seleccion)} gasto(s) seleccionado(s)?\n\n"
            f"Esta acción no se puede deshacer."):
            return
        
        gastos_a_eliminar = []
        monto_total = 0
        for item in seleccion:
            valores = self.tree_gastos.item(item)['values']
            gasto_id = int(valores[0])
            monto = float(valores[3])
            gastos_a_eliminar.append(gasto_id)
            monto_total += monto
        
        self.gastos = [g for g in self.gastos if g.get('id') not in gastos_a_eliminar]
        self.caja_general = self.redondear(self.caja_general + monto_total)
        
        self.guardar_datos()
        self.actualizar_lista_gastos()
        self.actualizar_metricas()
        self.actualizar_info_caja()
        
        self.seleccionar_todos_gastos.set(False)
        messagebox.showinfo("Éxito", f"✅ {len(gastos_a_eliminar)} gasto(s) eliminado(s) correctamente\n💰 Se ha incrementado la caja en ${monto_total:.2f}")
    
    def registrar_gasto(self):
        concepto = self.gasto_concepto_entry.get().strip()
        monto = self.gasto_monto_entry.get().strip()
        categoria = self.gasto_categoria_combo.get()
        
        if not concepto:
            messagebox.showwarning("Error", "Ingrese un concepto para el gasto")
            return
        
        try:
            monto = float(monto)
            if monto <= 0:
                raise ValueError
        except:
            messagebox.showwarning("Error", "Ingrese un monto válido")
            return
        
        if self.caja_general < monto:
            if not messagebox.askyesno("Fondos Insuficientes", 
                f"⚠️ El monto del gasto (${monto:.2f}) excede el saldo disponible (${self.caja_general:.2f}).\n\n"
                f"¿Desea registrar el gasto de todos modos (saldo negativo)?"):
                return
        
        gasto_id = max([g.get('id', 0) for g in self.gastos]) + 1 if self.gastos else 1
        
        gasto = {
            "id": gasto_id,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "concepto": concepto,
            "monto": monto,
            "categoria": categoria,
            "usuario": self.usuario_actual
        }
        
        self.gastos.append(gasto)
        self.caja_general = self.redondear(self.caja_general - monto)
        
        self.registrar_movimiento_caja("egreso", f"Gasto: {concepto}", monto)
        
        self.guardar_datos()
        self.actualizar_lista_gastos()
        self.actualizar_metricas()
        self.actualizar_info_caja()
        self.actualizar_movimientos_caja()
        
        self.gasto_concepto_entry.delete(0, tk.END)
        self.gasto_monto_entry.delete(0, tk.END)
        
        messagebox.showinfo("Éxito", 
            f"✅ Gasto registrado correctamente\n\n"
            f"📌 Concepto: {concepto}\n"
            f"💰 Monto: ${monto:.2f}\n"
            f"📁 Categoría: {categoria}\n"
            f"💰 Saldo en caja: ${self.caja_general:.2f}")
    
    def actualizar_lista_gastos(self):
        for item in self.tree_gastos.get_children():
            self.tree_gastos.delete(item)
        
        for gasto in sorted(self.gastos, key=lambda x: x.get('fecha', ''), reverse=True)[:50]:
            self.tree_gastos.insert("", "end", values=(
                gasto.get('id', ''),
                gasto.get('fecha', '')[:16],
                gasto.get('concepto', ''),
                f"{gasto.get('monto', 0):.2f}",
                gasto.get('categoria', ''),
                gasto.get('usuario', '')
            ))
        
        self.seleccionar_todos_gastos.set(False)
    
    def eliminar_gasto(self):
        seleccion = self.tree_gastos.selection()
        if not seleccion:
            messagebox.showwarning("Error", "Seleccione un gasto para eliminar")
            return
        
        item = seleccion[0]
        item_data = self.tree_gastos.item(item)
        valores = item_data['values']
        gasto_id = int(valores[0])
        monto = float(valores[3])
        
        if messagebox.askyesno("Confirmar", 
            f"⚠️ ¿Eliminar el gasto #{gasto_id}?\n\n"
            f"📌 Concepto: {valores[2]}\n"
            f"💰 Monto: ${monto:.2f}\n\n"
            f"El saldo de caja se incrementará en ${monto:.2f}"):
            
            self.gastos = [g for g in self.gastos if g.get('id') != gasto_id]
            self.caja_general = self.redondear(self.caja_general + monto)
            
            self.guardar_datos()
            self.actualizar_lista_gastos()
            self.actualizar_metricas()
            self.actualizar_info_caja()
            
            messagebox.showinfo("Éxito", "Gasto eliminado correctamente")
    
    # ==================== TAB MÉTRICAS ====================
    
    def crear_tab_metricas(self):
        frame_resumen = ttk.LabelFrame(self.tab_metricas, text="📊 Resumen General")
        frame_resumen.pack(pady=8, padx=8, fill='x')
        
        self.labels_metricas = {}
        metricas = [
            ("💰 Caja General", "caja_general"),
            ("👥 Fondo Salarios", "fondo_salarios"),
            ("📦 Total Stock", "total_stock"),
            ("💎 Valor Total Inventario", "valor_inventario"),
            ("📊 Total Materiales", "total_materiales"),
            ("💰 Inversión Total", "inversion_total"),
            ("💵 Total Ventas", "total_ventas"),
            ("💰 Ganancia Potencial", "ganancia_potencial"),
            ("📈 Total Gastos", "total_gastos"),
            ("📋 Total Remisiones", "total_remisiones"),
            ("📊 Pos Venta Total", "pos_venta_total")
        ]
        
        for i, (nombre, key) in enumerate(metricas):
            row = i // 3
            col = i % 3
            frame_metric = ttk.Frame(frame_resumen, relief='ridge', borderwidth=1)
            frame_metric.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            
            ttk.Label(frame_metric, text=nombre, font=("Arial", 10, "bold")).pack(pady=2)
            label_valor = ttk.Label(frame_metric, text="$0.00", font=("Arial", 12, "bold"), foreground="blue")
            label_valor.pack(pady=2)
            self.labels_metricas[key] = label_valor
        
        ttk.Button(frame_resumen, text="🔄 Actualizar Métricas", command=self.actualizar_metricas).grid(
            row=len(metricas)//3 + 1, column=0, columnspan=3, pady=10)
        
        frame_categorias = ttk.LabelFrame(self.tab_metricas, text="📊 Resumen por Categoría")
        frame_categorias.pack(pady=8, padx=8, fill='x')
        
        self.labels_categoria_metricas = {}
        categorias = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"]
        for i, cat in enumerate(categorias):
            frame_cat = ttk.Frame(frame_categorias, relief='ridge', borderwidth=1)
            frame_cat.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            
            ttk.Label(frame_cat, text=cat.upper(), font=("Arial", 10, "bold")).pack(pady=2)
            label_stock = ttk.Label(frame_cat, text="Stock: 0.00 kg", font=("Arial", 9))
            label_stock.pack()
            label_valor = ttk.Label(frame_cat, text="Valor: $0.00", font=("Arial", 9, "bold"), foreground="green")
            label_valor.pack()
            label_inversion = ttk.Label(frame_cat, text="Inversión: $0.00", font=("Arial", 9), foreground="blue")
            label_inversion.pack()
            label_ganancia = ttk.Label(frame_cat, text="Ganancia: $0.00", font=("Arial", 9), foreground="purple")
            label_ganancia.pack()
            
            self.labels_categoria_metricas[cat] = {
                "stock": label_stock,
                "valor": label_valor,
                "inversion": label_inversion,
                "ganancia": label_ganancia
            }
        
        frame_categorias.grid_columnconfigure(0, weight=1)
        frame_categorias.grid_columnconfigure(1, weight=1)
        frame_categorias.grid_columnconfigure(2, weight=1)
        frame_categorias.grid_columnconfigure(3, weight=1)
        frame_categorias.grid_columnconfigure(4, weight=1)
        frame_categorias.grid_columnconfigure(5, weight=1)
        
        self.actualizar_metricas()
    
    def actualizar_metricas(self):
        total_stock = sum(d.get("stock", 0) for d in self.inventario.values())
        total_valor = sum(self.redondear(d.get("stock", 0) * d.get("precio_venta", 0)) for d in self.inventario.values())
        total_inversion = sum(d.get("inversion_total", 0) for d in self.inventario.values())
        total_materiales = len(self.inventario)
        total_ventas = sum(v.get("total", 0) for v in self.ventas)
        total_gastos = sum(g.get("monto", 0) for g in self.gastos)
        total_remisiones = len(self.remisiones_generadas)
        total_pos_venta = sum(v.get("total", 0) for v in self.ventas_simuladas)
        
        ganancia_potencial = 0
        for material, datos in self.inventario.items():
            stock = datos.get("stock", 0)
            precio_venta = datos.get("precio_venta", 0)
            ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
            if stock > 0:
                ganancia_potencial += self.redondear(stock * ganancia_por_kg)
        
        self.labels_metricas["caja_general"].config(text=f"${self.caja_general:.2f}")
        self.labels_metricas["fondo_salarios"].config(text=f"${self.fondo_salarios:.2f}")
        self.labels_metricas["total_stock"].config(text=f"{total_stock:.2f} kg")
        self.labels_metricas["valor_inventario"].config(text=f"${total_valor:.2f}")
        self.labels_metricas["total_materiales"].config(text=f"{total_materiales}")
        self.labels_metricas["inversion_total"].config(text=f"${total_inversion:.2f}")
        self.labels_metricas["total_ventas"].config(text=f"${total_ventas:.2f}")
        self.labels_metricas["ganancia_potencial"].config(text=f"${ganancia_potencial:.2f}", 
                                                         foreground="green" if ganancia_potencial > 0 else "red")
        self.labels_metricas["total_gastos"].config(text=f"${total_gastos:.2f}")
        self.labels_metricas["total_remisiones"].config(text=f"{total_remisiones}")
        self.labels_metricas["pos_venta_total"].config(text=f"${total_pos_venta:.2f}", 
                                                       foreground="blue" if total_pos_venta > 0 else "gray")
        
        categorias = ["ferrosos", "plasticos", "electronicos", "papel", "por_pieza", "pos_venta"]
        for cat in categorias:
            stock_cat = 0
            valor_cat = 0
            inversion_cat = 0
            ganancia_cat = 0
            
            for material, datos in self.inventario.items():
                if datos.get("seccion") == cat:
                    stock = datos.get("stock", 0)
                    precio_venta = datos.get("precio_venta", 0)
                    stock_cat += stock
                    valor_cat += self.redondear(stock * precio_venta)
                    inversion_cat += datos.get("inversion_total", 0)
                    ganancia_por_kg = self.calcular_ganancia(material, precio_venta)
                    if stock > 0:
                        ganancia_cat += self.redondear(stock * ganancia_por_kg)
            
            if cat in self.labels_categoria_metricas:
                self.labels_categoria_metricas[cat]["stock"].config(text=f"Stock: {stock_cat:.2f} kg")
                self.labels_categoria_metricas[cat]["valor"].config(text=f"Valor: ${valor_cat:.2f}")
                self.labels_categoria_metricas[cat]["inversion"].config(text=f"Inversión: ${inversion_cat:.2f}")
                self.labels_categoria_metricas[cat]["ganancia"].config(
                    text=f"Ganancia: ${ganancia_cat:.2f}",
                    foreground="green" if ganancia_cat > 0 else "red"
                )

# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaReciclaje(root)
    root.mainloop()