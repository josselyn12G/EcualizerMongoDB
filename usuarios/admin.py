from django.contrib import admin
from .models import Persona, Usuario, Artista, Administrador

admin.site.register(Persona)
admin.site.register(Usuario)
admin.site.register(Artista)
admin.site.register(Administrador)