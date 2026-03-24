import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# 1. CONEXIÓN (Mantenemos tus credenciales)
URL = "https://lxxpndevdmknsukkdwse.supabase.co"
KEY = "sb_publishable_0-qVhWfRx20xsATZV0BGTg_R2aAzDMv"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Control Aguacate - Francisco", layout="wide")

def obtener_datos(tabla):
    try:
        res = supabase.table(tabla).select("*").execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al conectar con {tabla}: {e}")
        return pd.DataFrame()

def insertar_dato(tabla, registro):
    try:
        supabase.table(tabla).insert(registro).execute()
        st.success("✅ Guardado correctamente")
        st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

def actualizar_dato(tabla, id_reg, registro):
    try:
        supabase.table(tabla).update(registro).eq("id", id_reg).execute()
        st.success("🔄 Actualizado correctamente")
        st.rerun()
    except Exception as e:
        st.error(f"Error al actualizar: {e}")

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("🥑 Control Aguacate")
    menu = st.radio("Seleccione Módulo:", [
        "📊 Dashboard", "📦 Inventario", "🛒 Compras", "🚜 Registro de Uso",
        "👷 Actividades Ejecutadas", "📅 Planeación EDT", "💸 Gastos Operativos", "💰 Ventas Cosecha"
    ])

# --- MÓDULO 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Panel de Control y Análisis Financiero")
    df_inv = obtener_datos("inventario")
    df_c = obtener_datos("compras")
    df_u = obtener_datos("registro_uso")
    if not df_c.empty: df_c['fecha'] = pd.to_datetime(df_c['fecha'])
    if not df_u.empty: df_u['fecha'] = pd.to_datetime(df_u['fecha'])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Filtros de Tiempo")
    f_inicio = st.sidebar.date_input("Fecha Inicio", value=pd.to_datetime("2024-01-01"))
    f_fin = st.sidebar.date_input("Fecha Fin", value=datetime.now())
    
    df_c_fil = df_c[(df_c['fecha'].dt.date >= f_inicio) & (df_c['fecha'].dt.date <= f_fin)] if not df_c.empty else df_c
    df_u_fil = df_u[(df_u['fecha'].dt.date >= f_inicio) & (df_u['fecha'].dt.date <= f_fin)] if not df_u.empty else df_u
    
    c1, c2, c3 = st.columns(3)
    inv_total = df_c_fil['valor_total'].sum() if not df_c_fil.empty else 0
    inv_usada = 0
    if not df_u_fil.empty and not df_inv.empty:
        df_u_c = pd.merge(df_u_fil, df_inv[['producto', 'costo_unitario']], on='producto', how='left').fillna(0)
        col_uso = 'total_usado_kg_l' if 'total_usado_kg_l' in df_u_c.columns else 'total_used_kg_l'
        inv_usada = (df_u_c[col_uso] * df_u_c['costo_unitario']).sum()
    
    inv_stock = inv_total - inv_usada
    c1.metric("💰 Inversión Total", f"$ {inv_total:,.0f}")
    c2.metric("🚜 Inversión Usada", f"$ {inv_usada:,.0f}")
    c3.metric("📦 Inversión en Stock", f"$ {inv_stock:,.0f}")
    
    st.divider()
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📦 Comprado Vs Usado")
        if not df_c_fil.empty:
            comp = df_c_fil.groupby('producto')['total_neto_ingresado'].sum()
            col_u = 'total_usado_kg_l' if 'total_usado_kg_l' in df_u_fil.columns else 'total_used_kg_l'
            uso = df_u_fil.groupby('producto')[col_u].sum() if not df_u_fil.empty else pd.Series()
            df_comp = pd.DataFrame({'Comprado': comp, 'Usado': uso}).fillna(0)
            st.bar_chart(df_comp)
    with col_g2:
        st.subheader("📈 Curva S (Inversión Acumulada)")
        if not df_c_fil.empty:
            df_s = df_c_fil.sort_values('fecha')
            df_s['Acumulado'] = df_s['valor_total'].cumsum()
            st.line_chart(df_s.set_index('fecha')['Acumulado'])
    
    st.divider()
    # RECUPERADO: El aviso de abajo
    st.info("💡 Los gráficos de 'Ventas' y 'Planeado Vs Ejecutado' se activarán cuando integremos las tablas de Cosecha y Presupuesto.")


# --- MÓDULO 2: INVENTARIO ---
elif menu == "📦 Inventario":
    st.title("📦 Inventario y Valoración Real")
    df_inv_base = obtener_datos("inventario")
    df_c = obtener_datos("compras")
    df_u = obtener_datos("registro_uso")
    
    if not df_inv_base.empty:
        res_c = df_c.groupby('producto')['total_neto_ingresado'].sum().reset_index() if not df_c.empty else pd.DataFrame(columns=['producto', 'total_neto_ingresado'])
        col_u = 'total_usado_kg_l' if 'total_usado_kg_l' in df_u.columns else 'total_used_kg_l'
        res_u = df_u.groupby('producto')[col_u].sum().reset_index() if not df_u.empty else pd.DataFrame(columns=['producto', col_u])
        
        df_final = pd.merge(df_inv_base[['producto', 'presentacion', 'unidad', 'costo_unitario']], res_c, on='producto', how='left').fillna(0)
        df_final = pd.merge(df_final, res_u, on='producto', how='left').fillna(0)
        
        df_final['saldo_real'] = df_final['total_neto_ingresado'] - df_final[col_u]
        df_final['inv_stock'] = df_final['saldo_real'] * df_final['costo_unitario']
        df_final['inv_usada'] = df_final[col_u] * df_final['costo_unitario']
        df_final['alerta'] = df_final['saldo_real'].apply(lambda x: "🚨 AGOTADO" if x <= 0 else ("⚠️ BAJO" if x < 5 else "✅ OK"))

        # --- AQUÍ ES DONDE DEFINIMOS EL ORDEN (cols) ---
        columnas_ordenadas = [
            'producto', 'presentacion', 'unidad', 'costo_unitario', 
            'total_neto_ingresado', col_u, 'saldo_real', 
            'inv_stock', 'inv_usada', 'alerta'
        ]
        
        # Mostramos solo las columnas en el orden de la lista anterior
        st.dataframe(df_final[columnas_ordenadas].rename(columns={
            'producto': 'Producto', 
            'presentacion': 'Presentación', 
            'unidad': 'Unidad',
            'total_neto_ingresado': 'Entradas Totales', 
            col_u: 'Salidas Totales',
            'saldo_real': 'SALDO REAL', 
            'alerta': 'Alerta', 
            'costo_unitario': 'Costo Unitario',
            'inv_stock': 'Inversión Stock', 
            'inv_usada': 'Inversión Usada'
        }), use_container_width=True, hide_index=True)

# --- MÓDULO 3: COMPRAS (RECUPERADO LAS 2 COLUMNAS) ---
elif menu == "🛒 Compras":
    st.title("🛒 Historial de Compras")
    df_c = obtener_datos("compras")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        with st.expander("➕ Registrar Nueva Compra"):
            with st.form("form_nueva_compra"):
                f = st.date_input("Fecha"); p = st.text_input("Producto")
                can = st.number_input("Cantidad", min_value=0.0); pre = st.text_input("Presentación")
                und = st.text_input("Unidad"); pes = st.number_input("Peso/Vol x Unidad", min_value=0.0)
                v_u = st.number_input("Valor Unitario", min_value=0.0)
                if st.form_submit_button("Guardar"):
                    insertar_dato("compras", {"fecha": str(f), "producto": p, "cantidad_comprada": can, "presentacion": pre, "unidad": und, "peso_vol_unidad": pes, "valor_unitario": v_u, "valor_total": can * v_u, "total_neto_ingresado": can * pes})
    with col_btn2:
        with st.expander("✏️ Editar Registro"):
            if not df_c.empty:
                df_c['selec'] = df_c['id'].astype(str) + " | " + df_c['producto']
                id_edit = st.selectbox("Seleccione para editar", df_c['selec'])
                sel = df_c[df_c['selec'] == id_edit].iloc[0]
                with st.form("form_edit_compra"):
                    f_e = st.date_input("Fecha", value=pd.to_datetime(sel['fecha']))
                    p_e = st.text_input("Producto", value=sel['producto'])
                    c_e = st.number_input("Cantidad", value=float(sel['cantidad_comprada']))
                    v_e = st.number_input("Valor Unitario", value=float(sel['valor_unitario']))
                    if st.form_submit_button("Actualizar"):
                        actualizar_dato("compras", int(sel['id']), {"fecha": str(f_e), "producto": p_e, "cantidad_comprada": c_e, "valor_unitario": v_e, "valor_total": c_e * v_e})
    if not df_c.empty:
        st.dataframe(df_c[['fecha', 'producto', 'cantidad_comprada', 'presentacion', 'unidad', 'peso_vol_unidad', 'valor_unitario', 'valor_total', 'total_neto_ingresado']], use_container_width=True, hide_index=True)

# --- MÓDULO 4: REGISTRO DE USO (RECUPERADO LAS 2 COLUMNAS) ---
elif menu == "🚜 Registro de Uso":
    st.title("🚜 Registro de Aplicaciones")
    df_u = obtener_datos("registro_uso")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        with st.expander("➕ Registrar Nuevo Uso"):
            with st.form("form_nuevo_uso"):
                f_u = st.date_input("Fecha"); p_u = st.text_input("Producto")
                d_u = st.number_input("Dosis Unitaria", min_value=0.0); n_u = st.number_input("Número de Dosis", min_value=0.0); obs = st.text_area("Observaciones")
                if st.form_submit_button("Guardar"):
                    insertar_dato("registro_uso", {"fecha": str(f_u), "producto": p_u, "dosis_unitaria": d_u, "numero_de_dosis": n_u, "total_usado_kg_l": d_u * n_u, "observaciones": obs})
    with col_u2:
        with st.expander("✏️ Editar Registro"):
            if not df_u.empty:
                df_u['selec'] = df_u['id'].astype(str) + " | " + df_u['producto']
                id_u_edit = st.selectbox("Seleccione para editar", df_u['selec'])
                sel_u = df_u[df_u['selec'] == id_u_edit].iloc[0]
                with st.form("form_edit_uso"):
                    f_ue = st.date_input("Fecha", value=pd.to_datetime(sel_u['fecha']))
                    p_ue = st.text_input("Producto", value=sel_u['producto'])
                    d_ue = st.number_input("Dosis", value=float(sel_u['dosis_unitaria']))
                    n_ue = st.number_input("Nº Dosis", value=float(sel_u['numero_de_dosis']))
                    if st.form_submit_button("Actualizar"):
                        actualizar_dato("registro_uso", int(sel_u['id']), {"fecha": str(f_ue), "producto": p_ue, "dosis_unitaria": d_ue, "numero_de_dosis": n_ue, "total_usado_kg_l": d_ue * n_ue})
    if not df_u.empty:
        col_u = 'total_usado_kg_l' if 'total_usado_kg_l' in df_u.columns else 'total_used_kg_l'
        st.dataframe(df_u[['fecha', 'producto', 'presentacion', 'unidad', 'dosis_unitaria', 'numero_de_dosis', col_u, 'observaciones']], use_container_width=True, hide_index=True)

# --- MÓDULO 5: ACTIVIDADES EJECUTADAS (CON 2 COLUMNAS) ---
elif menu == "👷 Actividades Ejecutadas":
    st.title("👷 Actividades Ejecutadas")
    df_ae = obtener_datos("actividades_ejecutadas")
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("➕ Nueva Actividad"):
            with st.form("n_ae"):
                f = st.date_input("Fecha"); t = st.text_input("Trabajador"); l = st.text_input("Labor")
                lot = st.text_input("Lote"); hj = st.number_input("Horas/Jornales", min_value=0.0); obs = st.text_area("Notas")
                if st.form_submit_button("Guardar"):
                    insertar_dato("actividades_ejecutadas", {"fecha":str(f),"trabajador":t,"labor":l,"lote":lot,"horas_jornales":hj,"observaciones":obs})
    with col2:
        with st.expander("✏️ Editar Actividad"):
            if not df_ae.empty:
                df_ae['selec'] = df_ae['id'].astype(str) + " | " + df_ae['labor']
                id_ae = st.selectbox("Seleccione para editar", df_ae['selec'])
                sel_ae = df_ae[df_ae['selec'] == id_ae].iloc[0]
                with st.form("e_ae"):
                    f_e = st.date_input("Fecha", value=pd.to_datetime(sel_ae['fecha']))
                    l_e = st.text_input("Labor", value=sel_ae['labor'])
                    if st.form_submit_button("Actualizar"):
                        actualizar_dato("actividades_ejecutadas", int(sel_ae['id']), {"fecha":str(f_e), "labor":l_e})
    st.dataframe(df_ae, use_container_width=True, hide_index=True)

# --- MÓDULO 6: PLANEACIÓN EDT ---
elif menu == "📅 Planeación EDT":
    st.title("📅 Planeación EDT")
    df_edt = obtener_datos("plan_de_actividades_edt")
    
    if not df_edt.empty:
        # 1. Procesamiento de Fechas
        col_f = next((c for c in df_edt.columns if 'fecha' in c.lower()), None)
        
        if col_f:
            df_edt[col_f] = pd.to_datetime(df_edt[col_f])
            df_edt['semana_num'] = df_edt[col_f].dt.isocalendar().week
            
            # --- MEJORA: Selector Descriptivo ---
            semanas_unicas = sorted(df_edt['semana_num'].unique())
            # Creamos una lista de textos: ["Semana 11", "Semana 12"...]
            opciones_mostrar = [f"📅 Semana {int(s)}" for s in semanas_unicas]
            
            # Diccionario para convertir el texto de vuelta al número
            dict_semanas = dict(zip(opciones_mostrar, semanas_unicas))
            
            seleccion = st.selectbox("📅 Seleccione el período de trabajo:", opciones_mostrar)
            
            # Filtramos por el número real de la semana
            semana_real = dict_semanas[seleccion]
            df_vista = df_edt[df_edt['semana_num'] == semana_real].copy()
        else:
            df_vista = df_edt.copy()

        # 2. Formularios de Acción
        c_edt1, c_edt2 = st.columns(2)
        with c_edt1:
            with st.expander("➕ Nueva Tarea"):
                with st.form("f_n_edt_final"):
                    l_n = st.text_input("Labor")
                    d_n = st.text_input("Descripción")
                    f_i = st.date_input("Fecha Inicio")
                    est = st.selectbox("Estado", ["Planificado", "Pendiente", "En Proceso", "Completado"])
                    if st.form_submit_button("Guardar"):
                        insertar_dato("plan_de_actividades_edt", {"labor": l_n, "descripcion": d_n, "fecha_inicio": str(f_i), "estado": est})
                        st.rerun()
        
        with c_edt2:
            with st.expander("✏️ Editar Estado"):
                if 'labor' in df_edt.columns:
                    # Buscador por nombre de labor
                    opciones_l = df_edt['labor'].unique().tolist()
                    sel_l = st.selectbox("Tarea a editar", opciones_l)
                    fila_l = df_edt[df_edt['labor'] == sel_l].iloc[0]
                    with st.form("f_e_edt_final"):
                        est_e = st.selectbox("Nuevo Estado", ["Planificado", "Pendiente", "En Proceso", "Completado"])
                        if st.form_submit_button("Actualizar"):
                            actualizar_dato("plan_de_actividades_edt", int(fila_edt['id']), {"estado": est_e})
                            st.rerun()

        # 3. Vista de la Tabla Limpia
        columnas_finales = ['labor', 'descripcion', 'fecha_inicio', 'estado']
        existentes = [c for c in columnas_finales if c in df_vista.columns]
        
        st.dataframe(df_vista[existentes].rename(columns={
            'labor': 'Labor', 'descripcion': 'Descripción', 
            'fecha_inicio': 'Fecha Inicio', 'estado': 'Estado'
        }), use_container_width=True, hide_index=True)

    else:
        st.info("No hay actividades registradas.")

# --- MÓDULO 7: GASTOS OPERATIVOS ---
elif menu == "💸 Gastos Operativos":
    st.title("💸 Gastos Operativos")
    df_go = obtener_datos("gastos_operativos")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("➕ Nuevo Gasto"):
            with st.form("n_go_v2"):
                f = st.date_input("Fecha")
                con = st.text_input("Concepto")
                lab = st.text_input("Labor")
                ben = st.text_input("Beneficiario")
                val = st.number_input("Valor", min_value=0.0)
                obs = st.text_area("Observaciones")
                if st.form_submit_button("Guardar Gasto"):
                    insertar_dato("gastos_operativos", {
                        "fecha": str(f), "concepto": con, "labor": lab, 
                        "beneficiario": ben, "valor": val, "observaciones": obs
                    })
                    st.success("Gasto registrado")
                    st.rerun()
    
    with col2:
        with st.expander("✏️ Editar Gasto"):
            if not df_go.empty:
                # Buscador con ID corto y Concepto
                df_go['selec'] = df_go['id'].astype(str).str[:8] + " | " + df_go['concepto'].fillna("")
                sel_id = st.selectbox("Seleccione Gasto para editar", df_go['selec'])
                fila = df_go[df_go['selec'] == sel_id].iloc[0]
                
                with st.form("e_go_v2"):
                    f_e = st.date_input("Fecha", value=pd.to_datetime(fila['fecha']))
                    con_e = st.text_input("Concepto", value=fila['concepto'])
                    val_e = st.number_input("Valor", value=float(fila['valor']))
                    if st.form_submit_button("Actualizar Gasto"):
                        actualizar_dato("gastos_operativos", int(fila['id']), {
                            "fecha": str(f_e), "concepto": con_e, "valor": val_e
                        })
                        st.success("Gasto actualizado")
                        st.rerun()

    if not df_go.empty:
        # --- FILTRO DE COLUMNAS PARA LA VISTA ---
        # Definimos solo las columnas que quieres ver
        columnas_interes = ['fecha', 'concepto', 'labor', 'beneficiario', 'valor', 'observaciones']
        
        # Filtramos las que existan en el DataFrame
        existentes = [c for c in columnas_interes if c in df_go.columns]
        
        st.dataframe(df_go[existentes].rename(columns={
            'fecha': 'Fecha', 'concepto': 'Concepto', 'labor': 'Labor',
            'beneficiario': 'Beneficiario', 'valor': 'Valor ($)', 'observaciones': 'Observaciones'
        }), use_container_width=True, hide_index=True)
    else:
        st.info("No hay gastos operativos registrados.")

# --- MÓDULO 8: VENTAS COSECHA ---
elif menu == "💰 Ventas Cosecha":
    st.title("💰 Ventas Cosecha")
    df_vc = obtener_datos("ventas_cosecha")
    
    c_v1, c_v2 = st.columns(2)
    with c_v1:
        with st.expander("➕ Registrar Venta"):
            with st.form("f_n_v"):
                f = st.date_input("Fecha")
                cli = st.text_input("Cliente")
                cal = st.selectbox("Calibre", ["12-14", "16-18", "20-22", "24", "Descarte"])
                kil = st.number_input("Kilos", min_value=0.0)
                pre = st.number_input("Precio x Kilo", min_value=0.0)
                ded = st.number_input("Deducciones (Transporte/Otros)", min_value=0.0)
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button("Guardar Venta"):
                    # Cálculos automáticos
                    sub = kil * pre
                    net = sub - ded
                    insertar_dato("ventas_cosecha", {
                        "fecha": str(f), "cliente": cli, "calibre": cal, 
                        "kilos": kil, "precio_por_kilo": pre, "deducciones": ded,
                        "subtotal": sub, "total_neto": net, "observaciones": obs
                    })
                    st.success("Venta registrada con éxito")
                    st.rerun()
    
    with c_v2:
        with st.expander("✏️ Editar Venta"):
            if not df_vc.empty:
                df_vc['selec'] = df_vc['id'].astype(str).str[:8] + " | " + df_vc['cliente'].fillna("S/N")
                sel_v = st.selectbox("Venta a editar", df_vc['selec'])
                fila_v = df_vc[df_vc['selec'] == sel_v].iloc[0]
                with st.form("f_e_v"):
                    cli_e = st.text_input("Cliente", value=str(fila_v['cliente']))
                    # Puedes agregar aquí más campos para editar si lo necesitas
                    if st.form_submit_button("Actualizar"):
                        actualizar_dato("ventas_cosecha", fila_v['id'], {"cliente": cli_e})
                        st.rerun()

    if not df_vc.empty:
        # --- DEFINICIÓN DEL ORDEN DE COLUMNAS SOLICITADO ---
        orden_columnas = [
            'fecha', 'cliente', 'calibre', 'kilos', 
            'precio_por_kilo', 'deducciones', 'subtotal', 
            'total_neto', 'observaciones'
        ]
        
        # Filtramos solo las que existan en el DF para evitar errores
        columnas_finales = [c for c in orden_columnas if c in df_vc.columns]
        
        # Mostramos la tabla con los nombres limpios
        st.dataframe(df_vc[columnas_finales].rename(columns={
            'fecha': 'Fecha', 'cliente': 'Cliente', 'calibre': 'Calibre',
            'kilos': 'Kilos', 'precio_por_kilo': 'Precio/Kg', 
            'deducciones': 'Deducciones', 'subtotal': 'Subtotal',
            'total_neto': 'Total Neto', 'observaciones': 'Observaciones'
        }), use_container_width=True, hide_index=True)