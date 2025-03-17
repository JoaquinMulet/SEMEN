import os

# Obtener la ruta del volumen
volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH')
print(f"Volumen montado en: {volume_path}")

# Listar el contenido del volumen
print("\nContenido del volumen:")
for item in os.listdir(volume_path):
    item_path = os.path.join(volume_path, item)
    if os.path.isdir(item_path):
        print(f"📁 {item} (directorio)")
    else:
        size = os.path.getsize(item_path)
        print(f"📄 {item} ({size} bytes)")

# Verificar el directorio 'instance'
instance_dir = os.path.join(volume_path, 'instance')
if os.path.exists(instance_dir) and os.path.isdir(instance_dir):
    print("\nContenido del directorio instance:")
    for item in os.listdir(instance_dir):
        item_path = os.path.join(instance_dir, item)
        if os.path.isdir(item_path):
            print(f"📁 {item} (directorio)")
        else:
            size = os.path.getsize(item_path)
            print(f"📄 {item} ({size} bytes)")
else:
    print("\nEl directorio 'instance' no existe en el volumen")