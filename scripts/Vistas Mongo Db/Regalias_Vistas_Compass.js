// =====================================================================
//  Ecualizer · VISTAS de REGALÍAS — versión para MongoDB COMPASS
// ---------------------------------------------------------------------
//  CÓMO EJECUTAR EN COMPASS:
//    1. Abre Compass y conéctate a tu cluster (ecualizer...mongodb.net).
//    2. Abajo, abre la pestaña  ">_ MONGOSH".
//    3. Copia y pega TODO este contenido y presiona Enter.
//
//  No necesitas seleccionar la base: el script apunta a "Ecualizer" con
//  getSiblingDB. Es idempotente (elimina y vuelve a crear cada vista).
// =====================================================================

const eq = db.getSiblingDB("Ecualizer");

// ── 1) vw_regalias_artista  (histórico con nombre de canción y álbum) ──
eq.getCollection("vw_regalias_artista").drop();
eq.createView("vw_regalias_artista", "Regalias", [
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
print("Vista creada: vw_regalias_artista");

// ── 2) vw_regalias_mensual_artista  (evolución mes a mes) ──────────────
eq.getCollection("vw_regalias_mensual_artista").drop();
eq.createView("vw_regalias_mensual_artista", "Regalias", [
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
print("Vista creada: vw_regalias_mensual_artista");

// ── 3) vw_reproducciones_artista  (para el pendiente de cierre) ────────
eq.getCollection("vw_reproducciones_artista").drop();
eq.createView("vw_reproducciones_artista", "Reproduccion", [
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
print("Vista creada: vw_reproducciones_artista");

print("✔ Listo: 3 vistas de regalías creadas en la base Ecualizer.");

// (Opcional) comprobar que existen:
eq.getCollectionNames().filter(n => n.startsWith("vw_regalias") || n === "vw_reproducciones_artista");
