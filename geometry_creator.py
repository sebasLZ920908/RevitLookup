# -*- coding: utf-8 -*-
"""
Módulo para crear masas geométricas para Revit usando ProtoGeometry (simulado).
"""

# --- Simulación de Clases de ProtoGeometry ---
# En un entorno real de Dynamo, estas importaciones serían:
# import clr
# clr.AddReference('ProtoGeometry')
# from Autodesk.DesignScript.Geometry import Point, Cuboid, Solid, Vector, CoordinateSystem, Rectangle

class GeometryBase:
    """Clase base para simular el método Dispose."""
    def Dispose(self):
        # En ProtoGeometry real, esto liberaría recursos no gestionados.
        # print(f"Disposing {self.__class__.__name__}")
        pass

class Point(GeometryBase):
    """Simulación de la clase Point de ProtoGeometry."""
    def __init__(self, x, y, z):
        self.X = x
        self.Y = y
        self.Z = z
        # print(f"Point created at ({self.X}, {self.Y}, {self.Z})")

    @staticmethod
    def ByCoordinates(x: float, y: float, z: float):
        """Crea un punto por coordenadas."""
        return Point(x, y, z)

class Vector(GeometryBase):
    """Simulación de la clase Vector de ProtoGeometry."""
    def __init__(self, x, y, z):
        self.X = x
        self.Y = y
        self.Z = z
        # print(f"Vector created ({self.X}, {self.Y}, {self.Z})")

    @staticmethod
    def ZAxis():
        """Devuelve un vector unitario en la dirección Z."""
        return Vector(0, 0, 1)

class CoordinateSystem(GeometryBase):
    """Simulación de la clase CoordinateSystem de ProtoGeometry."""
    def __init__(self, origin: Point, xAxis: Vector = None, yAxis: Vector = None, zAxis: Vector = None):
        self.Origin = origin
        self.XAxis = xAxis if xAxis else Vector(1, 0, 0)
        self.YAxis = yAxis if yAxis else Vector(0, 1, 0)
        self.ZAxis = zAxis if zAxis else Vector(0, 0, 1)
        # print(f"CoordinateSystem created at origin ({origin.X}, {origin.Y}, {origin.Z})")

    @staticmethod
    def ByOrigin(origin: Point):
        """Crea un sistema de coordenadas en el origen especificado."""
        return CoordinateSystem(origin)

class Rectangle(GeometryBase):
    """Simulación de la clase Rectangle de ProtoGeometry."""
    def __init__(self, cs: CoordinateSystem, width: float, length: float):
        self.CoordinateSystem = cs
        self.Width = width # Dimensión a lo largo del eje Y del CS
        self.Length = length # Dimensión a lo largo del eje X del CS
        # print(f"Rectangle created with Width (Y-dim): {self.Width}, Length (X-dim): {self.Length}")

    @staticmethod
    def ByWidthLength(cs: CoordinateSystem, width: float, length: float):
        """
        Crea un rectángulo en el plano XY del sistema de coordenadas dado.
        Width es a lo largo del eje Y local, Length es a lo largo del eje X local.
        """
        return Rectangle(cs, width, length)

    def ExtrudeAsSolid(self, direction: Vector, distance: float):
        """Simula la extrusión de un rectángulo para formar un sólido."""
        # print(f"Extruding Rectangle as Solid along vector ({direction.X},{direction.Y},{direction.Z}) by distance {distance}")
        # En la simulación, simplemente devolvemos un objeto Solid genérico.
        # El nombre_espacio no se usa directamente en la creación geométrica aquí,
        # pero se pasa a la función principal y podría usarse para metadatos en Revit.
        return Solid(cuboid_like_shape=self, extrusion_height=distance)

class Solid(GeometryBase):
    """Simulación de la clase Solid de ProtoGeometry."""
    def __init__(self, cuboid_like_shape=None, extrusion_height=None):
        # Estas propiedades son solo para ayudar a la simulación/depuración.
        self. rappresentative_shape = cuboid_like_shape
        self.extrusion_height = extrusion_height
        # print("Solid (Cuboid-like) created.")
        pass # En ProtoGeometry real, esto sería un objeto de geometría sólida.

# --- Fin de Simulación de Clases ---

def crear_masa_revit(nombre_espacio: str, longitud: float, ancho: float, altura: float, punto_insercion: Point) -> Solid:
    """
    Crea una masa geométrica (Solid) para Revit utilizando ProtoGeometry (simulado).

    Args:
        nombre_espacio (str): Nombre o identificador para la masa (actualmente no usado en la geometría misma).
        longitud (float): La longitud de la masa (dimensión a lo largo del eje X local).
        ancho (float): El ancho de la masa (dimensión a lo largo del eje Y local).
        altura (float): La altura de la masa (dimensión a lo largo del eje Z local).
        punto_insercion (Point): La esquina base (inferior, origen local) de la masa.

    Returns:
        Solid: El objeto Solid (la masa) resultante.
    """
    # El argumento nombre_espacio se recibe pero no se usa directamente en la creación
    # de la geometría ProtoGeometry aquí. Podría ser usado para nombrar la forma en Revit
    # o para asociar metadatos posteriormente.

    # Crear un sistema de coordenadas en el punto de inserción.
    # Este CS define el plano base para el rectángulo.
    # El rectángulo se dibujará con su 'longitud' a lo largo del eje X del CS
    # y su 'ancho' a lo largo del eje Y del CS.
    cs = CoordinateSystem.ByOrigin(punto_insercion)

    try:
        # Crear un rectángulo base en el plano XY del sistema de coordenadas.
        # En ProtoGeometry, Rectangle.ByWidthLength(cs, width, length):
        # - width es la extensión a lo largo del eje Y del CoordinateSystem.
        # - length es la extensión a lo largo del eje X del CoordinateSystem.
        # Por lo tanto, pasamos 'ancho' como primer argumento dimensional y 'longitud' como segundo.
        rectangulo_base = Rectangle.ByWidthLength(cs, ancho, longitud)

        # Extruir el rectángulo como un sólido a lo largo del eje Z positivo
        # por la altura especificada.
        vector_extrusion = Vector.ZAxis()
        masa_solida = rectangulo_base.ExtrudeAsSolid(vector_extrusion, altura)

        return masa_solida
    finally:
        # Es una buena práctica en Dynamo liberar los objetos de geometría intermedios
        # que ya no son necesarios, para gestionar la memoria.
        if 'rectangulo_base' in locals() and rectangulo_base:
            rectangulo_base.Dispose()
        if cs:
            cs.Dispose()
        # El punto_insercion y vector_extrusion no necesitan Dispose si son parámetros
        # o creados estáticamente sin estado interno complejo que requiera liberación.

if __name__ == '__main__':
    # --- Ejemplo de uso (simulado fuera de Dynamo) ---
    print("Iniciando prueba de creación de masa...")

    # 1. Definir los parámetros de entrada
    nombre_del_espacio = "Oficina Principal"
    longitud_espacio = 10.0  # Dimensión en X
    ancho_espacio = 5.0    # Dimensión en Y
    altura_espacio = 3.0     # Dimensión en Z
    # Punto de inserción (esquina inferior, por ejemplo, en el origen del proyecto)
    punto_base = Point.ByCoordinates(0, 0, 0)
    print(f"Parámetros: Nombre='{nombre_del_espacio}', L={longitud_espacio}, A={ancho_espacio}, H={altura_espacio}, "
          f"Pin=({punto_base.X},{punto_base.Y},{punto_base.Z})")

    # 2. Llamar a la función para crear la masa
    masa_creada = crear_masa_revit(
        nombre_del_espacio,
        longitud_espacio,
        ancho_espacio,
        altura_espacio,
        punto_base
    )

    # 3. Verificar el resultado (simulado)
    if isinstance(masa_creada, Solid):
        print(f"Masa '{nombre_del_espacio}' creada exitosamente como un objeto Solid (simulado).")
        # En un entorno real, esta 'masa_creada' sería un objeto de ProtoGeometry
        # que podría ser usado como salida en un nodo de Dynamo (OUT = masa_creada).

        # Inspección simulada de las propiedades del sólido
        if hasattr(masa_creada, 'rappresentative_shape') and isinstance(masa_creada.rappresentative_shape, Rectangle):
            rect_sim = masa_creada.rappresentative_shape
            print(f"  Forma base simulada: Rectángulo con Ancho (Y-dim): {rect_sim.Width}, Longitud (X-dim): {rect_sim.Length}")
            print(f"  Origen del CS base simulado: ({rect_sim.CoordinateSystem.Origin.X}, {rect_sim.CoordinateSystem.Origin.Y}, {rect_sim.CoordinateSystem.Origin.Z})")
        if hasattr(masa_creada, 'extrusion_height'):
            print(f"  Altura de extrusión simulada: {masa_creada.extrusion_height}")

        # Verificar que las dimensiones del rectángulo base corresponden a ancho y longitud
        assert masa_creada.rappresentative_shape.Width == ancho_espacio, "El ancho del rectángulo base no coincide."
        assert masa_creada.rappresentative_shape.Length == longitud_espacio, "La longitud del rectángulo base no coincide."
        assert masa_creada.extrusion_height == altura_espacio, "La altura de extrusión no coincide."
        assert masa_creada.rappresentative_shape.CoordinateSystem.Origin == punto_base, "El punto de inserción no coincide."

    else:
        print(f"Error: La creación de la masa para '{nombre_del_espacio}' no devolvió un objeto Solid.")

    print("\nProbando con otro punto de inserción...")
    punto_base_2 = Point.ByCoordinates(10, 20, 5)
    nombre_espacio_2 = "Sala Reuniones"
    masa_creada_2 = crear_masa_revit(nombre_espacio_2, 8.0, 4.0, 2.5, punto_base_2)

    if isinstance(masa_creada_2, Solid):
        print(f"Masa '{nombre_espacio_2}' creada exitosamente.")
        rect_sim_2 = masa_creada_2.rappresentative_shape
        print(f"  Origen del CS base simulado: ({rect_sim_2.CoordinateSystem.Origin.X}, {rect_sim_2.CoordinateSystem.Origin.Y}, {rect_sim_2.CoordinateSystem.Origin.Z})")
        assert rect_sim_2.CoordinateSystem.Origin.X == 10 and rect_sim_2.CoordinateSystem.Origin.Y == 20 and rect_sim_2.CoordinateSystem.Origin.Z == 5

    # Prueba de Dispose (simulado)
    print("\nSimulando Dispose de la última masa creada (y sus componentes internos si la función los liberó):")
    if masa_creada_2:
        masa_creada_2.Dispose() # El objeto Solid en sí mismo

    print("\nPrueba completada.")
