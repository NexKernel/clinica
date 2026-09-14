from datetime import datetime
from typing import Annotated

from pydantic import PlainSerializer

from app.core.datetime import to_local

# Toda fecha que sale de la API se expresa en horario de Perú, con su
# desplazamiento explícito (…T08:30:00-05:00) para que no haya ambigüedad.
LocalDatetime = Annotated[
    datetime,
    PlainSerializer(lambda value: to_local(value).isoformat(), return_type=str, when_used="json"),
]
