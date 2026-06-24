// =====================================================================
//  Ecualizer · VISTAS de MongoDB para la ANALÍTICA del ARTISTA y ADMIN
// ---------------------------------------------------------------------
//  Crea las vistas que alimentan el dashboard de analítica del artista
//  (/usuarios/perfil/artista/analytics/) y el ranking del administrador.
//
//  Cómo ejecutar:
//    • Compass / Atlas: abre un Playground en la base "Ecualizer",
//      pega este contenido y pulsa "Run".
//    • mongosh:
//        mongosh "<TU_URI>/Ecualizer" --file "scripts/Vistas Mongo Db/Analitica_Artista_Vistas_Compass.js"
//
//  Es idempotente: si la vista ya existe la elimina y la vuelve a crear.
//  Modelo de datos usado:
//    - Reproduccion: { cancionId, usuarioId, fechaHora, pais, liquidada }
//    - Cancion:      { cancionId, tituloCancion, totalReproducciones,
//                      albumId, numeroPista, artistas:[{artistaId,nombreArtistico}] }
//    - Albums:       { albumId, tituloAlbum, nombreArtistico }
// =====================================================================

use("Ecualizer");

function recrearVista(nombre, fuente, pipeline) {
    db.getCollection(nombre).drop();          // si no existe, no pasa nada
    db.createView(nombre, fuente, pipeline);
    print("Vista creada: " + nombre);
}

// =====================================================================
//  1) vw_artista_canciones
//     Una fila por (artista, canción) con sus reproducciones acumuladas.
//     Base para "Top 10" y "Reproducciones por canción".
// =====================================================================
recrearVista("vw_artista_canciones", "Cancion", [
    { $unwind: "$artistas" },
    { $lookup: { from: "Albums", localField: "albumId", foreignField: "albumId", as: "_a" } },
    { $set: { _a: { $arrayElemAt: ["$_a", 0] } } },
    { $project: {
        _id: 0,
        artistaId:            "$artistas.artistaId",
        nombreArtistico:      "$artistas.nombreArtistico",
        cancionId:            { $toString: { $ifNull: ["$cancionId", "$_id"] } },
        NombreCancion:        "$tituloCancion",
        TotalReproducciones:  { $ifNull: ["$totalReproducciones", 0] },
        NumeroPista:          "$numeroPista",
        albumId:              "$albumId",
        Album:                { $ifNull: ["$_a.tituloAlbum", "—"] },
        estadoCancion:        "$estadoCancion",
    } },
    { $sort: { TotalReproducciones: -1 } },
]);

// =====================================================================
//  2) vw_artista_geografia
//     Reproducciones por artista y país (de la canción reproducida).
//     Alimenta el mapa/listado de "Distribución geográfica".
// =====================================================================
recrearVista("vw_artista_geografia", "Reproduccion", [
    { $lookup: { from: "Cancion", localField: "cancionId", foreignField: "cancionId", as: "_c" } },
    { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
    { $unwind: "$_c.artistas" },
    { $group: {
        _id: { artistaId: "$_c.artistas.artistaId", pais: { $ifNull: ["$pais", "Desconocido"] } },
        Total: { $sum: 1 },
    } },
    { $project: {
        _id: 0,
        artistaId: "$_id.artistaId",
        Pais:      "$_id.pais",
        Total:     1,
    } },
    { $sort: { Total: -1 } },
]);

// =====================================================================
//  3) vw_artista_reproducciones_mensuales
//     Reproducciones por artista, canción y período (YYYY-MM).
//     Base para oyentes/crecimiento mensual y series temporales.
// =====================================================================
recrearVista("vw_artista_reproducciones_mensuales", "Reproduccion", [
    { $lookup: { from: "Cancion", localField: "cancionId", foreignField: "cancionId", as: "_c" } },
    { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
    { $unwind: "$_c.artistas" },
    { $group: {
        _id: {
            artistaId: "$_c.artistas.artistaId",
            periodo:   { $dateToString: { format: "%Y-%m", date: "$fechaHora" } },
        },
        Reproducciones: { $sum: 1 },
        OyentesUnicos:  { $addToSet: "$usuarioId" },
    } },
    { $project: {
        _id: 0,
        artistaId:      "$_id.artistaId",
        periodo:        "$_id.periodo",
        Reproducciones: 1,
        OyentesUnicos:  { $size: "$OyentesUnicos" },
    } },
    { $sort: { periodo: 1 } },
]);

// =====================================================================
//  4) vw_admin_ranking_mensual
//     Top global de canciones del ÚLTIMO MES por reproducciones reales
//     (colección Reproduccion). Alimenta el "Top 20" del panel admin.
//     Nota: el filtro temporal de 30 días se aplica en la consulta, p.ej.:
//       db.vw_admin_ranking_mensual.find().sort({TotalReproduccionesGlobales:-1}).limit(20)
// =====================================================================
recrearVista("vw_admin_ranking_mensual", "Reproduccion", [
    { $group: {
        _id: "$cancionId",
        TotalReproduccionesGlobales: { $sum: 1 },
        oyentes: { $addToSet: "$usuarioId" },
        ultima:  { $max: "$fechaHora" },
    } },
    { $lookup: { from: "Cancion", localField: "_id", foreignField: "cancionId", as: "_c" } },
    { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
    { $project: {
        _id: 0,
        cancionId:                   { $toString: "$_id" },
        Cancion:                     { $ifNull: ["$_c.tituloCancion", "—"] },
        Artista:                     { $ifNull: [{ $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] }, "—"] },
        TotalReproduccionesGlobales: 1,
        OyentesUnicos:               { $size: "$oyentes" },
        UltimaReproduccion:          "$ultima",
    } },
    { $sort: { TotalReproduccionesGlobales: -1 } },
]);

// =====================================================================
//  5) vw_artista_resumen
//     KPI rápido por artista: nº de canciones y reproducciones totales.
// =====================================================================
recrearVista("vw_artista_resumen", "Cancion", [
    { $unwind: "$artistas" },
    { $group: {
        _id: "$artistas.artistaId",
        nombreArtistico:     { $first: "$artistas.nombreArtistico" },
        TotalCanciones:      { $sum: 1 },
        TotalReproducciones: { $sum: { $ifNull: ["$totalReproducciones", 0] } },
    } },
    { $project: {
        _id: 0,
        artistaId:           "$_id",
        nombreArtistico:     1,
        TotalCanciones:      1,
        TotalReproducciones: 1,
    } },
    { $sort: { TotalReproducciones: -1 } },
]);

print("✔ Vistas de analítica del artista/admin creadas correctamente.");
