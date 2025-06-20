# -*- coding: utf-8 -*-
# Python For Dynamo Script
# Autor: Asistente de IA (basado en especificaciones)
# Versión: 1.0
# Fecha: 2023-12-14
# Propósito: Leer datos de espacios desde Excel, calcular un layout 2D heurístico,
# y generar masas 3D (Solid) en Dynamo usando ProtoGeometry.

# --- Importaciones Necesarias ---
import clr
import sys
import json
import collections # Usado en calcular_layout_espacios

# Añadir referencias a ProtoGeometry para geometría de Dynamo
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import Point, Vector, CoordinateSystem, Rectangle, Solid

# Importar System.Exception para un manejo de errores más específico si es necesario
from System import Exception as DotNetException

# (Opcional) Referencia a la API de Revit, aunque no se usa directamente para crear elementos en DB.
# clr.AddReference('RevitAPI')
# import Autodesk
# from Autodesk.Revit.DB import *

# (Opcional) Referencia a Servicios de Revit para transacciones si se modificara el documento.
# clr.AddReference("RevitServices")
# import RevitServices
# from RevitServices.Persistence import DocumentManager
# from RevitServices.Transactions import TransactionManager

# --- Dependencia Externa ---
# Esta sección del script (leer_datos_espacios_excel) depende de la librería 'openpyxl'.
# Asegúrese de que 'openpyxl' está instalada en el entorno Python que Dynamo está utilizando.
# Puede ser CPython3 si el nodo está configurado así, o IronPython (más antiguo).
# Para CPython3 en Dynamo, puede instalar paquetes vía pip.
try:
    import openpyxl
except ImportError:
    # No se puede asignar a OUT directamente aquí, se maneja en la lógica principal.
    # Esta es una forma de señalar el problema temprano si se ejecuta fuera de la lógica principal.
    # sys.stderr.write("Error: La librería 'openpyxl' es necesaria y no se encontró.\n")
    # raise # Re-lanzar la excepción para que Dynamo la capture si es posible
    pass # El error se manejará en la lógica principal del script

# --- Función 1: Leer Datos de Espacios desde Excel ---
def leer_datos_espacios_excel(ruta_archivo_excel: str) -> list[dict]:
    """
    Lee los datos de espacios desde un archivo Excel.

    Args:
        ruta_archivo_excel: La ruta al archivo Excel (.xlsx).

    Returns:
        Una lista de diccionarios, donde cada diccionario representa un espacio.
        Devuelve una lista vacía si ocurre un error crítico.
    """
    if 'openpyxl' not in sys.modules:
        # Si openpyxl no se importó, no podemos continuar con esta función.
        # El error se imprimirá en la lógica principal del script de Dynamo.
        raise ImportError("La librería 'openpyxl' es necesaria para leer archivos Excel y no está disponible.")

    datos_espacios = []
    try:
        workbook = openpyxl.load_workbook(ruta_archivo_excel, data_only=True) # data_only para obtener valores de fórmulas
        sheet = workbook.active

        headers_row = sheet[1]
        headers = [cell.value for cell in headers_row]

        expected_headers = ["Código del espacio", "Nombre del ambiente", "Área", "Longitud", "Ancho", "Altura"]
        # Validar que los encabezados mínimos estén, aunque no todos se usan directamente en el layout.
        if not all(header in headers for header in ["Código del espacio", "Longitud", "Ancho", "Altura"]):
            # sys.stderr.write("Error: El archivo Excel no contiene los encabezados esperados (Código del espacio, Longitud, Ancho, Altura).\n")
            # En Dynamo, es mejor devolver un error que pueda ir a OUT.
            raise ValueError("El archivo Excel no contiene los encabezados esperados (Código del espacio, Longitud, Ancho, Altura).")

        header_to_index = {header: i for i, header in enumerate(headers)}
        columnas_numericas = ["Área", "Longitud", "Ancho", "Altura"] # Columnas a convertir a float

        for row_num in range(2, sheet.max_row + 1):
            row_data = {}
            current_row_values = sheet[row_num]
            valid_row = True
            for header_name in headers: # Iterar sobre los encabezados encontrados en el archivo
                if header_name not in header_to_index: continue # Saltar si el encabezado no tiene índice (raro)

                cell = current_row_values[header_to_index[header_name]]
                cell_value = cell.value

                if header_name in columnas_numericas:
                    if cell_value is not None and not isinstance(cell_value, (int, float)):
                        try:
                            # Intentar convertir valores que parecen números pero son strings
                            row_data[header_name] = float(str(cell_value).strip())
                        except ValueError:
                            # sys.stderr.write(f"Advertencia: No se pudo convertir '{cell_value}' a número para '{header_name}' en fila {row_num}. Se usará None.\n")
                            row_data[header_name] = None
                    elif isinstance(cell_value, (int, float)):
                        row_data[header_name] = float(cell_value)
                    else: # cell_value es None o no convertible
                        row_data[header_name] = None
                else:
                    row_data[header_name] = cell_value

            # Asegurar que las dimensiones clave para el layout y la masa existan
            if any(row_data.get(dim) is None for dim in ["Longitud", "Ancho", "Altura"]):
                # sys.stderr.write(f"Advertencia: Fila {row_num} omitida por falta de Longitud, Ancho o Altura.\n")
                continue # Omitir esta fila si faltan dimensiones esenciales

            datos_espacios.append(row_data)

    except FileNotFoundError:
        raise FileNotFoundError(f"Error: No se encontró el archivo Excel en: {ruta_archivo_excel}")
    except DotNetException as e_dotnet: # Capturar excepciones específicas de .NET/IronPython si es relevante
        raise Exception(f"Error de .NET al procesar Excel: {str(e_dotnet)}")
    except Exception as e_general: # Capturar excepciones generales de Python
        raise Exception(f"Error general al procesar Excel: {str(e_general)}")

    return datos_espacios

# --- Función 2: Chequeo de Solapamiento de Rectángulos ---
def check_overlap(x1: float, y1: float, l1: float, w1: float,
                  x2: float, y2: float, l2: float, w2: float) -> bool:
    """Comprueba si dos rectángulos 2D (definidos por esquina inf-izq, longitud, ancho) se solapan."""
    rect1_x_fin, rect1_y_fin = x1 + l1, y1 + w1
    rect2_x_fin, rect2_y_fin = x2 + l2, y2 + w2
    no_overlap = (rect1_x_fin <= x2 or rect1_x_fin <= rect2_x_inicio or # Corrección aquí
                  x1 >= rect2_x_fin or rect1_x_inicio >= rect2_x_fin or # Corrección aquí
                  rect1_y_fin <= y2 or rect1_y_fin <= rect2_y_inicio or # Corrección aquí
                  y1 >= rect2_y_fin or rect1_y_inicio >= rect2_y_fin) # Corrección aquí
    # Corregido:
    no_overlap = (rect1_x_fin <= x2 or # R1 está completamente a la izquierda de R2
                  x1 >= x2 + l2 or    # R1 está completamente a la derecha de R2
                  rect1_y_fin <= y2 or # R1 está completamente debajo de R2
                  y1 >= y2 + w2)       # R1 está completamente encima de R2
    return not no_overlap

# --- Función 3: Cálculo de Layout Heurístico ---
def calcular_layout_espacios(espacios_data: list[dict], relaciones_grafo: dict) -> list[dict]:
    """Calcula una disposición 2D heurística para espacios, evitando colisiones."""
    if not espacios_data: return []
    espacios_map = {esp["Código del espacio"]: esp for esp in espacios_data}

    for espacio in espacios_data:
        espacio["punto_insercion_calculado"] = (0.0, 0.0, 0.0)
        espacio["colocado"] = False

    cola_procesamiento = collections.deque()
    if espacios_data:
        espacio_inicial = espacios_data[0]
        espacio_inicial["punto_insercion_calculado"] = (0.0, 0.0, 0.0)
        espacio_inicial["colocado"] = True
        cola_procesamiento.append(espacio_inicial)

    espacios_colocados_lista = [esp for esp in espacios_data if esp["colocado"]]

    while cola_procesamiento:
        espacio_padre = cola_procesamiento.popleft()
        padre_codigo = espacio_padre["Código del espacio"]
        padre_x, padre_y, _ = espacio_padre["punto_insercion_calculado"]
        padre_longitud, padre_ancho = espacio_padre["Longitud"], espacio_padre["Ancho"]

        codigos_hijos_conectados = relaciones_grafo.get(padre_codigo, [])
        for codigo_hijo in codigos_hijos_conectados:
            espacio_hijo = espacios_map.get(codigo_hijo)
            if not espacio_hijo or espacio_hijo["colocado"]: continue

            hijo_longitud, hijo_ancho = espacio_hijo["Longitud"], espacio_hijo["Ancho"]
            if hijo_longitud is None or hijo_ancho is None or hijo_longitud <=0 or hijo_ancho <=0: continue

            # Posiciones tentativas (Derecha, Arriba, Izquierda, Abajo del padre)
            # Se pueden añadir más estrategias o un pequeño gap
            gap = 0.1 # Pequeño espacio entre geometrías, opcional
            posiciones_tentativas = [
                (padre_x + padre_longitud + gap, padre_y),
                (padre_x, padre_y + padre_ancho + gap),
                (padre_x - hijo_longitud - gap, padre_y),
                (padre_x, padre_y - hijo_ancho - gap)
            ]

            posicion_encontrada_para_hijo = False
            for tentativa_x, tentativa_y in posiciones_tentativas:
                colision_detectada = False
                for otro_espacio_colocado in espacios_colocados_lista:
                    if otro_espacio_colocado == espacio_hijo: continue # No chequear contra sí mismo (aunque no debería estar en la lista aún)

                    otro_x, otro_y, _ = otro_espacio_colocado["punto_insercion_calculado"]
                    otro_longitud, otro_ancho = otro_espacio_colocado["Longitud"], otro_espacio_colocado["Ancho"]
                    if check_overlap(tentativa_x, tentativa_y, hijo_longitud, hijo_ancho,
                                     otro_x, otro_y, otro_longitud, otro_ancho):
                        colision_detectada = True
                        break
                if not colision_detectada:
                    espacio_hijo["punto_insercion_calculado"] = (tentativa_x, tentativa_y, 0.0)
                    espacio_hijo["colocado"] = True
                    cola_procesamiento.append(espacio_hijo)
                    espacios_colocados_lista.append(espacio_hijo) # Añadir a la lista al colocarlo
                    posicion_encontrada_para_hijo = True
                    break
            # if not posicion_encontrada_para_hijo:
                # sys.stderr.write(f"Advertencia: No se pudo colocar '{codigo_hijo}'.\n")
    return espacios_data

# --- Función 4: Crear Masa Geométrica (Solid) ---
def crear_masa_revit(nombre_espacio: str, longitud: float, ancho: float, altura: float, punto_insercion: Point) -> Solid:
    """
    Crea una masa geométrica (Solid) usando ProtoGeometry.
    Args:
        nombre_espacio (str): Nombre (no usado directamente en la geometría).
        longitud (float): Dimensión X de la masa.
        ancho (float): Dimensión Y de la masa.
        altura (float): Dimensión Z de la masa.
        punto_insercion (Point): Objeto Point de ProtoGeometry, esquina base de la masa.
    Returns:
        Solid: Objeto Solid (masa) o None si hay error.
    """
    if not all(isinstance(dim, (int, float)) and dim > 0 for dim in [longitud, ancho, altura]):
        # sys.stderr.write(f"Error en crear_masa_revit para '{nombre_espacio}': Dimensiones inválidas ({longitud}, {ancho}, {altura}).\n")
        return None
    if not isinstance(punto_insercion, Point):
        # sys.stderr.write(f"Error en crear_masa_revit para '{nombre_espacio}': punto_insercion no es un Point válido.\n")
        return None

    cs, rectangulo_base, vector_extrusion, masa_solida = None, None, None, None # Para el bloque finally
    try:
        # Crear un sistema de coordenadas en el punto de inserción.
        cs = CoordinateSystem.ByOrigin(punto_insercion.X, punto_insercion.Y, punto_insercion.Z)

        # Crear un rectángulo base. Width es Y, Length es X en Rectangle.ByWidthLength.
        rectangulo_base = Rectangle.ByWidthLength(cs, ancho, longitud)

        # Extruir el rectángulo.
        vector_extrusion = Vector.ZAxis()
        masa_solida = rectangulo_base.ExtrudeAsSolid(vector_extrusion, altura)

        return masa_solida
    except DotNetException as e_dotnet_geom:
        # sys.stderr.write(f"Error de ProtoGeometry (.NET) en crear_masa_revit para '{nombre_espacio}': {str(e_dotnet_geom)}\n")
        return None
    except Exception as e_geom: # Captura otras excepciones de Python
        # sys.stderr.write(f"Error de Python en crear_masa_revit para '{nombre_espacio}': {str(e_geom)}\n")
        return None
    finally:
        # Liberar objetos intermedios de ProtoGeometry para gestionar memoria.
        # Esto es crucial en scripts de Dynamo que crean mucha geometría.
        if cs: cs.Dispose()
        if rectangulo_base: rectangulo_base.Dispose()
        if vector_extrusion: vector_extrusion.Dispose()
        # No se hace Dispose de 'punto_insercion' porque es un argumento de entrada.
        # No se hace Dispose de 'masa_solida' porque es el valor de retorno.

# --- Lógica Principal del Script de Dynamo ---
# Las entradas de Dynamo se acceden a través de la lista IN.
# IN[0]: ruta_archivo_excel (string)
# IN[1]: relaciones_json_str (string JSON)
# IN[2]: origen_global_ds (Point de Dynamo, opcional)

# Inicializar la salida de Dynamo
OUT = []
error_messages = [] # Lista para acumular errores y advertencias

try:
    # Verificar si openpyxl está disponible antes de empezar
    if 'openpyxl' not in sys.modules:
        raise ImportError("Error Crítico: La librería 'openpyxl' es necesaria y no se encontró. Instálela en su entorno Python para Dynamo.")

    # --- Leer Entradas ---
    ruta_archivo_excel = IN[0]
    relaciones_json_str = IN[1]
    origen_global_ds = IN[2] if len(IN) > 2 else None # Punto de origen global opcional

    if not isinstance(ruta_archivo_excel, str) or not ruta_archivo_excel:
        error_messages.append("Error: IN[0] debe ser una ruta de archivo Excel válida (string).")
        raise ValueError("Entrada de ruta de archivo Excel inválida.")

    if not isinstance(relaciones_json_str, str) or not relaciones_json_str:
        error_messages.append("Error: IN[1] debe ser un string JSON de relaciones válido.")
        raise ValueError("Entrada de string JSON de relaciones inválida.")

    # --- Paso 1: Leer Datos de Excel ---
    # sys.stdout.write("Paso 1: Leyendo datos de Excel...\n") # Para depuración en consola de Dynamo
    try:
        espacios_data_leidos = leer_datos_espacios_excel(ruta_archivo_excel)
    except Exception as e_excel:
        error_messages.append(f"Error en lectura de Excel: {str(e_excel)}")
        raise # Re-lanzar para que el bloque try-except principal lo maneje

    if not espacios_data_leidos:
        error_messages.append("No se leyeron datos de espacios del archivo Excel o el archivo está vacío/formato incorrecto.")
        # No necesariamente un error fatal si se quiere devolver una lista vacía de geometrías
        OUT = error_messages
        # sys.exit() # No usar sys.exit() en Dynamo, simplemente asignar a OUT.

    # --- Paso 2: Parsear Relaciones JSON ---
    # sys.stdout.write("Paso 2: Parseando relaciones JSON...\n")
    try:
        relaciones_grafo = json.loads(relaciones_json_str)
    except json.JSONDecodeError as e_json:
        error_messages.append(f"Error al parsear JSON de relaciones: {str(e_json)}")
        raise

    # --- Paso 3: Filtrar y Validar Espacios ---
    # sys.stdout.write("Paso 3: Filtrando y validando espacios...\n")
    espacios_filtrados_para_layout = []
    codigos_espacios_validos = set()
    for esp in espacios_data_leidos:
        try:
            # Validar y convertir dimensiones clave
            l = float(esp.get("Longitud", 0))
            w = float(esp.get("Ancho", 0))
            h = float(esp.get("Altura", 0))
            codigo = esp.get("Código del espacio")

            if codigo and l > 0 and w > 0 and h > 0:
                esp["Longitud"] = l # Asegurar que son float
                esp["Ancho"] = w
                esp["Altura"] = h
                espacios_filtrados_para_layout.append(esp)
                codigos_espacios_validos.add(codigo)
            else:
                adv = f"Advertencia: Espacio '{codigo}' omitido por dimensiones inválidas/cero (L:{l}, W:{w}, H:{h})."
                # sys.stderr.write(adv + "\n")
                error_messages.append(adv) # Añadir como advertencia a la salida
        except (ValueError, TypeError) as e_conv:
            adv = f"Advertencia: Espacio '{esp.get('Código del espacio')}' omitido. Error al convertir dimensiones: {str(e_conv)}."
            # sys.stderr.write(adv + "\n")
            error_messages.append(adv)

    if not espacios_filtrados_para_layout:
        error_messages.append("No hay espacios con dimensiones válidas para procesar después del filtrado.")
        OUT = error_messages
        # sys.exit() # No usar sys.exit()

    # Filtrar relaciones_grafo para que solo incluya códigos de espacios válidos
    relaciones_filtradas = {}
    for padre, hijos in relaciones_grafo.items():
        if padre in codigos_espacios_validos:
            hijos_validos = [h for h in hijos if h in codigos_espacios_validos]
            if hijos_validos:
                relaciones_filtradas[padre] = hijos_validos
    relaciones_grafo = relaciones_filtradas

    # --- Paso 4: Calcular Layout ---
    # sys.stdout.write("Paso 4: Calculando layout...\n")
    espacios_layout_calculado = calcular_layout_espacios(espacios_filtrados_para_layout, relaciones_grafo)

    # --- Paso 5: Generar Masas 3D ---
    # sys.stdout.write("Paso 5: Generando masas 3D...\n")
    masas_generadas = []
    puntos_base_a_liberar = [] # Para gestionar Dispose de puntos creados

    # Determinar el vector de desplazamiento global si hay un origen_global_ds
    vector_desplazamiento_global = None
    if isinstance(origen_global_ds, Point):
        vector_desplazamiento_global = Vector.ByCoordinates(origen_global_ds.X, origen_global_ds.Y, origen_global_ds.Z)

    for espacio in espacios_layout_calculado:
        if espacio.get("colocado") and espacio.get("Longitud", 0) > 0: # Solo procesar si fue colocado y tiene dimensiones
            nombre = espacio.get("Nombre del ambiente", espacio.get("Código del espacio", "MasaSinNombre"))
            lon = espacio["Longitud"]
            anc = espacio["Ancho"]
            alt = espacio["Altura"]

            x_rel, y_rel, z_rel = espacio["punto_insercion_calculado"]

            # Crear punto base relativo (a (0,0,0) del layout)
            # Los puntos creados con ByCoordinates deben ser liberados si no se retornan directamente
            punto_base_layout = Point.ByCoordinates(x_rel, y_rel, z_rel)

            # Aplicar desplazamiento global
            if vector_desplazamiento_global:
                punto_base_final = punto_base_layout.Translate(vector_desplazamiento_global)
                punto_base_layout.Dispose() # Liberar el punto intermedio
            else:
                punto_base_final = punto_base_layout # Usar el punto relativo directamente

            puntos_base_a_liberar.append(punto_base_final) # Marcar para liberar después de usar

            # Crear la masa
            try:
                masa = crear_masa_revit(nombre, lon, anc, alt, punto_base_final)
                if masa:
                    masas_generadas.append(masa)
                else:
                    err_masa = f"Error: No se pudo crear la masa para '{nombre}'."
                    # sys.stderr.write(err_masa + "\n")
                    error_messages.append(err_masa)
            except Exception as e_crear_masa:
                err_m = f"Excepción al crear masa para '{nombre}': {str(e_crear_masa)}"
                # sys.stderr.write(err_m + "\n")
                error_messages.append(err_m)
        else:
            if not espacio.get("colocado"):
                 adv_no_colocado = f"Info: Espacio '{espacio.get('Código del espacio')}' no fue colocado por el algoritmo de layout."
                 # sys.stdout.write(adv_no_colocado + "\n")
                 error_messages.append(adv_no_colocado)


    # Liberar puntos base creados
    for pt in puntos_base_a_liberar:
        if pt: pt.Dispose()
    if vector_desplazamiento_global: vector_desplazamiento_global.Dispose()

    # --- Paso 6: Salida ---
    if masas_generadas:
        OUT = masas_generadas
        if error_messages: # Si hay geometrías Y errores/advertencias
             # Dynamo podría no mostrar bien listas mixtas. Considerar enviar errores a otro output si es posible.
             # O convertir errores a strings y añadirlos a la lista OUT si se necesita depurar.
             # Por ahora, si hay geometrías, se prioriza eso. Se pueden loggear errores a un archivo o a la consola de Dynamo.
             # Para este script, si hay masas, las advertencias se pueden ignorar en OUT, pero se imprimieron a stderr (consola).
             # Si se quieren devolver errores junto con geometrías, habría que estructurar OUT diferente (ej. un diccionario)
             # OUT = {"geometrias": masas_generadas, "mensajes": error_messages}
             # Por simplicidad, si hay masas, devolvemos solo masas. Los errores se pueden ver en la consola de Dynamo si se usa print().
             pass
    else: # No hay masas, probablemente solo errores
        OUT = error_messages if error_messages else ["No se generaron masas. Verifique datos de entrada y logs/advertencias."]

except ImportError as e_imp: # Captura el error de openpyxl si no está
    OUT = [str(e_imp)]
except ValueError as e_val: # Captura errores de validación de entradas
    OUT = error_messages + [str(e_val)] if error_messages else [str(e_val)]
except Exception as e:
    # Captura cualquier otra excepción no manejada
    import traceback
    error_completo = f"Error inesperado en el script de Dynamo: {str(e)}\nTraceback:\n{traceback.format_exc()}"
    # sys.stderr.write(error_completo + "\n")
    OUT = error_messages + [error_completo] if error_messages else [error_completo]

# Ejemplo de cómo se podrían ver los errores en la consola de Dynamo (si se usa print en lugar de sys.stderr):
# for msg in error_messages:
#     print(msg)
