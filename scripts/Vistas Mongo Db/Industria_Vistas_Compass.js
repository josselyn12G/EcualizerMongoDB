// =====================================================================
//  Ecualizer · VISTAS de MongoDB para INDUSTRIA (Discográficas/Contratos)
// ---------------------------------------------------------------------
//  Alimentan el panel del administrador (CRUD/listados de discográficas y
//  contratos) y el dashboard del artista ("Mis Contratos").
//
//  Cómo ejecutar:
//    • Compass / Atlas: abre un Playground en la base "Ecualizer",
//      pega este contenido y pulsa "Run".
//    • mongosh:
//        mongosh "<TU_URI>/Ecualizer" --file "scripts/Vistas Mongo Db/Industria_Vistas_Compass.js"
//
//  Idempotente: elimina la vista si ya existe y la vuelve a crear.
//  Modelo de datos:
//    - Discograficas:          { discograficaId, nombreDiscografica, paisOrigen,
//                                correoContacto, telefonoContacto }
//    - ContratosDiscograficos: { contratoId, fechaInicio(date), fechaFin(str|null),
//                                porcentajeArtista, porcentajeDiscografica,
//                                estadoContrato, discograficaAsociada{...},
//                                artistaAsociado{...} }
// =====================================================================

use("Ecualizer");

function recrearVista(nombre, fuente, pipeline) {
    db.getCollection(nombre).drop();
    db.createView(nombre, fuente, pipeline);
    print("Vista creada: " + nombre);
}

// =====================================================================
//  1) vw_contratos_detalle
//     Un contrato por fila con el PAÍS de la discográfica resuelto
//     (la discográfica embebida sólo guarda id + nombre). Alimenta el
//     listado de contratos del admin y el "Mis Contratos" del artista.
// =====================================================================
recrearVista("vw_contratos_detalle", "ContratosDiscograficos", [
    { $lookup: {
        from: "Discograficas",
        localField: "discograficaAsociada.discograficaId",
        foreignField: "discograficaId",
        as: "_d"
    } },
    { $set: { _d: { $arrayElemAt: ["$_d", 0] } } },
    { $project: {
        _id: 0,
        contratoId:               { $toString: { $ifNull: ["$contratoId", "$_id"] } },
        artistaId:                { $toString: "$artistaAsociado.artistaId" },
        Artista:                  { $ifNull: ["$artistaAsociado.nombreArtistico", "—"] },
        discograficaId:           { $toString: "$discograficaAsociada.discograficaId" },
        Discografica:             { $ifNull: ["$discograficaAsociada.discograficaNombre", "—"] },
        PaisDiscografica:         { $ifNull: ["$_d.paisOrigen", "—"] },
        fechaInicio:              1,
        fechaFin:                 1,
        porcentajeArtista:        { $ifNull: ["$porcentajeArtista", 0] },
        porcentajeDiscografica:   { $ifNull: ["$porcentajeDiscografica", 0] },
        estadoContrato:           1
    } },
    { $sort: { fechaInicio: -1 } }
]);

// =====================================================================
//  2) vw_contratos_kpis_artista
//     Conteo de contratos por artista y estado (KPIs del dashboard artista).
//       db.vw_contratos_kpis_artista.find({ artistaId: "<id>" })
// =====================================================================
recrearVista("vw_contratos_kpis_artista", "ContratosDiscograficos", [
    { $group: {
        _id: "$artistaAsociado.artistaId",
        Artista:     { $first: "$artistaAsociado.nombreArtistico" },
        Total:       { $sum: 1 },
        Activos:     { $sum: { $cond: [{ $eq: ["$estadoContrato", "Activo"] }, 1, 0] } },
        Finalizados: { $sum: { $cond: [{ $eq: ["$estadoContrato", "Finalizado"] }, 1, 0] } },
        Cancelados:  { $sum: { $cond: [{ $eq: ["$estadoContrato", "Cancelado"] }, 1, 0] } }
    } },
    { $project: {
        _id: 0,
        artistaId: { $toString: "$_id" },
        Artista: 1, Total: 1, Activos: 1, Finalizados: 1, Cancelados: 1
    } },
    { $sort: { Total: -1 } }
]);

// =====================================================================
//  3) vw_discograficas_resumen
//     Discográficas + nº de contratos asociados (panel admin comercial).
// =====================================================================
recrearVista("vw_discograficas_resumen", "Discograficas", [
    { $lookup: {
        from: "ContratosDiscograficos",
        localField: "discograficaId",
        foreignField: "discograficaAsociada.discograficaId",
        as: "_c"
    } },
    { $project: {
        _id: 0,
        discograficaId:    { $toString: { $ifNull: ["$discograficaId", "$_id"] } },
        Nombre:            "$nombreDiscografica",
        Pais:              { $ifNull: ["$paisOrigen", "—"] },
        Correo:            "$correoContacto",
        Telefono:          "$telefonoContacto",
        TotalContratos:    { $size: "$_c" },
        ContratosActivos:  { $size: { $filter: {
            input: "$_c", as: "c",
            cond: { $eq: ["$$c.estadoContrato", "Activo"] }
        } } }
    } },
    { $sort: { Nombre: 1 } }
]);

print("✔ Vistas de industria (discográficas/contratos) creadas correctamente.");
