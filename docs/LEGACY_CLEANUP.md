# Limpieza segura, **sin eliminación automática**

Primero ejecuta `bash scripts/legacy_inventory.sh` y guarda su salida.

Conservar obligatoriamente: `~/radiant-go2`, `~/cyclonedds_ws`, `~/fastlio_ws`, `/opt/ros/foxy`, `/lib/modules/$(uname -r)/extra/kromekusb.ko`, `/etc/udev/rules.d/99-kromek*.rules`, `/dev/kromek0` (dinámico), `~/kromek_ros2/vendor/dr_park`, y datos experimentales de `~/kromek_ws/results`/`~/kromek_ros2/data`.

Candidatos para **archivar luego de pruebas RC1**: `~/kromek_stage2`, `~/kromek_stage3`, `~/kromek_vendor` (solo cuando el SDK incluido en nuestro repo ya esté verificado), ZIPs sueltos de etapas anteriores, y `~/Downloads/kromek` (únicamente después de conservar los programas originales en `vendor/dr_park/reference`).

`~/radiation_mapping_ws` contiene la solución del investigador anterior; NO tocarlo sin comprobar referencias de servicios, otros paquetes y experimentos y conservar una copia. No basta con verificar un grep de `.bashrc`.

Ejemplo de backup conservador antes de quitar dos etapas **cuando no haya procesos activos**:

```bash
mkdir -p ~/kromek_archives
tar -czf ~/kromek_archives/stage2_stage3_$(date +%Y%m%d).tar.gz -C "$HOME" kromek_stage2 kromek_stage3
# Confirma su integridad antes de borrar las carpetas originales:
tar -tzf ~/kromek_archives/stage2_stage3_$(date +%Y%m%d).tar.gz | head
```

**Ningún script de este release ejecuta rm -rf sobre workspaces antiguos.** Si luego se aprueba eliminación explícita, hacerlo solo sobre rutas listadas y verificadas, jamás `~/radiant-go2` ni carpetas con sensores compartidos.
