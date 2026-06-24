"""
Endpoint de carátulas en LOTE (lazy-load).

Las páginas del oyente se renderizan al instante con un placeholder y luego
piden las imágenes de Deezer aquí, en paralelo y con caché persistente. Así
la lista de canciones/álbumes/artistas aparece de inmediato sin esperar a la
API externa.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from ...services import (
    deezer_get_track_image,
    deezer_get_album_image,
    deezer_get_artist_image,
)


@method_decorator(csrf_exempt, name='dispatch')
class CoversBatchView(View):
    """POST {items:[{k,t,a,b}]} → {covers:[url,...]} en el mismo orden.

    k = 'track' | 'album' | 'artist'; t=título, a=artista, b=álbum.
    """

    def post(self, request):
        try:
            data = json.loads(request.body or b'{}')
        except (ValueError, TypeError):
            return JsonResponse({'covers': []})

        items = (data.get('items') or [])[:80]

        def _resolve(it):
            k = (it.get('k') or 'track')
            t = it.get('t') or ''
            a = it.get('a') or ''
            b = it.get('b') or ''
            try:
                if k == 'album':
                    return deezer_get_album_image(t, a)
                if k == 'artist':
                    return deezer_get_artist_image(t or a)
                return deezer_get_track_image(t, a, b)
            except Exception:
                return ''

        if not items:
            return JsonResponse({'covers': []})

        with ThreadPoolExecutor(max_workers=min(16, len(items))) as pool:
            covers = list(pool.map(_resolve, items))
        return JsonResponse({'covers': covers})
