//  Ecualizer · VISTAS DE — Albums, Cancion, Playlist, Reproduccion, Likes
// ---------------------------------------------------------------------
//  CÓMO EJECUTAR EN COMPASS:
//    1. Abre Compass y conéctate a tu cluster (ecualizer...mongodb.net).
//    2. Abajo, abre la pestaña ">_ MONGOSH".
//    3. Copia y pega TODO este contenido y presiona Enter.
//
//  El script apunta a "Ecualizer" con getSiblingDB.
//  Es IDEMPOTENTE: elimina y recrea cada vista sin romper las demás.
// =====================================================================

const eq = db.getSiblingDB("Ecualizer");

// ═════════════════════════════════════════════════════════════════════
//  BLOQUE 1 · ALBUMS
//  Colección base: Albums
//  Campos clave: albumId, tituloAlbum, estadoAlbum, artistaId,
//                nombreArtistico, tipoAlbum{nombreTipo}, fechaLanzamiento
// ═════════════════════════════════════════════════════════════════════

// ── 1.1  vw_albums_activos ────────────────────────────────────────────
//  Lista limpia de álbumes activos con tipo y artista.
//  USADA EN: catalogo/views/usuario/album_views.py (UsuarioAlbumListView)
//            catalogo/views/artista/album_views.py (ArtistaAlbumListView)
eq.getCollection("vw_albums_activos").drop();
eq.createView("vw_albums_activos", "Albums", [
  { $match: { estadoAlbum: "activo" } },
  { $project: {
      _id: 0,
      idAlbum: { $toString: { $ifNull: ["$albumId", "$_id"] } },
      tituloAlbum: 1,
      nombreArtistico: 1,
      nombreTipo: "$tipoAlbum.nombreTipo",
      fechaLanzamiento: 1,
      estadoAlbum: 1,
      descripcion: "$descripcionAlbum"
  }},
  { $sort: { fechaLanzamiento: -1 } }
]);
print("Vista creada: vw_albums_activos");

// ── 1.2  vw_albums_con_canciones ─────────────────────────────────────
//  Álbumes enriquecidos con sus canciones (lookup + unwind).
//  USADA EN: catalogo/views/usuario/album_views.py (UsuarioAlbumDetailView)
//            catalogo/views/artista/album_views.py (ArtistaAlbumDetailView)
eq.getCollection("vw_albums_con_canciones").drop();
eq.createView("vw_albums_con_canciones", "Albums", [
  { $lookup: {
      from: "Cancion",
      localField: "albumId",
      foreignField: "albumId",
      as: "canciones"
  }},
  { $project: {
      _id: 0,
      idAlbum: { $toString: { $ifNull: ["$albumId", "$_id"] } },
      tituloAlbum: 1,
      nombreArtistico: 1,
      estadoAlbum: 1,
      fechaLanzamiento: 1,
      totalCanciones: { $size: "$canciones" },
      canciones: {
        $map: {
          input: "$canciones",
          as: "c",
          in: {
            idCancion: { $toString: { $ifNull: ["$$c.cancionId", "$$c._id"] } },
            tituloCancion: "$$c.tituloCancion",
            numeroPista: "$$c.numeroPista",
            duracion: "$$c.duracion",
            estadoCancion: "$$c.estadoCancion",
            totalReproducciones: { $ifNull: ["$$c.totalReproducciones", 0] }
          }
        }
      }
  }},
  { $sort: { fechaLanzamiento: -1 } }
]);
print("Vista creada: vw_albums_con_canciones");

// ── 1.3  vw_top_albums ───────────────────────────────────────────────
//  Top álbumes por suma de reproducciones de sus canciones.
//  USADA EN: analitica / industria (reportes de escuchas por álbum)
eq.getCollection("vw_top_albums").drop();
eq.createView("vw_top_albums", "Albums", [
  { $match: { estadoAlbum: "activo" } },
  { $lookup: {
      from: "Cancion",
      localField: "albumId",
      foreignField: "albumId",
      as: "canciones"
  }},
  { $project: {
      _id: 0,
      idAlbum: { $toString: { $ifNull: ["$albumId", "$_id"] } },
      tituloAlbum: 1,
      nombreArtistico: 1,
      totalReproducciones: { $sum: "$canciones.totalReproducciones" }
  }},
  { $sort: { totalReproducciones: -1 } }
]);
print("Vista creada: vw_top_albums");

// ═════════════════════════════════════════════════════════════════════
//  BLOQUE 2 · CANCION
//  Colección base: Cancion
//  Campos clave: cancionId, tituloCancion, estadoCancion, albumId,
//                duracion, calidadKbps, totalReproducciones,
//                generos[{nombreGenero}], artistas[{artistaId, nombreArtistico}]
// ═════════════════════════════════════════════════════════════════════

// ── 2.1  vw_canciones_activas ────────────────────────────────────────
//  Canciones activas enriquecidas con el álbum (lookup).
//  USADA EN: catalogo/views/usuario/cancion_views.py (UsuarioCancionListView)
//            catalogo/services/cancion_mongo.py (listar_canciones)
eq.getCollection("vw_canciones_activas").drop();
eq.createView("vw_canciones_activas", "Cancion", [
  { $match: { estadoCancion: "activa" } },
  { $lookup: {
      from: "Albums",
      localField: "albumId",
      foreignField: "albumId",
      as: "_album"
  }},
  { $set: { _album: { $arrayElemAt: ["$_album", 0] } } },
  { $project: {
      _id: 0,
      idCancion: { $toString: { $ifNull: ["$cancionId", "$_id"] } },
      nombreCancion: "$tituloCancion",
      duracion: 1,
      calidadKbps: 1,
      totalReproducciones: { $ifNull: ["$totalReproducciones", 0] },
      estadoCancion: 1,
      numeroPista: 1,
      idAlbum: { $toString: "$albumId" },
      tituloAlbum: "$_album.tituloAlbum",
      nombreArtistico: { $arrayElemAt: ["$artistas.nombreArtistico", 0] },
      generos: "$generos.nombreGenero"
  }},
  { $sort: { totalReproducciones: -1 } }
]);
print("Vista creada: vw_canciones_activas");

// ── 2.2  vw_canciones_por_genero ─────────────────────────────────────
//  Una fila por cada par (cancion, género); facilita filtrar por género.
//  USADA EN: catalogo/views/usuario/cancion_views.py (UsuarioCancionFilterView)
//            catalogo/services/cancion_mongo.py (filtrar_canciones_genero)
eq.getCollection("vw_canciones_por_genero").drop();
eq.createView("vw_canciones_por_genero", "Cancion", [
  { $match: { estadoCancion: "activa" } },
  { $unwind: "$generos" },
  { $lookup: {
      from: "Albums",
      localField: "albumId",
      foreignField: "albumId",
      as: "_album"
  }},
  { $set: { _album: { $arrayElemAt: ["$_album", 0] } } },
  { $project: {
      _id: 0,
      idCancion: { $toString: { $ifNull: ["$cancionId", "$_id"] } },
      nombreCancion: "$tituloCancion",
      duracion: 1,
      totalReproducciones: { $ifNull: ["$totalReproducciones", 0] },
      nombreGenero: "$generos.nombreGenero",
      tituloAlbum: "$_album.tituloAlbum",
      nombreArtistico: { $arrayElemAt: ["$artistas.nombreArtistico", 0] }
  }},
  { $sort: { nombreGenero: 1, totalReproducciones: -1 } }
]);
print("Vista creada: vw_canciones_por_genero");

// ── 2.3  vw_top_canciones ────────────────────────────────────────────
//  Top 50 canciones activas ordenadas por reproducciones.
//  USADA EN: catalogo/services/cancion_mongo.py (top_canciones)
//            Página de inicio / widget "Popular"
eq.getCollection("vw_top_canciones").drop();
eq.createView("vw_top_canciones", "Cancion", [
  { $match: { estadoCancion: "activa" } },
  { $sort: { totalReproducciones: -1 } },
  { $limit: 50 },
  { $project: {
      _id: 0,
      idCancion: { $toString: { $ifNull: ["$cancionId", "$_id"] } },
      nombreCancion: "$tituloCancion",
      totalReproducciones: { $ifNull: ["$totalReproducciones", 0] },
      nombreArtistico: { $arrayElemAt: ["$artistas.nombreArtistico", 0] }
  }}
]);
print("Vista creada: vw_top_canciones");

// ═════════════════════════════════════════════════════════════════════
//  BLOQUE 3 · PLAYLIST
//  Colección base: Playlist
//  Patrón Extended Reference: canciones[] y colaboradores[] embebidos.
//  Campos clave: playlistId, nombrePlaylist, tipoVisibilidad,
//                tipoPlaylist, colaboradores[{userId, rolPlaylist}],
//                canciones[{cancionId, nombreCancion, fechaAgregada}]
// ═════════════════════════════════════════════════════════════════════

// ── 3.1  vw_playlists_publicas ───────────────────────────────────────
//  Playlists públicas con total de canciones y datos del creador.
//  USADA EN: biblioteca/mongo_service.py (listar_playlists con visibilidad='Publica')
eq.getCollection("vw_playlists_publicas").drop();
eq.createView("vw_playlists_publicas", "Playlist", [
  { $match: { tipoVisibilidad: "Publica" } },
  { $set: {
      _creador: {
        $arrayElemAt: [
          { $filter: {
              input: "$colaboradores",
              as: "c",
              cond: { $eq: ["$$c.rolPlaylist", "Creador"] }
          }},
          0
        ]
      }
  }},
  { $project: {
      _id: 0,
      idPlaylist: { $toString: { $ifNull: ["$playlistId", "$_id"] } },
      nombrePlaylist: 1,
      descripcionPlaylist: 1,
      tipoPlaylist: 1,
      tipoVisibilidad: 1,
      fechaCreacion: 1,
      TotalCanciones: { $size: { $ifNull: ["$canciones", []] } },
      creadorId: { $toString: "$_creador.userId" }
  }},
  { $sort: { fechaCreacion: -1 } }
]);
print("Vista creada: vw_playlists_publicas");

// ── 3.2  vw_playlists_con_canciones ──────────────────────────────────
//  Playlists con lista de canciones enriquecida (lookup a Cancion).
//  USADA EN: biblioteca/mongo_service.py (get_canciones_playlist)
//            biblioteca/views.py (DetallePlaylistView)
eq.getCollection("vw_playlists_con_canciones").drop();
eq.createView("vw_playlists_con_canciones", "Playlist", [
  { $unwind: { path: "$canciones", preserveNullAndEmptyArrays: true } },
  { $lookup: {
      from: "Cancion",
      localField: "canciones.cancionId",
      foreignField: "cancionId",
      as: "_c"
  }},
  { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
  { $group: {
      _id: { $ifNull: ["$playlistId", "$_id"] },
      nombrePlaylist: { $first: "$nombrePlaylist" },
      tipoVisibilidad: { $first: "$tipoVisibilidad" },
      tipoPlaylist: { $first: "$tipoPlaylist" },
      canciones: {
        $push: {
          $cond: {
            if: { $gt: ["$canciones.cancionId", null] },
            then: {
              idCancion: { $toString: { $ifNull: ["$_c.cancionId", "$_c._id"] } },
              nombreCancion: "$_c.tituloCancion",
              duracion: "$_c.duracion",
              totalReproducciones: { $ifNull: ["$_c.totalReproducciones", 0] },
              nombreArtistico: { $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] },
              fechaAgregada: "$canciones.fechaAgregada"
            },
            else: "$$REMOVE"
          }
        }
      }
  }},
  { $project: {
      _id: 0,
      idPlaylist: { $toString: "$_id" },
      nombrePlaylist: 1,
      tipoVisibilidad: 1,
      tipoPlaylist: 1,
      TotalCanciones: { $size: "$canciones" },
      canciones: 1
  }}
]);
print("Vista creada: vw_playlists_con_canciones");

// ═════════════════════════════════════════════════════════════════════
//  BLOQUE 4 · REPRODUCCION
//  Colección base: Reproduccion (append-only, eventos de escucha)
//  Campos clave: reproduccionId, usuarioId, cancionId,
//                fechaHora, pais, duracionEscuchada, fueSaltada
// ═════════════════════════════════════════════════════════════════════

// ── 4.1  vw_reproducciones_detalle ───────────────────────────────────
//  Eventos de reproducción con nombre de canción, artista y álbum.
//  USADA EN: analitica — dashboards de escuchas recientes
//            catalogo/services/cancion_mongo.py (historial_reproduccion)
eq.getCollection("vw_reproducciones_detalle").drop();
eq.createView("vw_reproducciones_detalle", "Reproduccion", [
  { $sort: { fechaHora: -1 } },
  { $lookup: {
      from: "Cancion",
      localField: "cancionId",
      foreignField: "cancionId",
      as: "_c"
  }},
  { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
  { $lookup: {
      from: "Albums",
      localField: "_c.albumId",
      foreignField: "albumId",
      as: "_a"
  }},
  { $set: { _a: { $arrayElemAt: ["$_a", 0] } } },
  { $project: {
      _id: 0,
      reproduccionId: { $toString: "$reproduccionId" },
      usuarioId: { $toString: "$usuarioId" },
      fechaHora: 1,
      pais: 1,
      duracionEscuchada: 1,
      fueSaltada: 1,
      nombreCancion: "$_c.tituloCancion",
      nombreArtistico: { $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] },
      tituloAlbum: "$_a.tituloAlbum"
  }}
]);
print("Vista creada: vw_reproducciones_detalle");

// ── 4.2  vw_reproducciones_por_pais ──────────────────────────────────
//  Totales de reproducciones agrupados por país.
//  USADA EN: industria — reportes geográficos de consumo musical
eq.getCollection("vw_reproducciones_por_pais").drop();
eq.createView("vw_reproducciones_por_pais", "Reproduccion", [
  { $group: {
      _id: "$pais",
      totalReproducciones: { $sum: 1 },
      totalEscuchadas: { $sum: "$duracionEscuchada" },
      saltadas: { $sum: { $cond: ["$fueSaltada", 1, 0] } }
  }},
  { $project: {
      _id: 0,
      pais: "$_id",
      totalReproducciones: 1,
      totalEscuchadas: 1,
      saltadas: 1,
      tasaSalto: {
        $round: [
          { $multiply: [
              { $divide: ["$saltadas", { $max: ["$totalReproducciones", 1] }] },
              100
          ]},
          1
        ]
      }
  }},
  { $sort: { totalReproducciones: -1 } }
]);
print("Vista creada: vw_reproducciones_por_pais");

// ── 4.3  vw_reproducciones_por_cancion ───────────────────────────────
//  Totales de reproducciones agrupados por canción.
//  USADA EN: analitica/industria — equivalente a SP_ReporteReproduccionesPorCancion
eq.getCollection("vw_reproducciones_por_cancion").drop();
eq.createView("vw_reproducciones_por_cancion", "Reproduccion", [
  { $group: {
      _id: "$cancionId",
      totalReproducciones: { $sum: 1 },
      duracionTotal: { $sum: "$duracionEscuchada" },
      saltadas: { $sum: { $cond: ["$fueSaltada", 1, 0] } }
  }},
  { $lookup: {
      from: "Cancion",
      localField: "_id",
      foreignField: "cancionId",
      as: "_c"
  }},
  { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
  { $project: {
      _id: 0,
      idCancion: { $toString: "$_id" },
      nombreCancion: "$_c.tituloCancion",
      nombreArtistico: { $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] },
      totalReproducciones: 1,
      duracionTotal: 1,
      saltadas: 1
  }},
  { $sort: { totalReproducciones: -1 } }
]);
print("Vista creada: vw_reproducciones_por_cancion");

// ═════════════════════════════════════════════════════════════════════
//  BLOQUE 5 · LIKES
//  Colección base: Likes
//  Campos clave: likeId, usuarioId, cancionId, fechaLike
// ═════════════════════════════════════════════════════════════════════

// ── 5.1  vw_canciones_likeadas ───────────────────────────────────────
//  Likes enriquecidos con datos completos de la canción y el álbum.
//  USADA EN: biblioteca/mongo_service.py (get_canciones_liked)
//            biblioteca/views.py (MisCancionesLikedView)
eq.getCollection("vw_canciones_likeadas").drop();
eq.createView("vw_canciones_likeadas", "Likes", [
  { $sort: { fechaLike: -1 } },
  { $lookup: {
      from: "Cancion",
      localField: "cancionId",
      foreignField: "cancionId",
      as: "_c"
  }},
  { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
  { $lookup: {
      from: "Albums",
      localField: "_c.albumId",
      foreignField: "albumId",
      as: "_a"
  }},
  { $set: { _a: { $arrayElemAt: ["$_a", 0] } } },
  { $match: { "_c.estadoCancion": "activa" } },
  { $project: {
      _id: 0,
      usuarioId: { $toString: "$usuarioId" },
      idCancion: { $toString: { $ifNull: ["$_c.cancionId", "$_c._id"] } },
      nombreCancion: "$_c.tituloCancion",
      duracion: "$_c.duracion",
      calidadKbps: "$_c.calidadKbps",
      totalReproducciones: { $ifNull: ["$_c.totalReproducciones", 0] },
      idAlbum: { $toString: "$_c.albumId" },
      tituloAlbum: "$_a.tituloAlbum",
      nombreArtistico: { $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] },
      fechaLike: 1
  }}
]);
print("Vista creada: vw_canciones_likeadas");

// ── 5.2  vw_top_liked ────────────────────────────────────────────────
//  Canciones activas ordenadas por número de likes recibidos.
//  USADA EN: industria — reportes de popularidad social
eq.getCollection("vw_top_liked").drop();
eq.createView("vw_top_liked", "Likes", [
  { $group: {
      _id: "$cancionId",
      totalLikes: { $sum: 1 }
  }},
  { $lookup: {
      from: "Cancion",
      localField: "_id",
      foreignField: "cancionId",
      as: "_c"
  }},
  { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
  { $match: { "_c.estadoCancion": "activa" } },
  { $project: {
      _id: 0,
      idCancion: { $toString: "$_id" },
      nombreCancion: "$_c.tituloCancion",
      nombreArtistico: { $arrayElemAt: ["$_c.artistas.nombreArtistico", 0] },
      totalLikes: 1
  }},
  { $sort: { totalLikes: -1 } }
]);
print("Vista creada: vw_top_liked");

// ═════════════════════════════════════════════════════════════════════
//  RESUMEN — verificar que todas las vistas existen
// ═════════════════════════════════════════════════════════════════════
const vistasTony = [
  "vw_albums_activos",
  "vw_albums_con_canciones",
  "vw_top_albums",
  "vw_canciones_activas",
  "vw_canciones_por_genero",
  "vw_top_canciones",
  "vw_playlists_publicas",
  "vw_playlists_con_canciones",
  "vw_reproducciones_detalle",
  "vw_reproducciones_por_pais",
  "vw_reproducciones_por_cancion",
  "vw_canciones_likeadas",
  "vw_top_liked"
];

const colecciones = eq.getCollectionNames();
print("\n=== Verificación de vistas creadas ===");
vistasTony.forEach(v => {
  const ok = colecciones.includes(v);
  print((ok ? "✔" : "✘") + " " + v);
});
print("=====================================");
print("Total vistas Tony: " + vistasTony.length);
print("✔ Script completado correctamente.");

// ═════════════════════════════════════════════════════════════════════
//  CONSULTAS DE EJEMPLO (pegar en MongoSH para probar cada vista)
// ═════════════════════════════════════════════════════════════════════

// --- ALBUMS ---

// 1. Ver los 5 álbumes activos más recientes
// eq.vw_albums_activos.find().limit(5).toArray();

// 2. Álbumes de un artista específico (reemplaza con el ObjectId real)
// eq.vw_albums_activos.find({ nombreArtistico: "Nombre Artista" }).toArray();

// 3. Detalle de álbum con su lista de canciones
// eq.vw_albums_con_canciones.find({ tituloAlbum: "Nombre Album" }, { canciones: 1 }).toArray();

// 4. Top 5 álbumes por reproducciones
// eq.vw_top_albums.find().limit(5).toArray();

// --- CANCION ---

// 5. Todas las canciones activas ordenadas por popularidad
// eq.vw_canciones_activas.find().limit(10).toArray();

// 6. Canciones del género "Rock"
// eq.vw_canciones_por_genero.find({ nombreGenero: "Rock" }).toArray();

// 7. Top 10 canciones más escuchadas
// eq.vw_top_canciones.find().limit(10).toArray();

// --- PLAYLIST ---

// 8. Playlists públicas con más de 5 canciones
// eq.vw_playlists_publicas.find({ TotalCanciones: { $gte: 5 } }).toArray();

// 9. Canciones de una playlist específica
// eq.vw_playlists_con_canciones.find({ nombrePlaylist: "Mi Playlist" }).toArray();

// --- REPRODUCCION ---

// 10. Últimas 20 reproducciones con detalle
// eq.vw_reproducciones_detalle.find().limit(20).toArray();

// 11. Reproducciones por país (top 5)
// eq.vw_reproducciones_por_pais.find().limit(5).toArray();

// 12. Canción más reproducida según la colección Reproduccion
// eq.vw_reproducciones_por_cancion.find().limit(1).toArray();

// --- LIKES ---

// 13. Canciones likeadas de un usuario específico
// eq.vw_canciones_likeadas.find({ usuarioId: "PEGA_AQUI_EL_ID_DEL_USUARIO" }).toArray();

// 14. Top 10 canciones por likes
// eq.vw_top_liked.find().limit(10).toArray();

// ═════════════════════════════════════════════════════════════════════
//  CONSULTAS AVANZADAS (agregaciones ad-hoc, sin vista)
// ═════════════════════════════════════════════════════════════════════

// 15. Historial de reproducción de un usuario con nombre de canción
// eq.Reproduccion.aggregate([
//   { $match: { usuarioId: ObjectId("PEGA_AQUI_EL_OBJECTID") } },
//   { $sort: { fechaHora: -1 } }, { $limit: 20 },
//   { $lookup: { from: "Cancion", localField: "cancionId", foreignField: "cancionId", as: "_c" } },
//   { $set: { _c: { $arrayElemAt: ["$_c", 0] } } },
//   { $project: { fechaHora: 1, pais: 1, nombreCancion: "$_c.tituloCancion" } }
// ]).toArray();

// 16. Verificar si una canción está likeada por un usuario
// eq.Likes.findOne({
//   usuarioId: ObjectId("USUARIO_OID"),
//   cancionId: ObjectId("CANCION_OID")
// });

// 17. Playlists de un usuario (como creador o colaborador)
// eq.Playlist.find({ "colaboradores.userId": ObjectId("USUARIO_OID") }).toArray();

// 18. Géneros distintos disponibles en la colección Cancion
// eq.Cancion.distinct("generos.nombreGenero");

// 19. Agregar una canción a una playlist (ejemplo de actualización)
// eq.Playlist.updateOne(
//   { playlistId: ObjectId("PLAYLIST_OID") },
//   { $push: { canciones: {
//       cancionId: ObjectId("CANCION_OID"),
//       nombreCancion: "Nombre de la Canción",
//       fechaAgregada: new Date()
//   }}}
// );

// 20. Registrar una reproducción manualmente
// eq.Reproduccion.insertOne({
//   reproduccionId: new ObjectId(),
//   usuarioId: ObjectId("USUARIO_OID"),
//   cancionId: ObjectId("CANCION_OID"),
//   fechaHora: new Date(),
//   pais: "Ecuador",
//   duracionEscuchada: 180,
//   fueSaltada: false
// });
