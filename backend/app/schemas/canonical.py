CANONICAL_SCHEMAS = {
    "ordenes_produccion": {
        "required": {
            "numero_orden_fabricacion": "string",
            "referencia_articulo": "string",
            "fecha_orden_fabricacion": "date",
            "cantidad_fabricada": "integer",
            "tasa_scrap": "float",
            "estado_orden_fabricacion": "string",
        },
        "optional": {
            "tiempo_ciclo": "float",
            "turno": "string",
            "maquina_id": "string",
            "coste": "float",
            "kg_materia_prima": "float",
            "observaciones": "string",
        },
        "enums": {
            "estado_orden_fabricacion": [
                "completada", "en_curso", "bloqueada", "pendiente", "cancelada"
            ],
            "turno": [
                "turno_a", "turno_b", "turno_c",
                "turno_manana", "turno_tarde", "turno_noche"
            ],
        }
    },
    "inventario": {
        "required": {
            "codigo_articulo": "string",
            "descripcion": "string",
            "stock_actual": "float",
            "stock_unidad": "string",
            "estado_stock": "string",
        },
        "optional": {
            "stock_minimo": "float",
            "stock_maximo": "float",
            "precio_coste": "float",
            "precio_coste_unidad": "string",
            "proveedor_principal": "string",
            "ubicacion": "string",
            "ultima_entrada": "date",
            "ultima_salida": "date",
        },
        "enums": {
            "estado_stock": [
                "ok", "critico", "bajo", "exceso", "bloqueado", "en_cuarentena"
            ],
            "stock_unidad": ["kg", "uds", "m", "l", "m2", "m3", "t"],
        }
    },
    "mantenimiento": {
        "required": {
            "id_averia": "string",
            "maquina_afectada": "string",
            "fecha_averia": "date",
            "tipo_mantenimiento": "string",
            "resuelta": "string",
        },
        "optional": {
            "tiempo_parada_horas": "float",
            "coste_reparacion": "float",
            "prioridad": "string",
            "descripcion_averia": "string",
            "tecnico_responsable": "string",
        },
        "enums": {
            "tipo_mantenimiento": ["correctivo", "preventivo", "predictivo"],
            "resuelta": ["si", "no"],
            "prioridad": ["alta", "media", "baja"],
        }
    },
    "calidad": {
        "required": {
            "id_inspeccion": "string",
            "referencia_articulo": "string",
            "fecha_inspeccion": "date",
            "resultado_inspeccion": "string",
        },
        "optional": {
            "cantidad_inspeccionada": "integer",
            "cantidad_rechazada": "integer",
            "tipo_defecto": "string",
            "linea_produccion": "string",
            "nombre_inspector": "string",
            "accion_correctiva": "string",
            "tiempo_inspeccion_horas": "float",
            "turno": "string",
        },
        "enums": {
            "resultado_inspeccion": ["aprobado", "rechazado", "pendiente"],
            "tipo_defecto": [
                "porosidad", "dimension", "rugosidad", "grieta", "otro", "sin_defecto"
            ],
            "accion_correctiva": [
                "desguace", "retrabajo", "liberado", "pendiente_revision"
            ],
        }
    }
}
