# ClassConnect - Plataforma de Microservicios

Plataforma backend modular para la gestión educativa, estructurada en microservicios independientes desarrollados en Go y Python.

## Arquitectura y Servicios

El sistema desacopla la lógica de negocio en servicios orientados al dominio:

| Servicio | Lenguaje / Framework | Base de Datos | Responsabilidad |
| :--- | :--- | :--- | :--- |
| `ms-users` | Go (Gin) | MongoDB | Autenticación, perfiles de usuario y gestión de roles. |
| `ms-courses` | Python (FastAPI) | PostgreSQL | Catálogo de cursos, contenidos, inscripciones y seguimiento. |

## Características Principales

- Arquitectura desacoplada mediante APIs RESTful.
- Persistencia políglota: PostgreSQL (SQLAlchemy) para modelos relacionales y MongoDB para almacenamiento de documentos.
- Observabilidad y métricas de latencia integradas con Datadog APM.
- Containerización y despliegue del entorno con Docker Compose.
- Pruebas automatizadas e integración continua con GitHub Actions.

## Tecnologías

- Lenguajes: Go, Python
- Frameworks y librerías: Gin, FastAPI, Pydantic, SQLAlchemy
- Bases de datos: PostgreSQL, MongoDB
- Herramientas y DevOps: Docker, Docker Compose, Datadog APM, GitHub Actions

## Contexto
Proyecto grupal desarrollado en la Facultad de Ingeniería de la Universidad de Buenos Aires (FIUBA).
