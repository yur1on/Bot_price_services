from typing import Iterable, Tuple

from django.db.models import Prefetch, Q

from .models import Device, DisplayOption, normalize_text


def search_devices(query: str, limit: int = 4, offset: int = 0) -> Iterable[Device]:
    normalized_query = normalize_text(query)
    display_queryset = DisplayOption.objects.all().order_by("display_type")
    return (
        Device.objects.filter(is_active=True)
        .filter(Q(normalized_name__contains=normalized_query) | Q(model_name__icontains=query))
        .prefetch_related(Prefetch("display_options", queryset=display_queryset))
        .order_by("model_name")[offset:offset + limit]
    )


def search_devices_with_total(query: str, limit: int = 4, offset: int = 0) -> Tuple[list[Device], int]:
    normalized_query = normalize_text(query)
    queryset = Device.objects.filter(is_active=True).filter(
        Q(normalized_name__contains=normalized_query) | Q(model_name__icontains=query)
    )
    total = queryset.count()
    display_queryset = DisplayOption.objects.all().order_by("display_type")
    devices = list(
        queryset.prefetch_related(Prefetch("display_options", queryset=display_queryset)).order_by("model_name")[
            offset:offset + limit
        ]
    )
    return devices, total
