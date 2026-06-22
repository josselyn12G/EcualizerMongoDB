use Ecualizer;

// Indice opcional para validar unicidad y acelerar consultas por alias de oyente.
// No reemplaza el login por correo; simplemente deja listo el soporte para
// que el modulo de usuarios pueda buscar por alias sin escanear la coleccion.
db.Usuarios.createIndex(
  { "perfilOyente.alias": 1 },
  {
    name: "idx_alias_unique_sparse",
    unique: true,
    sparse: true
  }
);