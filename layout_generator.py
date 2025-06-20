# -*- coding: utf-8 -*-
"""
Módulo para calcular el layout generativo heurístico de espacios.
"""
import collections

def check_overlap(x1: float, y1: float, l1: float, w1: float,
                  x2: float, y2: float, l2: float, w2: float) -> bool:
    """
    Comprueba si dos rectángulos se solapan.
    Cada rectángulo está definido por su esquina inferior izquierda (x, y),
    su longitud (extensión en x) y su ancho (extensión en y).

    Args:
        x1, y1, l1, w1: Propiedades del primer rectángulo.
        x2, y2, l2, w2: Propiedades del segundo rectángulo.

    Returns:
        True si hay solapamiento, False en caso contrario.
    """
    rect1_x_inicio, rect1_y_inicio = x1, y1
    rect1_x_fin = x1 + l1
    rect1_y_fin = y1 + w1

    rect2_x_inicio, rect2_y_inicio = x2, y2
    rect2_x_fin = x2 + l2
    rect2_y_fin = y2 + w2

    # Comprobar si NO hay solapamiento
    # Un rectángulo está a la izquierda de otro, o a la derecha, o abajo, o arriba.
    no_overlap = (rect1_x_fin <= rect2_x_inicio or  # R1 está completamente a la izquierda de R2
                  rect1_x_inicio >= rect2_x_fin or  # R1 está completamente a la derecha de R2
                  rect1_y_fin <= rect2_y_inicio or  # R1 está completamente debajo de R2
                  rect1_y_inicio >= rect2_y_fin)   # R1 está completamente encima de R2

    return not no_overlap

def calcular_layout_espacios(espacios_data: list[dict], relaciones_grafo: dict) -> list[dict]:
    """
    Calcula una disposición 2D heurística para una lista de espacios
    basada en sus dimensiones y un grafo de relaciones, evitando colisiones.

    Args:
        espacios_data: Lista de diccionarios, cada uno representando un espacio.
                       Se espera que contengan "Código del espacio", "Longitud", "Ancho".
                       Estos diccionarios serán modificados para añadir/actualizar
                       "punto_insercion_calculado" y "colocado".
        relaciones_grafo: Diccionario que representa conexiones.
                          Ej: {"CODIGO_A": ["CODIGO_B", "CODIGO_C"]}

    Returns:
        La lista espacios_data actualizada con "punto_insercion_calculado" y "colocado".
    """
    if not espacios_data:
        return []

    # Crear un mapeo de código de espacio a su diccionario para acceso rápido
    espacios_map = {esp["Código del espacio"]: esp for esp in espacios_data}

    # 1. Inicializar campos en cada espacio
    for espacio in espacios_data:
        espacio["punto_insercion_calculado"] = (0.0, 0.0, 0.0) # (x, y, z)
        espacio["colocado"] = False
        # Asegurarse de que las dimensiones existen y no son None
        if espacio.get("Longitud") is None or espacio.get("Ancho") is None:
            # Esto debería ser manejado antes o lanzar un error más específico
            print(f"Advertencia: Espacio {espacio['Código del espacio']} no tiene dimensiones válidas.")
            # Podríamos optar por no colocarlo, o asignarle dimensiones por defecto.
            # Por ahora, el algoritmo podría fallar si intenta usar Longitud/Ancho None.

    # 2. Algoritmo de Colocación
    # Cola para espacios colocados cuyos vecinos necesitan ser procesados
    cola_procesamiento = collections.deque()

    # Colocar el primer espacio como referencia (si existe)
    # Podría elegirse uno sin dependencias si el grafo lo permite, pero por simplicidad, el primero.
    espacio_inicial = espacios_data[0]
    espacio_inicial["punto_insercion_calculado"] = (0.0, 0.0, 0.0)
    espacio_inicial["colocado"] = True
    cola_procesamiento.append(espacio_inicial)

    espacios_colocados_lista = [espacio_inicial] # Lista para chequeo de colisiones

    while cola_procesamiento:
        espacio_padre = cola_procesamiento.popleft()
        padre_codigo = espacio_padre["Código del espacio"]
        padre_x, padre_y, _ = espacio_padre["punto_insercion_calculado"]
        padre_longitud = espacio_padre["Longitud"]
        padre_ancho = espacio_padre["Ancho"]

        if padre_longitud is None or padre_ancho is None: # Chequeo por si acaso
            print(f"Error: Espacio padre {padre_codigo} tiene dimensiones None. Saltando.")
            continue

        # Hijos conectados según el grafo
        codigos_hijos_conectados = relaciones_grafo.get(padre_codigo, [])

        for codigo_hijo in codigos_hijos_conectados:
            espacio_hijo = espacios_map.get(codigo_hijo)
            if not espacio_hijo:
                print(f"Advertencia: Código de espacio hijo '{codigo_hijo}' no encontrado en espacios_data.")
                continue

            if espacio_hijo["colocado"]:
                continue # Ya fue colocado, posiblemente por otro padre

            hijo_longitud = espacio_hijo["Longitud"]
            hijo_ancho = espacio_hijo["Ancho"]

            if hijo_longitud is None or hijo_ancho is None:
                print(f"Error: Espacio hijo {codigo_hijo} tiene dimensiones None. No se puede colocar.")
                continue

            # Estrategias de Posicionamiento Tentativo (coordenadas x,y para esquina inf-izq)
            # 1. A la derecha del padre: (padre_x + padre_longitud, padre_y)
            # 2. Arriba del padre: (padre_x, padre_y + padre_ancho)
            # (Podrían añadirse más, como izquierda, abajo, con pequeños offsets, etc.)
            posiciones_tentativas = [
                (padre_x + padre_longitud, padre_y), # Derecha
                (padre_x, padre_y + padre_ancho),   # Arriba
                (padre_x - hijo_longitud, padre_y), # Izquierda
                (padre_x, padre_y - hijo_ancho)    # Abajo
            ]

            posicion_encontrada_para_hijo = False
            for tentativa_x, tentativa_y in posiciones_tentativas:
                colision_detectada = False
                # Verificar colisión con TODOS los espacios ya colocados
                for otro_espacio_colocado in espacios_colocados_lista:
                    # No es necesario chequear colisión con el padre si la posición es adyacente y externa
                    # if otro_espacio_colocado == espacio_padre:
                    # continue

                    otro_x, otro_y, _ = otro_espacio_colocado["punto_insercion_calculado"]
                    otro_longitud = otro_espacio_colocado["Longitud"]
                    otro_ancho = otro_espacio_colocado["Ancho"]

                    if check_overlap(tentativa_x, tentativa_y, hijo_longitud, hijo_ancho,
                                     otro_x, otro_y, otro_longitud, otro_ancho):
                        colision_detectada = True
                        break # Colisión con este 'otro_espacio_colocado', probar siguiente tentativa

                if not colision_detectada:
                    espacio_hijo["punto_insercion_calculado"] = (tentativa_x, tentativa_y, 0.0)
                    espacio_hijo["colocado"] = True
                    cola_procesamiento.append(espacio_hijo)
                    espacios_colocados_lista.append(espacio_hijo)
                    posicion_encontrada_para_hijo = True
                    break # Posición encontrada para este hijo, pasar al siguiente hijo

            if not posicion_encontrada_para_hijo:
                print(f"Advertencia: No se pudo encontrar posición sin colisión para el espacio '{codigo_hijo}' adyacente a '{padre_codigo}'.")

    # Manejo opcional de espacios no colocados (ej. por no estar en el grafo o por colisiones)
    # Podrían colocarse en una nueva fila/grilla.
    # Por ahora, simplemente se listan.
    no_colocados = [esp for esp in espacios_data if not esp["colocado"]]
    if no_colocados:
        print(f"\nEspacios que no pudieron ser colocados o no estaban conectados:")
        for esp in no_colocados:
            print(f"- {esp['Código del espacio']}")
            # Aquí se podría implementar una lógica de colocación secundaria.
            # Por ejemplo, encontrar la Y máxima de los colocados y empezar una nueva "fila".
            # O una grilla simple.
            # Para este subtask, se dejan como no colocados con su posición inicial (0,0,0).

    return espacios_data


if __name__ == '__main__':
    print("--- Prueba de Layout Generativo Heurístico ---")

    # Datos de prueba
    espacios_input = [
        {"Código del espacio": "ESP001", "Nombre": "Recepción", "Longitud": 5.0, "Ancho": 4.0, "Altura": 3.0},
        {"Código del espacio": "ESP002", "Nombre": "Oficina1", "Longitud": 3.0, "Ancho": 3.0, "Altura": 3.0},
        {"Código del espacio": "ESP003", "Nombre": "Oficina2", "Longitud": 3.0, "Ancho": 3.0, "Altura": 3.0},
        {"Código del espacio": "ESP004", "Nombre": "SalaReuniones", "Longitud": 4.0, "Ancho": 4.0, "Altura": 3.0},
        {"Código del espacio": "ESP005", "Nombre": "Baño", "Longitud": 2.0, "Ancho": 2.0, "Altura": 3.0},
        {"Código del espacio": "ESP006", "Nombre": "Pasillo", "Longitud": 1.0, "Ancho": 5.0, "Altura": 3.0}, # Largo y estrecho
        {"Código del espacio": "ESP007", "Nombre": "Almacen", "Longitud": 2.0, "Ancho": 2.0, "Altura": 3.0}, # No conectado
    ]

    # Relaciones: ESP001 conecta con ESP002, ESP003, ESP006. ESP002 con ESP005. ESP006 con ESP004.
    relaciones = {
        "ESP001": ["ESP002", "ESP003", "ESP006"],
        "ESP002": ["ESP005"],
        "ESP003": [], # Sin conexiones salientes explícitas aquí
        "ESP006": ["ESP004"],
        # ESP004, ESP005, ESP007 no tienen conexiones salientes definidas en este grafo
    }
    print("\nDatos de entrada (espacios):")
    for esp in espacios_input:
        print(esp)
    print("\nRelaciones:")
    for k, v in relaciones.items():
        print(f"{k}: {v}")

    espacios_layout = calcular_layout_espacios(list(espacios_input), relaciones) # Usar una copia para no alterar el original en pruebas múltiples

    print("\n--- Resultados del Layout ---")
    for espacio in espacios_layout:
        print(f"Espacio: {espacio['Código del espacio']} ({espacio['Nombre']}), "
              f"Colocado: {espacio['colocado']}, "
              f"Posición (x,y,z): {espacio['punto_insercion_calculado']}, "
              f"Dims (L,W): ({espacio['Longitud']}, {espacio['Ancho']})")

    # Verificaciones básicas (no exhaustivas)
    print("\n--- Verificaciones ---")
    colocados_count = sum(1 for esp in espacios_layout if esp['colocado'])
    print(f"Total de espacios colocados: {colocados_count} de {len(espacios_layout)}")

    esp001 = next(e for e in espacios_layout if e["Código del espacio"] == "ESP001")
    assert esp001["colocado"] and esp001["punto_insercion_calculado"] == (0.0, 0.0, 0.0), "ESP001 fallo en colocación inicial"

    esp002 = next(e for e in espacios_layout if e["Código del espacio"] == "ESP002")
    # ESP002 debería estar a la derecha de ESP001 (5,0) o arriba (0,4)
    # Con L=5, A=4 para ESP001. L=3, A=3 para ESP002.
    # Derecha: (0+5, 0) = (5,0) -> No colisión con ESP001.
    # Arriba: (0, 0+4) = (0,4) -> No colisión con ESP001.
    # El algoritmo prueba Derecha primero.
    if esp002["colocado"]:
        assert esp002["punto_insercion_calculado"] == (5.0, 0.0, 0.0), f"ESP002 posición inesperada {esp002['punto_insercion_calculado']}"
        print("ESP002 colocado a la derecha de ESP001, como se esperaba.")

    esp003 = next(e for e in espacios_layout if e["Código del espacio"] == "ESP003")
    # ESP003 (L=3,A=3) conectado a ESP001 (L=5,A=4) en (0,0). ESP002 (L=3,A=3) en (5,0).
    # Tentativas para ESP003 desde ESP001:
    # 1. Derecha (5,0): Colisiona con ESP002.
    # 2. Arriba (0,4): No colisión con ESP001 ni ESP002. Debería ser (0.0, 4.0, 0.0).
    if esp003["colocado"]:
         assert esp003["punto_insercion_calculado"] == (0.0, 4.0, 0.0), f"ESP003 posición inesperada {esp003['punto_insercion_calculado']}"
         print("ESP003 colocado arriba de ESP001, como se esperaba (tras colisión a la derecha).")

    esp007 = next(e for e in espacios_layout if e["Código del espacio"] == "ESP007")
    assert not esp007["colocado"], "ESP007 (no conectado) no debería haberse colocado por el algo. principal."
    print("ESP007 (no conectado) permaneció no colocado, como se esperaba.")

    print("\nPrueba de función check_overlap:")
    # No solapan
    assert not check_overlap(0,0,1,1, 2,2,1,1), "check_overlap Falla 1"
    assert not check_overlap(0,0,1,1, 1,0,1,1), "check_overlap Falla 2 (adyacente)"
    # Solapan
    assert check_overlap(0,0,2,2, 1,1,2,2), "check_overlap Falla 3"
    assert check_overlap(0,0,1,1, 0,0,1,1), "check_overlap Falla 4 (identicos)"
    assert check_overlap(1,1,3,3, 0,0,2,2), "check_overlap Falla 5 (R2 dentro de R1)"
    print("Pruebas de check_overlap pasadas.")

    print("\n--- Fin de la Prueba ---")
