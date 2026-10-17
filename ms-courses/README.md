# ms-courses
Backend: microservicio para manejar cursos

## Pre-requisitos

Para levantar el entorno de desarrollo, se requiere lo siguiente:

- **Python 3** (Este proyecto fue desarrollado con Python 3.12.3)  
- **Docker**  
- **Gestor de paquetes**: `pip`  
- **sqlite3**
- **venv** (Para utilizar un entorno virtual)

Las dependencias necesarias de Python están listadas en `requirements.txt`.

## Testing

Para correr los test:

```bash
docker-compose -f docker-compose.test.yml up --build
```

## Comandos Docker

### Construir la imagen

```bash
docker-compose -f docker-compose.yml up --build
```

Ahora la API está andando, para una clara visualizacion:

Suponiendo que se toma un host por ejemplo: 0.0.0.0.
Un Puerto 8080:

En http://0.0.0.0:8080/docs tendremos una manera facil de usarla.

### Información Extra

Aunque es posible interactuar con la API usando `curl`, al estar utilizando FastAPI, recomiendo hacer uso de la UI que viene implementada. Esta interfaz proporciona una visualización clara y simple de los endpoints, junto con ejemplos de respuestas para cada uno de ellos.

#### Para utilizar la UI:

Al ejecutar la aplicación, verás entre los mensajes que imprime la consola: (dependiendo las variables de entorno usadas)

INFO: Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)

Si entramos exactamente a ese link, la aplicacion lanzará un error 404 que no es importante, simplemente una vez que veas este mensaje, agrega `/docs` al final de la URL, como se muestra a continuación:

http://127.0.0.1:8080/docs

De esta manera, accederás a una interfaz limpia y sencilla para interactuar con los endpoints.
