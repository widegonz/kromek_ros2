# kromek_ros2 — SIGMA50 ROS 2 Foxy (RC1)

Repositorio independiente de RADIANT para adquisición de radiación con Kromek SIGMA50, sobre ARM64 Ubuntu 20.04 / ROS 2 Foxy, siguiendo el SDK y los programas de adquisición originales aportados por Dr. Park.

**Componentes:** `src/kromek_interfaces` (mensajes), `src/kromek_driver` (ctypes SDK, ROS, diagnósticos, recuperación), `vendor/` (SDK importado localmente, sin incluir en Git), `scripts/` (compilación/ejecución/validación) y `systemd/` (servicio opcional).

**Fase actual:** RC1 posterior a reconexión física de Stage 4. Aún requiere probar RC1 en el robot; no activar el servicio ni borrar versiones anteriores antes de esa prueba.

## Actualizar el checkout existente en Go2

1. Detén con Ctrl+C todos los procesos Kromek y comprueba `sudo fuser -v /dev/kromek0`.
2. Copia este ZIP al Go2, extrae en `~/kromek_rc1_extract` (NO encima de tu copia activa), y aplica:

```bash
bash ~/kromek_rc1_extract/scripts/apply_to_robot.sh ~/kromek_ros2
cd ~/kromek_ros2
python3 -m unittest discover -s tests -v
./scripts/build_ros.sh
./scripts/run_detector.sh
```

El aplicador conserva los archivos `vendor/dr_park` y `data`, así como `build/`, `install/` y `log/`; crea copia de código anterior en `.backups/`.

## Verificar funcionamiento

```bash
ros2 topic hz /kromek/measurement
ros2 topic hz /kromek/spectrum
ros2 topic echo /diagnostics
```

Los tipos de mensajes ROS y nombres de topics siguen idénticos a Stage 4. El reloj monotónico controla cuándo consultamos el SDK; CPS siempre usa `interval_real_time_ms` o `interval_live_time_ms` comunicados por SDK.

## Servicio systemd opcional (NO habilitado por defecto)

```bash
bash scripts/install_service.sh --show
bash scripts/install_service.sh --install
sudo systemctl enable --now kromek-ros2.service
systemctl status kromek-ros2.service
journalctl -u kromek-ros2.service -f
```

Antes de habilitarlo, comprueba que ningún `ros2 launch` manual ni dashboard anterior abra el mismo detector. **Servicio de plantilla para tu Go2:** fija las rutas `/home/unitree/..`, el CycloneDDS ya verificado con RealSense y Foxy. Adaptar para otros robots.

## Limpieza de etapas previas

```bash
bash scripts/legacy_inventory.sh | tee ~/kromek_legacy_inventory.txt
```

Leer `docs/LEGACY_CLEANUP.md`. No se eliminan carpetas, servicios, módulos USB ni reglas udev sin revisar el inventario y preservar pruebas experimentales.

## Método experimental

Se incluye `scripts/run_park_reference.py` y `scripts/compare_acquisitions.py` para comparar adquisiciones **consecutivas**, nunca simultáneas. Más detalles y límites: `docs/RELEASE_NOTES_RC1.md`.

## Migración no destructiva de los datos antiguos

Si todavía guardas grabaciones o resultados en `~/kromek_ws/results/`:

```bash
bash scripts/import_legacy_results.sh
```

Copia los resultados disponibles a `data/legacy_results` sin sustituir archivos ni borrar originales. Confirma capacidad de disco antes de copiar rosbag grandes.
