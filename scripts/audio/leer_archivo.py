import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Lee un archivo de texto y extrae su contenido")
    parser.add_argument("archivo", help="Ruta del archivo de texto a leer")
    args = parser.parse_args()

    try:
        with open(args.archivo, "r", encoding="utf-8") as f:
            contenido = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{args.archivo}'", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el archivo: {e}", file=sys.stderr)
        sys.exit(1)

    print(contenido)


if __name__ == "__main__":
    main()
