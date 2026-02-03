"""
Utilidad para limpiar datos de las obras
Este script permite resetear los avances y presupuestos de las obras
manteniendo la estructura y configuración original.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

def crear_backup():
    """Crea una copia de seguridad de los archivos de obras"""
    backup_dir = Path("data/obras/backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    obras_dir = Path("data/obras")
    archivos = ["obras.json", "pachacutec.json", "rinconada.json", "test01.json"]
    
    for archivo in archivos:
        origen = obras_dir / archivo
        if origen.exists():
            destino = backup_dir / archivo
            shutil.copy2(origen, destino)
            print(f"✓ Backup creado: {destino}")
    
    print(f"\n✅ Backup completo guardado en: {backup_dir}\n")
    return backup_dir

def limpiar_obra(obra_file, resetear_presupuesto=False, presupuesto_nuevo=500000.0):
    """
    Limpia los datos de una obra específica
    
    Args:
        obra_file: Ruta al archivo JSON de la obra
        resetear_presupuesto: Si True, establece un presupuesto nuevo
        presupuesto_nuevo: Valor del presupuesto a establecer
    """
    with open(obra_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Guardar información antes de limpiar
    avances_borrados = len(data.get("avance", []))
    
    # Limpiar avances
    data["avance"] = []
    
    # Resetear presupuesto si se solicita
    if resetear_presupuesto:
        data["presupuesto_total"] = presupuesto_nuevo
    
    # Mantener cronograma y hitos_pago si existen
    # No se tocan, solo se limpian los avances
    
    # Guardar archivo limpio
    with open(obra_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return avances_borrados

def mostrar_menu():
    """Muestra el menú de opciones"""
    print("=" * 60)
    print("        LIMPIEZA DE DATOS DE OBRAS - BOSS 4.0")
    print("=" * 60)
    print("\nOpciones:")
    print("1. Limpiar TODAS las obras (solo avances)")
    print("2. Limpiar TODAS las obras (avances + resetear presupuesto)")
    print("3. Limpiar obra específica")
    print("4. Ver estado actual de las obras")
    print("5. Salir")
    print("\n" + "=" * 60)

def ver_estado():
    """Muestra el estado actual de cada obra"""
    obras_dir = Path("data/obras")
    archivos = ["pachacutec.json", "rinconada.json", "test01.json"]
    
    print("\n" + "=" * 60)
    print("ESTADO ACTUAL DE LAS OBRAS")
    print("=" * 60)
    
    for archivo in archivos:
        ruta = obras_dir / archivo
        if ruta.exists():
            with open(ruta, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            nombre_obra = archivo.replace(".json", "").upper()
            num_avances = len(data.get("avance", []))
            presupuesto = data.get("presupuesto_total", 0)
            
            # Calcular gasto total
            gasto_total = 0
            for avance in data.get("avance", []):
                costos = avance.get("costos", {})
                for mat in costos.get("materiales", []):
                    gasto_total += mat.get("Parcial (S/)", 0)
                for mo in costos.get("mano_de_obra", []):
                    gasto_total += mo.get("Parcial (S/)", 0)
                for eq in costos.get("equipos", []):
                    gasto_total += eq.get("Parcial (S/)", 0)
            
            print(f"\n📊 {nombre_obra}")
            print(f"   Avances registrados: {num_avances}")
            print(f"   Presupuesto total: S/ {presupuesto:,.2f}")
            print(f"   Gasto ejecutado: S/ {gasto_total:,.2f}")
            
            if gasto_total > presupuesto:
                exceso = gasto_total - presupuesto
                print(f"   ⚠️  EXCEDIDO por: S/ {exceso:,.2f}")
            else:
                disponible = presupuesto - gasto_total
                print(f"   ✓ Disponible: S/ {disponible:,.2f}")
    
    print("\n" + "=" * 60 + "\n")

def main():
    """Función principal"""
    while True:
        mostrar_menu()
        opcion = input("Selecciona una opción (1-5): ").strip()
        
        if opcion == "1":
            # Limpiar solo avances
            print("\n⚠️  Vas a BORRAR todos los avances de todas las obras")
            print("    El presupuesto se mantendrá igual")
            confirm = input("\n¿Confirmas esta acción? (SI/no): ").strip().upper()
            
            if confirm == "SI":
                backup_dir = crear_backup()
                obras_dir = Path("data/obras")
                archivos = ["pachacutec.json", "rinconada.json", "test01.json"]
                
                total = 0
                for archivo in archivos:
                    ruta = obras_dir / archivo
                    if ruta.exists():
                        num = limpiar_obra(ruta, resetear_presupuesto=False)
                        total += num
                        print(f"✓ {archivo}: {num} avances eliminados")
                
                print(f"\n✅ Limpieza completada. Total: {total} avances eliminados")
                print(f"💾 Backup guardado en: {backup_dir}\n")
            else:
                print("\n❌ Operación cancelada\n")
        
        elif opcion == "2":
            # Limpiar avances y resetear presupuesto
            print("\n⚠️  Vas a BORRAR todos los avances Y RESETEAR el presupuesto")
            presupuesto = input("Ingresa el nuevo presupuesto (Enter para S/ 500,000): ").strip()
            
            if presupuesto == "":
                presupuesto = 500000.0
            else:
                try:
                    presupuesto = float(presupuesto)
                except:
                    print("❌ Valor inválido, usando S/ 500,000")
                    presupuesto = 500000.0
            
            confirm = input(f"\n¿Confirmas resetear todo con presupuesto de S/ {presupuesto:,.2f}? (SI/no): ").strip().upper()
            
            if confirm == "SI":
                backup_dir = crear_backup()
                obras_dir = Path("data/obras")
                archivos = ["pachacutec.json", "rinconada.json", "test01.json"]
                
                total = 0
                for archivo in archivos:
                    ruta = obras_dir / archivo
                    if ruta.exists():
                        num = limpiar_obra(ruta, resetear_presupuesto=True, presupuesto_nuevo=presupuesto)
                        total += num
                        print(f"✓ {archivo}: {num} avances eliminados, presupuesto = S/ {presupuesto:,.2f}")
                
                print(f"\n✅ Limpieza completada. Total: {total} avances eliminados")
                print(f"💾 Backup guardado en: {backup_dir}\n")
            else:
                print("\n❌ Operación cancelada\n")
        
        elif opcion == "3":
            # Limpiar obra específica
            print("\nObras disponibles:")
            print("1. pachacutec")
            print("2. rinconada")
            print("3. test01")
            
            obra_num = input("\nSelecciona la obra (1-3): ").strip()
            obras = {"1": "pachacutec.json", "2": "rinconada.json", "3": "test01.json"}
            
            if obra_num in obras:
                archivo = obras[obra_num]
                print(f"\nVas a limpiar: {archivo}")
                resetear = input("¿Resetear también el presupuesto? (s/N): ").strip().lower()
                
                presupuesto = 500000.0
                if resetear == "s":
                    presupuesto_input = input("Nuevo presupuesto (Enter para S/ 500,000): ").strip()
                    if presupuesto_input:
                        try:
                            presupuesto = float(presupuesto_input)
                        except:
                            print("Usando S/ 500,000")
                
                confirm = input(f"\n¿Confirmar limpieza de {archivo}? (SI/no): ").strip().upper()
                
                if confirm == "SI":
                    backup_dir = crear_backup()
                    ruta = Path("data/obras") / archivo
                    num = limpiar_obra(ruta, resetear_presupuesto=(resetear == "s"), presupuesto_nuevo=presupuesto)
                    print(f"\n✅ {num} avances eliminados de {archivo}")
                    print(f"💾 Backup guardado en: {backup_dir}\n")
                else:
                    print("\n❌ Operación cancelada\n")
            else:
                print("\n❌ Opción inválida\n")
        
        elif opcion == "4":
            ver_estado()
        
        elif opcion == "5":
            print("\n👋 Saliendo...\n")
            break
        
        else:
            print("\n❌ Opción inválida. Intenta de nuevo.\n")

if __name__ == "__main__":
    main()
