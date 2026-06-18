from .auth_views import (
    index_usuarios,
    LoginView,
    LogoutView,
    SeleccionarTipoView,
    AdminLoginView,
)
from .registro_views import (
    RegistroOyenteView,
    RegistroArtistaView,
    RegistroAdminView,
)
from .perfil_views import (
    DashboardOyenteView,
    DashboardArtistaView,
    PerfilOyenteView,
    ConfiguracionOyenteView,
    PerfilArtistaView,
    ConfiguracionArtistaView,
)
from .admin_views import (
    AdminDashboardView,
    AdminOyenteListView,
    AdminOyenteDetailView,
    AdminOyenteEditView,
    AdminOyenteDeleteView,
    AdminArtistaListView,
    AdminArtistaDetailView,
    AdminArtistaEditView,
    AdminArtistaDeleteView,
    AdminAdminListView,
    AdminAdminDetailView,
    AdminAdminEditView,
    AdminAdminDeleteView,
    AdminPersonaListView,
    AdminPersonaDetailView,
)
