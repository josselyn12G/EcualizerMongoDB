// =====================================================================
//  Ecualizer · VISTAS de MongoDB para REGALÍAS del artista
// ---------------------------------------------------------------------
//  Ejecuta este archivo sobre la base "Ecualizer" (mongosh, Compass
//  Playground o Atlas) para crear las 3 vistas que alimentan la página
//  de Monetización del artista.
//
//  Cómo ejecutar (mongosh):
//    mongosh "mongodb+srv://...@ecualizer.mles0h5.mongodb.net/Ecualizer" \
//            --file "scripts/Vistas Mongo Db/Regalias_Vistas.js"
//
//  O en Compass / Atlas: abre un Playground, pega este contenido y "Run".
//  Es idempotente: elimina la vista si ya existe y la vuelve a crear.
// =====================================================================

use("Ecualizer");

// ── Util: recrear una vista (drop + createView) ──────────────────────
function recrearVista(nombre, fuente, pipeline) {
    db.getCollection(nombre).drop();          // si no existe, no pasa nada
    db.createView(nombre, fuente, pipeline);
    print("Vista creada: " + nombre);
}

// =====================================================================
//  1) vw_regalias_artista
//     Detalle de regalías YA cerradas (colección Regalias) con el nombre
//     de la canción y del álbum resueltos. Alimenta el "Histórico".
// =====================================================================
recrearVista("vw_regalias_artista", "Regalias", [
    { $lookup: { from: "Cancion", localField: "cancionId", foreignField: "cancionId", as: "_c" } },
    { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
    { $lookup: { from: "Albums", localField: "_c.albumId", foreignField: "albumId", as: "_a" } },
    { $set: { _a: { $arrayElemAt: ["$_a", 0] } } },
    { $project: {
        _id: 0,
        artistaId: 1,
        periodo: 1,
        anio: { $toInt: { $substrBytes: ["$periodo", 0, 4] } },
        mes:  { $toInt: { $substrBytes: ["$periodo", 5, 2] } },
        pais: "$paisReproduccion",
        reproducciones: "$cantidadReproducciones",
        montoBruto: "$montoTotalGenerado",
        montoArtista: "$montoArtista",
        montoDiscografica: "$montoDiscografica",
        cancion: { $ifNull: ["$_c.tituloCancion", "—"] },
        album:   { $ifNull: ["$_a.tituloAlbum", "—"] },
        estadoPago: { $ifNull: ["$estadoPago", "Pendiente"] }
    } }
]);

// =====================================================================
//  2) vw_regalias_mensual_artista
//     Regalías agrupadas por (artista, periodo). Alimenta el gráfico de
//     evolución mes a mes.
// =====================================================================
recrearVista("vw_regalias_mensual_artista", "Regalias", [
    { $group: {
        _id: { artistaId: "$artistaId", periodo: "$periodo" },
        reproducciones: { $sum: "$cantidadReproducciones" },
        montoBruto:     { $sum: "$montoTotalGenerado" },
        montoArtista:   { $sum: "$montoArtista" }
    } },
    { $project: {
        _id: 0,
        artistaId: "$_id.artistaId",
        periodo: "$_id.periodo",
        reproducciones: 1,
        montoBruto: 1,
        montoArtista: 1
    } },
    { $sort: { periodo: 1 } }
]);

// =====================================================================
//  3) vw_reproducciones_artista
//     Cada reproducción "explotada" por artista de la canción. Alimenta
//     el cálculo en vivo de "Pendiente de cierre" (reproducciones × tarifa).
// =====================================================================
recrearVista("vw_reproducciones_artista", "Reproduccion", [
    { $lookup: { from: "Cancion", localField: "cancionId", foreignField: "cancionId", as: "_c" } },
    { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
    { $unwind: "$_c.artistas" },
    { $project: {
        _id: 0,
        artistaId: "$_c.artistas.artistaId",
        cancionId: 1,
        cancion: "$_c.tituloCancion",
        pais: 1,
        fechaHora: 1
    } }
]);

print("✔ Vistas de regalías listas.");
