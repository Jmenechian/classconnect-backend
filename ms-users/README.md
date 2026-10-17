# ms-users
Backend: microservicio para manejar usuarios

# Tabla de contenidos
1. [Solucion](#solución)
2. [Requisitos](#requisitos)
3. [Testeo](#testeo)
4. [Instrucciones de ejecución](#instrucciones-de-ejecución)
5. [Base de Datos](#y-la-base-de-datos)

## Solución

La solución planteada está desarrollada en **go**, utilizando la librería *gorilla-mux* para el manejo de rutas de la API y utilizando **mongoDB** para la base de datos.

## Requisitos

El proyecto se puede correr enteramente desde docker. Por lo tanto, el único requisito para levantar el proyecto es tener instalado docker.

## Testeo

```
docker-compose --env-file .env.prod -f docker-compose.test.yml up -d --build
```

## Instrucciones de ejecución

Para levantar el proyecto, solo se debe correr el siguiente comando en el directorio principal:
```
docker compose --env-file .env.prod up -d --build
```

## Pendientes:

- Pasar HTTP a HTTPS
- Corregir para que no utilice llaves locales ni .env en repo ( actualmente se debe tener un archivo authKey.json 
